from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Protocol

from src.applications.webhook.domain.entities import WebhookEndpointRuntime


class WebhookRuntimeRepository(Protocol):
    def resolve_ingress_endpoint(
        self,
        *,
        provider_code: str,
        event_type: str,
    ) -> Optional[WebhookEndpointRuntime]:
        ...

    def resolve_egress_endpoint(
        self,
        *,
        workflow_id: uuid.UUID,
        target_ref: str,
    ) -> WebhookEndpointRuntime:
        ...

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
        ...

    def get_webhook_event(
        self,
        *,
        webhook_event_id: uuid.UUID,
    ) -> Optional[dict[str, object]]:
        ...

    def update_webhook_event_status(
        self,
        *,
        webhook_event_id: uuid.UUID,
        delivery_status: str,
    ) -> None:
        ...

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
        ...

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
        ...

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
        ...

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
        ...

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
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

