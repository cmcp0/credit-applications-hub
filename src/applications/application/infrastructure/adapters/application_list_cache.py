from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Protocol

try:  # pragma: no cover - optional runtime dependency fallback
    from redis import Redis
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency fallback
    Redis = None  # type: ignore[assignment]

from src.applications.application.domain.value_objects import ApplicationListPage, ApplicationSummary


class ApplicationListCache(Protocol):
    def get(self, key: str) -> Optional[ApplicationListPage]:
        ...

    def set(self, key: str, value: ApplicationListPage) -> None:
        ...


class InMemoryApplicationListCache:
    def __init__(self, *, ttl_seconds: int) -> None:
        self._ttl_seconds = max(1, ttl_seconds)
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, ApplicationListPage]] = {}

    def get(self, key: str) -> Optional[ApplicationListPage]:
        now = time.time()
        with self._lock:
            cached = self._items.get(key)
            if cached is None:
                return None
            expires_at, value = cached
            if expires_at <= now:
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: str, value: ApplicationListPage) -> None:
        expires_at = time.time() + self._ttl_seconds
        with self._lock:
            self._items[key] = (expires_at, value)


class RedisApplicationListCache:
    def __init__(
        self,
        *,
        redis_url: str,
        ttl_seconds: int,
        key_prefix: str = "applications:list",
        fallback_cache: Optional[ApplicationListCache] = None,
    ) -> None:
        self._ttl_seconds = max(1, ttl_seconds)
        self._key_prefix = key_prefix
        self._fallback_cache = fallback_cache or InMemoryApplicationListCache(
            ttl_seconds=self._ttl_seconds
        )

        if Redis is None:
            self._redis = None
            return

        try:
            self._redis = Redis.from_url(redis_url, decode_responses=True)
        except Exception:
            self._redis = None

    def get(self, key: str) -> Optional[ApplicationListPage]:
        if self._redis is None:
            return self._fallback_cache.get(key)

        cache_key = self._cache_key(key)
        try:
            raw_value = self._redis.get(cache_key)
        except Exception:
            self._redis = None
            return self._fallback_cache.get(key)

        if not raw_value:
            return self._fallback_cache.get(key)

        try:
            payload = json.loads(raw_value)
            cached_page = _deserialize_page(payload)
        except Exception:
            return self._fallback_cache.get(key)

        self._fallback_cache.set(key, cached_page)
        return cached_page

    def set(self, key: str, value: ApplicationListPage) -> None:
        self._fallback_cache.set(key, value)
        if self._redis is None:
            return

        cache_key = self._cache_key(key)
        serialized = json.dumps(_serialize_page(value), separators=(",", ":"))
        try:
            self._redis.setex(cache_key, self._ttl_seconds, serialized)
        except Exception:
            self._redis = None

    def _cache_key(self, key: str) -> str:
        return f"{self._key_prefix}:{key}"


def build_application_list_cache(
    *,
    enabled: bool,
    redis_url: str,
    ttl_seconds: int,
) -> ApplicationListCache:
    in_memory_cache = InMemoryApplicationListCache(ttl_seconds=ttl_seconds)
    if not enabled:
        return in_memory_cache
    return RedisApplicationListCache(
        redis_url=redis_url,
        ttl_seconds=ttl_seconds,
        fallback_cache=in_memory_cache,
    )


def _serialize_page(page: ApplicationListPage) -> dict[str, object]:
    return {
        "items": [
            {
                "id": item.id,
                "country": item.country,
                "status_code": item.status_code,
                "requested_amount": item.requested_amount,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in page.items
        ],
        "page": page.page,
        "page_size": page.page_size,
        "total": page.total,
    }


def _deserialize_page(payload: object) -> ApplicationListPage:
    if not isinstance(payload, dict):
        raise ValueError("Cached payload must be an object")

    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("Cached payload items must be a list")

    items: list[ApplicationSummary] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError("Cached item must be an object")
        items.append(
            ApplicationSummary(
                id=str(raw_item["id"]),
                country=str(raw_item["country"]),
                status_code=str(raw_item["status_code"]),
                requested_amount=float(raw_item["requested_amount"]),
                created_at=_parse_datetime(raw_item["created_at"]),
                updated_at=_parse_datetime(raw_item["updated_at"]),
            )
        )

    return ApplicationListPage(
        items=tuple(items),
        page=int(payload["page"]),
        page_size=int(payload["page_size"]),
        total=int(payload["total"]),
    )


def _parse_datetime(raw: object) -> datetime:
    if not isinstance(raw, str):
        raise ValueError("Cached datetime must be a string")
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
