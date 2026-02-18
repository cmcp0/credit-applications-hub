from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from src.applications.application.infrastructure.adapters.application_orm_model import ApplicationOrm


@dataclass(frozen=True)
class ApplicationsRealtimeEnvelope:
    owner_id: str
    payload: dict[str, Any]


class ApplicationsRealtimeHub:
    def __init__(self, *, queue_size: int = 200) -> None:
        self._queue_size = max(1, queue_size)
        self._subscribers: set[asyncio.Queue[ApplicationsRealtimeEnvelope]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[ApplicationsRealtimeEnvelope]:
        queue: asyncio.Queue[ApplicationsRealtimeEnvelope] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[ApplicationsRealtimeEnvelope]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, envelope: ApplicationsRealtimeEnvelope) -> None:
        async with self._lock:
            subscribers = tuple(self._subscribers)

        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                continue


class ApplicationsRealtimeProjector:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        hub: ApplicationsRealtimeHub,
        poll_interval_ms: int,
        batch_size: int = 200,
    ) -> None:
        self._session_factory = session_factory
        self._hub = hub
        self._poll_interval_seconds = max(0.1, poll_interval_ms / 1000)
        self._batch_size = max(1, batch_size)
        self._running = False
        self._cursor_updated_at = datetime.now(timezone.utc)
        self._cursor_id = uuid.UUID(int=0)

    async def run(self) -> None:
        self._running = True
        while self._running:
            events = await asyncio.to_thread(self._read_next_events_batch)
            for event in events:
                await self._hub.publish(event)
            if events:
                await asyncio.sleep(0)
            else:
                await asyncio.sleep(self._poll_interval_seconds)

    def stop(self) -> None:
        self._running = False

    def _read_next_events_batch(self) -> list[ApplicationsRealtimeEnvelope]:
        with self._session_factory() as session:
            rows = self._query_updated_applications(session)
            if not rows:
                return []

            events = [_build_realtime_envelope(row) for row in rows]
            last_row = rows[-1]
            self._cursor_updated_at = _as_utc(last_row.updated_at)
            self._cursor_id = last_row.id
            return events

    def _query_updated_applications(self, session: Session) -> list[ApplicationOrm]:
        statement = (
            select(ApplicationOrm)
            .where(
                or_(
                    ApplicationOrm.updated_at > self._cursor_updated_at,
                    and_(
                        ApplicationOrm.updated_at == self._cursor_updated_at,
                        ApplicationOrm.id > self._cursor_id,
                    ),
                )
            )
            .order_by(ApplicationOrm.updated_at.asc(), ApplicationOrm.id.asc())
            .limit(self._batch_size)
        )
        return session.execute(statement).scalars().all()


def build_realtime_message(envelope: ApplicationsRealtimeEnvelope) -> str:
    return json.dumps(envelope.payload, separators=(",", ":"))


def _build_realtime_envelope(row: ApplicationOrm) -> ApplicationsRealtimeEnvelope:
    emitted_at = _as_utc(row.updated_at).isoformat()
    event_type = "ApplicationCreated" if int(row.version) <= 1 else "ApplicationStatusUpdated"
    payload = {
        "event": {
            "application": {
                "id": str(row.id),
                "country": row.country,
                "status_code": row.status_code,
                "requested_amount": float(row.requested_amount),
                "created_at": _as_utc(row.created_at).isoformat(),
                "updated_at": emitted_at,
            },
            "version": int(row.version),
        },
        "meta": {
            "event_type": event_type,
            "schema_version": "1.0",
            "correlation_id": str(row.id),
            "emitted_at": emitted_at,
        },
    }
    return ApplicationsRealtimeEnvelope(owner_id=str(row.user_id), payload=payload)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
