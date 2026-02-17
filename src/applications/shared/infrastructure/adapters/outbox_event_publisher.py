from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm


class ExchangePublisher(Protocol):
    def publish(self, *, exchange_name: str, routing_key: str, payload: dict[str, Any]) -> None:
        ...


@dataclass(frozen=True)
class PublishedOutboxEvent:
    exchange_name: str
    routing_key: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class OutboxPublishCycle:
    claimed_count: int
    published_count: int
    retried_count: int
    failed_count: int
    published_messages: tuple[PublishedOutboxEvent, ...]


@dataclass(frozen=True)
class _ClaimedOutboxEvent:
    id: uuid.UUID
    exchange_name: str
    routing_key: str
    payload: dict[str, Any]


class InMemoryExchangePublisher:
    def __init__(self) -> None:
        self.messages: list[PublishedOutboxEvent] = []

    def publish(self, *, exchange_name: str, routing_key: str, payload: dict[str, Any]) -> None:
        self.messages.append(
            PublishedOutboxEvent(
                exchange_name=exchange_name,
                routing_key=routing_key,
                payload=payload,
            )
        )


class RabbitMqExchangePublisher:
    def __init__(
        self,
        amqp_url: str,
        *,
        exchange_type: str = "topic",
        durable: bool = True,
    ) -> None:
        try:
            import pika
        except ModuleNotFoundError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("pika is required when messaging is enabled") from exc

        self._pika = pika
        self._amqp_url = amqp_url
        self._exchange_type = exchange_type
        self._durable = durable

    def publish(self, *, exchange_name: str, routing_key: str, payload: dict[str, Any]) -> None:
        connection = self._pika.BlockingConnection(self._pika.URLParameters(self._amqp_url))
        try:
            channel = connection.channel()
            channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=self._exchange_type,
                durable=self._durable,
            )
            channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                properties=self._pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
        finally:
            connection.close()


class OutboxEventPublisher:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        exchange_publisher: ExchangePublisher,
        *,
        worker_id: Optional[str] = None,
        lock_timeout_seconds: int = 60,
        max_attempts: int = 5,
        base_retry_delay_seconds: int = 5,
    ) -> None:
        self._session_factory = session_factory
        self._exchange_publisher = exchange_publisher
        self._worker_id = worker_id or f"outbox-worker-{uuid.uuid4()}"
        self._lock_timeout_seconds = lock_timeout_seconds
        self._max_attempts = max_attempts
        self._base_retry_delay_seconds = base_retry_delay_seconds

    def publish_pending(self, limit: int = 100) -> Sequence[PublishedOutboxEvent]:
        cycle = self.publish_cycle(limit=limit)
        return cycle.published_messages

    def publish_cycle(self, limit: int = 100) -> OutboxPublishCycle:
        claimed_events = self._claim_batch(limit=limit)
        published_messages: list[PublishedOutboxEvent] = []
        retried_count = 0
        failed_count = 0

        for claimed_event in claimed_events:
            try:
                self._exchange_publisher.publish(
                    exchange_name=claimed_event.exchange_name,
                    routing_key=claimed_event.routing_key,
                    payload=claimed_event.payload,
                )
                self._mark_published(claimed_event.id)
                published_messages.append(
                    PublishedOutboxEvent(
                        exchange_name=claimed_event.exchange_name,
                        routing_key=claimed_event.routing_key,
                        payload=claimed_event.payload,
                    )
                )
            except Exception as exc:  # pragma: no cover - integration/runtime behavior
                publish_status = self._mark_retry_or_failed(claimed_event.id, str(exc))
                if publish_status == "FAILED":
                    failed_count += 1
                else:
                    retried_count += 1

        return OutboxPublishCycle(
            claimed_count=len(claimed_events),
            published_count=len(published_messages),
            retried_count=retried_count,
            failed_count=failed_count,
            published_messages=tuple(published_messages),
        )

    def _claim_batch(self, *, limit: int) -> tuple[_ClaimedOutboxEvent, ...]:
        now = datetime.now(timezone.utc)
        stale_lock_cutoff = now - timedelta(seconds=self._lock_timeout_seconds)

        with self._session_factory() as session:
            query = (
                select(OutboxEventOrm)
                .where(
                    or_(
                        and_(
                            OutboxEventOrm.publish_status.in_(("PENDING", "RETRY")),
                            OutboxEventOrm.next_attempt_at <= now,
                        ),
                        and_(
                            OutboxEventOrm.publish_status == "PROCESSING",
                            OutboxEventOrm.locked_at.is_not(None),
                            OutboxEventOrm.locked_at <= stale_lock_cutoff,
                        ),
                    )
                )
                .order_by(OutboxEventOrm.created_at.asc())
                .limit(limit)
            )

            dialect_name = session.bind.dialect.name if session.bind is not None else ""
            if dialect_name != "sqlite":
                query = query.with_for_update(skip_locked=True)

            rows = session.execute(query).scalars().all()
            for row in rows:
                row.publish_status = "PROCESSING"
                row.locked_at = now
                row.locked_by = self._worker_id

            session.commit()

            claimed = tuple(
                _ClaimedOutboxEvent(
                    id=row.id,
                    exchange_name=row.exchange_name,
                    routing_key=row.routing_key,
                    payload=row.payload,
                )
                for row in rows
            )
            return claimed

    def _mark_published(self, outbox_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            row = session.get(OutboxEventOrm, outbox_id)
            if row is None:
                return

            row.attempts += 1
            row.publish_status = "PUBLISHED"
            row.published_at = now
            row.next_attempt_at = now
            row.last_error = None
            row.locked_at = None
            row.locked_by = None
            session.commit()

    def _mark_retry_or_failed(self, outbox_id: uuid.UUID, error_message: str) -> str:
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            row = session.get(OutboxEventOrm, outbox_id)
            if row is None:
                return "FAILED"

            row.attempts += 1
            row.last_error = error_message[:2048]
            row.locked_at = None
            row.locked_by = None

            if row.attempts >= self._max_attempts:
                row.publish_status = "FAILED"
                row.next_attempt_at = now
            else:
                retry_seconds = self._base_retry_delay_seconds * (2 ** max(0, row.attempts - 1))
                row.publish_status = "RETRY"
                row.next_attempt_at = now + timedelta(seconds=retry_seconds)

            session.commit()
            return row.publish_status
