from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.applications.application.domain.events import IntegrationEvent
from src.applications.application.domain.ports.outbox_event_writer import OutboxEventWriter
from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm


class SqlAlchemyOutboxEventRepository(OutboxEventWriter):
    def __init__(self, session: Session) -> None:
        self._session = session

    def write(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        exchange_name: str,
        routing_key: str,
        event: IntegrationEvent,
    ) -> None:
        created_at = datetime.now(timezone.utc)
        self._session.add(
            OutboxEventOrm(
                id=uuid.UUID(event.event_id),
                aggregate_type=aggregate_type,
                aggregate_id=uuid.UUID(aggregate_id),
                exchange_name=exchange_name,
                routing_key=routing_key,
                event_name=event.event_name,
                schema_version=event.schema_version,
                correlation_id=uuid.UUID(event.correlation_id),
                payload={
                    "event_name": event.event_name,
                    "schema_version": event.schema_version,
                    "event_id": event.event_id,
                    "occurred_at": event.occurred_at.isoformat(),
                    "request_id": event.request_id,
                    "correlation_id": event.correlation_id,
                    "payload": event.payload,
                },
                publish_status="PENDING",
                attempts=0,
                last_error=None,
                next_attempt_at=created_at,
                locked_at=None,
                locked_by=None,
                occurred_at=event.occurred_at,
                created_at=created_at,
            )
        )
