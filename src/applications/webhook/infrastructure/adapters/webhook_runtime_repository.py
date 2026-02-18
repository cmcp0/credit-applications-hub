from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.applications.execution.infrastructure.adapters.execution_orm_model import (
    EventConsumptionOrm,
    WorkerJobOrm,
)
from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm
from src.applications.webhook.domain.entities import WebhookEndpointRuntime
from src.applications.webhook.domain.ports.webhook_runtime_repository import (
    WebhookRuntimeRepository,
)
from src.applications.workflow.infrastructure.adapters.workflow_orm_model import (
    WebhookDeliveryAttemptOrm,
    WebhookEndpointOrm,
    WebhookEventOrm,
)


class SqlAlchemyWebhookRuntimeRepository(WebhookRuntimeRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve_ingress_endpoint(
        self,
        *,
        provider_code: str,
        event_type: str,
    ) -> Optional[WebhookEndpointRuntime]:
        endpoint = self._session.execute(
            select(WebhookEndpointOrm)
            .where(
                WebhookEndpointOrm.direction == "INGRESS",
                WebhookEndpointOrm.provider_code == provider_code,
                WebhookEndpointOrm.event_type == event_type,
                WebhookEndpointOrm.active.is_(True),
            )
            .order_by(WebhookEndpointOrm.updated_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return _to_runtime_endpoint(endpoint) if endpoint else None

    def resolve_egress_endpoint(
        self,
        *,
        workflow_id: uuid.UUID,
        target_ref: str,
    ) -> WebhookEndpointRuntime:
        normalized_target_ref = target_ref.strip()
        endpoint: Optional[WebhookEndpointOrm]
        if normalized_target_ref.startswith("webhook_endpoint:"):
            endpoint_id = uuid.UUID(normalized_target_ref.split(":", 1)[1])
            endpoint = self._session.execute(
                select(WebhookEndpointOrm)
                .where(
                    WebhookEndpointOrm.id == endpoint_id,
                    WebhookEndpointOrm.workflow_id == workflow_id,
                    WebhookEndpointOrm.direction == "EGRESS",
                    WebhookEndpointOrm.active.is_(True),
                )
                .limit(1)
            ).scalar_one_or_none()
            if endpoint is None:
                raise ValueError("No active egress endpoint found for target_ref")
            return _to_runtime_endpoint(endpoint)

        if normalized_target_ref.startswith("provider:"):
            parts = normalized_target_ref.split(":")
            if len(parts) != 3:
                raise ValueError("provider target_ref must match provider:{provider_code}:{event_type}")
            provider_code = parts[1].strip()
            event_type = parts[2].strip()
            rows = self._session.execute(
                select(WebhookEndpointOrm)
                .where(
                    WebhookEndpointOrm.workflow_id == workflow_id,
                    WebhookEndpointOrm.direction == "EGRESS",
                    WebhookEndpointOrm.provider_code == provider_code,
                    WebhookEndpointOrm.event_type == event_type,
                    WebhookEndpointOrm.active.is_(True),
                )
                .order_by(WebhookEndpointOrm.updated_at.desc())
                .limit(2)
            ).scalars().all()
            if len(rows) != 1:
                raise ValueError("Target resolver requires exactly one active endpoint")
            return _to_runtime_endpoint(rows[0])

        raise ValueError("Unsupported target_ref format")

    def create_webhook_event(
        self,
        *,
        endpoint_id: uuid.UUID,
        workflow_id: uuid.UUID,
        provider_code: str,
        direction: str,
        event_type: str,
        payload: dict[str, object],
        payload_hash: str,
        signature_valid: Optional[bool],
        external_event_id: Optional[str],
        application_id: Optional[uuid.UUID],
        correlation_id: uuid.UUID,
        delivery_status: str,
        occurred_at: datetime,
        created_at: datetime,
    ) -> uuid.UUID:
        webhook_event_id = uuid.uuid4()
        self._session.add(
            WebhookEventOrm(
                id=webhook_event_id,
                endpoint_id=endpoint_id,
                workflow_id=workflow_id,
                application_id=application_id,
                provider_code=provider_code,
                direction=direction,
                event_type=event_type,
                payload=payload,
                payload_hash=payload_hash,
                signature_valid=signature_valid,
                external_event_id=external_event_id,
                correlation_id=correlation_id,
                delivery_status=delivery_status,
                occurred_at=occurred_at,
                created_at=created_at,
            )
        )
        self._session.flush()
        return webhook_event_id

    def get_webhook_event(
        self,
        *,
        webhook_event_id: uuid.UUID,
    ) -> Optional[dict[str, object]]:
        row = self._session.get(WebhookEventOrm, webhook_event_id)
        if row is None:
            return None
        return {
            "id": str(row.id),
            "workflow_id": str(row.workflow_id),
            "endpoint_id": str(row.endpoint_id),
            "delivery_status": row.delivery_status,
            "correlation_id": str(row.correlation_id),
        }

    def update_webhook_event_status(
        self,
        *,
        webhook_event_id: uuid.UUID,
        delivery_status: str,
    ) -> None:
        row = self._session.get(WebhookEventOrm, webhook_event_id)
        if row is None:
            raise ValueError("webhook event not found")
        row.delivery_status = delivery_status

    def append_delivery_attempt(
        self,
        *,
        webhook_event_id: uuid.UUID,
        attempt_no: int,
        delivery_status: str,
        response_code: Optional[int],
        response_body: Optional[str],
        latency_ms: Optional[int],
        error_code: Optional[str],
        error_message: Optional[str],
        next_retry_at: Optional[datetime],
        created_at: datetime,
    ) -> None:
        self._session.add(
            WebhookDeliveryAttemptOrm(
                id=uuid.uuid4(),
                webhook_event_id=webhook_event_id,
                attempt_no=attempt_no,
                delivery_status=delivery_status,
                response_code=response_code,
                response_body=response_body,
                latency_ms=latency_ms,
                error_code=error_code,
                error_message=error_message,
                next_retry_at=next_retry_at,
                created_at=created_at,
            )
        )

    def get_or_create_worker_job(
        self,
        *,
        idempotency_key: str,
        workflow_id: uuid.UUID,
        workflow_revision: int,
        application_id: Optional[uuid.UUID],
        operation_id: Optional[uuid.UUID],
        sub_operation_id: Optional[uuid.UUID],
        correlation_id: uuid.UUID,
        max_attempts: int,
        created_at: datetime,
    ) -> dict[str, object]:
        existing = self._session.execute(
            select(WorkerJobOrm).where(WorkerJobOrm.idempotency_key == idempotency_key).limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return {
                "id": existing.id,
                "attempts": existing.attempts,
                "max_attempts": existing.max_attempts,
            }

        worker_job_id = uuid.uuid4()
        self._session.add(
            WorkerJobOrm(
                id=worker_job_id,
                workflow_id=workflow_id,
                workflow_revision=workflow_revision,
                application_id=application_id,
                operation_id=operation_id,
                sub_operation_id=sub_operation_id,
                status="PENDING",
                idempotency_key=idempotency_key,
                payload_summary={"redacted": True},
                attempts=0,
                max_attempts=max_attempts,
                available_at=created_at,
                locked_at=None,
                completed_at=None,
                last_error_code=None,
                last_error_message=None,
                correlation_id=correlation_id,
                created_at=created_at,
                updated_at=created_at,
            )
        )
        self._session.flush()
        return {
            "id": worker_job_id,
            "attempts": 0,
            "max_attempts": max_attempts,
        }

    def update_worker_job(
        self,
        *,
        worker_job_id: uuid.UUID,
        status: str,
        attempts: int,
        available_at: datetime,
        completed_at: Optional[datetime],
        last_error_code: Optional[str],
        last_error_message: Optional[str],
        updated_at: datetime,
    ) -> None:
        row = self._session.get(WorkerJobOrm, worker_job_id)
        if row is None:
            raise ValueError("worker job not found")

        row.status = status
        row.attempts = attempts
        row.available_at = available_at
        row.completed_at = completed_at
        row.last_error_code = last_error_code
        row.last_error_message = last_error_message
        row.updated_at = updated_at

    def record_event_consumption(
        self,
        *,
        consumer_name: str,
        queue_name: str,
        message_id: str,
        correlation_id: Optional[uuid.UUID],
        payload_hash: Optional[str],
        consumed_at: datetime,
    ) -> bool:
        try:
            self._session.add(
                EventConsumptionOrm(
                    id=uuid.uuid4(),
                    consumer_name=consumer_name,
                    queue_name=queue_name,
                    message_id=message_id,
                    correlation_id=correlation_id,
                    payload_hash=payload_hash,
                    consumed_at=consumed_at,
                )
            )
            self._session.flush()
            return True
        except IntegrityError:
            self._session.rollback()
            return False

    def enqueue_outbox_event(
        self,
        *,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        exchange_name: str,
        routing_key: str,
        event_name: str,
        schema_version: str,
        correlation_id: uuid.UUID,
        payload: dict[str, object],
        occurred_at: datetime,
    ) -> None:
        event_id = uuid.uuid4()
        self._session.add(
            OutboxEventOrm(
                id=event_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                exchange_name=exchange_name,
                routing_key=routing_key,
                event_name=event_name,
                schema_version=schema_version,
                correlation_id=correlation_id,
                payload={
                    "event_name": event_name,
                    "schema_version": schema_version,
                    "event_id": str(event_id),
                    "occurred_at": occurred_at.isoformat(),
                    "request_id": str(event_id),
                    "correlation_id": str(correlation_id),
                    "payload": payload,
                },
                publish_status="PENDING",
                attempts=0,
                last_error=None,
                next_attempt_at=occurred_at,
                locked_at=None,
                locked_by=None,
                occurred_at=occurred_at,
                created_at=datetime.now(timezone.utc),
            )
        )

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()


def _to_runtime_endpoint(endpoint: WebhookEndpointOrm) -> WebhookEndpointRuntime:
    return WebhookEndpointRuntime(
        endpoint_id=str(endpoint.id),
        workflow_id=str(endpoint.workflow_id),
        country=endpoint.country,
        provider_code=endpoint.provider_code,
        direction=endpoint.direction,
        event_type=endpoint.event_type,
        method=endpoint.method,
        url=endpoint.url,
        secret_ref=endpoint.secret_ref,
        timeout_ms=endpoint.timeout_ms,
    )

