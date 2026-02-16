from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis


class RateLimitStorageUnavailable(Exception):
    pass


@dataclass(frozen=True)
class RateLimitCheckResult:
    allowed: bool
    limit: int
    remaining: int
    reset_epoch_seconds: int
    retry_after_seconds: int


class RedisSlidingWindowStorage:
    def __init__(self, redis_url: str) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)

    async def check_and_increment(
        self,
        *,
        key: str,
        window_seconds: int,
        max_requests: int,
    ) -> RateLimitCheckResult:
        now_seconds = time.time()
        now_ms = int(now_seconds * 1000)
        window_ms = window_seconds * 1000
        window_start_ms = now_ms - window_ms
        member = f"{now_ms}:{uuid.uuid4()}"

        try:
            pipeline = self._redis.pipeline(transaction=True)
            pipeline.zadd(key, {member: now_ms})
            pipeline.zremrangebyscore(key, 0, window_start_ms)
            pipeline.zcard(key)
            pipeline.expire(key, window_seconds)
            _, _, count, _ = await pipeline.execute()

            count = int(count)
            allowed = count <= max_requests
            remaining = max(0, max_requests - count)

            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_timestamp_ms = int(oldest[0][1])
                reset_epoch_seconds = math.ceil((oldest_timestamp_ms + window_ms) / 1000)
            else:
                reset_epoch_seconds = math.ceil(now_seconds + window_seconds)

            retry_after_seconds = max(1, reset_epoch_seconds - math.floor(now_seconds))
            return RateLimitCheckResult(
                allowed=allowed,
                limit=max_requests,
                remaining=remaining,
                reset_epoch_seconds=reset_epoch_seconds,
                retry_after_seconds=retry_after_seconds,
            )
        except Exception as exc:  # pragma: no cover
            raise RateLimitStorageUnavailable() from exc


class InMemorySlidingWindowStorage:
    def __init__(self) -> None:
        self._events: dict[str, list[float]] = {}

    async def check_and_increment(
        self,
        *,
        key: str,
        window_seconds: int,
        max_requests: int,
    ) -> RateLimitCheckResult:
        now = time.time()
        window_start = now - window_seconds

        events = self._events.setdefault(key, [])
        events[:] = [event for event in events if event > window_start]
        events.append(now)

        count = len(events)
        allowed = count <= max_requests
        remaining = max(0, max_requests - count)

        oldest = events[0] if events else now
        reset_epoch_seconds = math.ceil(oldest + window_seconds)
        retry_after_seconds = max(1, reset_epoch_seconds - math.floor(now))

        return RateLimitCheckResult(
            allowed=allowed,
            limit=max_requests,
            remaining=remaining,
            reset_epoch_seconds=reset_epoch_seconds,
            retry_after_seconds=retry_after_seconds,
        )
