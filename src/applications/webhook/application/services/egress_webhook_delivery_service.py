from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from src.applications.webhook.application.services.template_renderer import (
    render_payload_template,
)
from src.applications.webhook.domain.entities import EgressDeliveryResult
from src.applications.webhook.domain.ports.webhook_runtime_repository import (
    WebhookRuntimeRepository,
)

WEBHOOKS_EVENTS_EXCHANGE = "webhooks.events"
WEBHOOK_EGRESS_DELIVERED_ROUTING_KEY = "credit.webhook.egress.delivered"
WEBHOOK_EGRESS_FAILED_ROUTING_KEY = "credit.webhook.egress.failed"

RETRYABLE_HTTP_CODES = {408, 425, 429}


@dataclass(frozen=True)
class EgressDeliveryCommand:
    workflow_id: str
    target_ref: str
    input_template: dict[str, object]
    execution_context: dict[str, object]
    correlation_id: str
    idempotency_key: str
    workflow_revision: int
    max_attempts: int = 5
    application_id: Optional[str] = None
    operation_id: Optional[str] = None
    sub_operation_id: Optional[str] = None
    webhook_event_id: Optional[str] = None
    request_id: Optional[str] = None
    message_id: Optional[str] = None
    consumer_name: Optional[str] = None
    queue_name: Optional[str] = None


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: str
    latency_ms: int


class WebhookHttpClient(Protocol):
    def send_json(
        self,
        *,
        method: str,
        url: str,
        payload: dict[str, object],
        timeout_ms: int,
        headers: dict[str, str],
    ) -> HttpResponse:
        ...


class EgressWebhookDeliveryService:
    def __init__(
        self,
        repository: WebhookRuntimeRepository,
        *,
        http_client: WebhookHttpClient,
    ) -> None:
        self._repository = repository
        self._http_client = http_client

    def deliver(self, command: EgressDeliveryCommand) -> EgressDeliveryResult:
        now = datetime.now(timezone.utc)
        workflow_id = uuid.UUID(command.workflow_id)
        correlation_id = uuid.UUID(command.correlation_id)
        application_id = _optional_uuid(command.application_id)
        operation_id = _optional_uuid(command.operation_id)
        sub_operation_id = _optional_uuid(command.sub_operation_id)
        existing_webhook_event_id = _optional_uuid(command.webhook_event_id)

        if command.consumer_name and command.queue_name and command.message_id:
            consumed = self._repository.record_event_consumption(
                consumer_name=command.consumer_name,
                queue_name=command.queue_name,
                message_id=command.message_id,
                correlation_id=correlation_id,
                payload_hash=None,
                consumed_at=now,
            )
            if not consumed:
                return EgressDeliveryResult(
                    webhook_event_id=str(existing_webhook_event_id or uuid.UUID(int=0)),
                    worker_job_id=str(uuid.UUID(int=0)),
                    delivery_status="DUPLICATE",
                    attempts=0,
                    max_attempts=max(1, command.max_attempts),
                    response_code=None,
                    retry_scheduled=False,
                    terminal_failure=False,
                    duplicate_consumption=True,
                )

        endpoint = self._repository.resolve_egress_endpoint(
            workflow_id=workflow_id,
            target_ref=command.target_ref,
        )
        rendered_payload = render_payload_template(command.input_template, command.execution_context)
        payload_bytes = json.dumps(rendered_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_hash = "sha256:" + hashlib.sha256(payload_bytes).hexdigest()

        webhook_event_id = existing_webhook_event_id
        if webhook_event_id is None:
            webhook_event_id = self._repository.create_webhook_event(
                endpoint_id=uuid.UUID(endpoint.endpoint_id),
                workflow_id=workflow_id,
                provider_code=endpoint.provider_code,
                direction="EGRESS",
                event_type=endpoint.event_type,
                payload=rendered_payload,
                payload_hash=payload_hash,
                signature_valid=None,
                external_event_id=None,
                application_id=application_id,
                correlation_id=correlation_id,
                delivery_status="QUEUED",
                occurred_at=now,
                created_at=now,
            )

        job_record = self._repository.get_or_create_worker_job(
            idempotency_key=command.idempotency_key,
            workflow_id=workflow_id,
            workflow_revision=command.workflow_revision,
            application_id=application_id,
            operation_id=operation_id,
            sub_operation_id=sub_operation_id,
            correlation_id=correlation_id,
            max_attempts=max(1, command.max_attempts),
            created_at=now,
        )
        worker_job_id = uuid.UUID(str(job_record["id"]))
        attempts_before = int(job_record.get("attempts", 0))
        max_attempts = int(job_record.get("max_attempts", max(1, command.max_attempts)))
        attempt_no = attempts_before + 1

        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-Id": command.request_id or str(correlation_id),
            "X-Correlation-Id": str(correlation_id),
            "X-Idempotency-Key": command.idempotency_key,
        }

        response_code: Optional[int] = None
        response_body: Optional[str] = None
        latency_ms: Optional[int] = None
        error_code: Optional[str] = None
        error_message: Optional[str] = None
        retryable_failure = False

        try:
            response = self._http_client.send_json(
                method=endpoint.method,
                url=endpoint.url,
                payload=rendered_payload,
                timeout_ms=endpoint.timeout_ms,
                headers=request_headers,
            )
            response_code = response.status_code
            response_body = response.body[:2048]
            latency_ms = response.latency_ms
            retryable_failure = _is_retryable_status_code(response_code)
            success = 200 <= response_code < 300
        except Exception as exc:  # pragma: no cover - runtime safety
            success = False
            retryable_failure = True
            error_code = "HTTP_TRANSPORT_ERROR"
            error_message = str(exc)

        if success:
            self._repository.append_delivery_attempt(
                webhook_event_id=webhook_event_id,
                attempt_no=attempt_no,
                delivery_status="DELIVERED",
                response_code=response_code,
                response_body=response_body,
                latency_ms=latency_ms,
                error_code=None,
                error_message=None,
                next_retry_at=None,
                created_at=now,
            )
            self._repository.update_webhook_event_status(
                webhook_event_id=webhook_event_id,
                delivery_status="DELIVERED",
            )
            self._repository.update_worker_job(
                worker_job_id=worker_job_id,
                status="SUCCEEDED",
                attempts=attempt_no,
                available_at=now,
                completed_at=now,
                last_error_code=None,
                last_error_message=None,
                updated_at=now,
            )
            self._repository.enqueue_outbox_event(
                aggregate_type="webhook_event",
                aggregate_id=webhook_event_id,
                exchange_name=WEBHOOKS_EVENTS_EXCHANGE,
                routing_key=WEBHOOK_EGRESS_DELIVERED_ROUTING_KEY,
                event_name="WebhookEgressDelivered",
                schema_version="v1",
                correlation_id=correlation_id,
                payload={
                    "webhook_event_id": str(webhook_event_id),
                    "worker_job_id": str(worker_job_id),
                    "response_code": response_code,
                    "attempts": attempt_no,
                    "delivered_at": now.isoformat(),
                },
                occurred_at=now,
            )
            self._repository.commit()
            return EgressDeliveryResult(
                webhook_event_id=str(webhook_event_id),
                worker_job_id=str(worker_job_id),
                delivery_status="DELIVERED",
                attempts=attempt_no,
                max_attempts=max_attempts,
                response_code=response_code,
                retry_scheduled=False,
                terminal_failure=False,
                duplicate_consumption=False,
            )

        if retryable_failure and attempt_no < max_attempts:
            next_retry_at = now + timedelta(seconds=_compute_backoff_seconds(attempt_no))
            self._repository.append_delivery_attempt(
                webhook_event_id=webhook_event_id,
                attempt_no=attempt_no,
                delivery_status="FAILED",
                response_code=response_code,
                response_body=response_body,
                latency_ms=latency_ms,
                error_code=error_code or _status_error_code(response_code),
                error_message=error_message or _status_error_message(response_code),
                next_retry_at=next_retry_at,
                created_at=now,
            )
            self._repository.update_webhook_event_status(
                webhook_event_id=webhook_event_id,
                delivery_status="QUEUED",
            )
            self._repository.update_worker_job(
                worker_job_id=worker_job_id,
                status="RUNNING",
                attempts=attempt_no,
                available_at=next_retry_at,
                completed_at=None,
                last_error_code=error_code or _status_error_code(response_code),
                last_error_message=error_message or _status_error_message(response_code),
                updated_at=now,
            )
            self._repository.commit()
            return EgressDeliveryResult(
                webhook_event_id=str(webhook_event_id),
                worker_job_id=str(worker_job_id),
                delivery_status="QUEUED",
                attempts=attempt_no,
                max_attempts=max_attempts,
                response_code=response_code,
                retry_scheduled=True,
                terminal_failure=False,
                duplicate_consumption=False,
            )

        terminal_status = "DEAD_LETTERED" if retryable_failure else "FAILED"
        self._repository.append_delivery_attempt(
            webhook_event_id=webhook_event_id,
            attempt_no=attempt_no,
            delivery_status=terminal_status,
            response_code=response_code,
            response_body=response_body,
            latency_ms=latency_ms,
            error_code=error_code or _status_error_code(response_code),
            error_message=error_message or _status_error_message(response_code),
            next_retry_at=None,
            created_at=now,
        )
        self._repository.update_webhook_event_status(
            webhook_event_id=webhook_event_id,
            delivery_status=terminal_status,
        )
        self._repository.update_worker_job(
            worker_job_id=worker_job_id,
            status=terminal_status,
            attempts=attempt_no,
            available_at=now,
            completed_at=now,
            last_error_code=error_code or _status_error_code(response_code),
            last_error_message=error_message or _status_error_message(response_code),
            updated_at=now,
        )
        self._repository.enqueue_outbox_event(
            aggregate_type="webhook_event",
            aggregate_id=webhook_event_id,
            exchange_name=WEBHOOKS_EVENTS_EXCHANGE,
            routing_key=WEBHOOK_EGRESS_FAILED_ROUTING_KEY,
            event_name="WebhookEgressFailed",
            schema_version="v1",
            correlation_id=correlation_id,
            payload={
                "webhook_event_id": str(webhook_event_id),
                "worker_job_id": str(worker_job_id),
                "response_code": response_code,
                "error_code": error_code or _status_error_code(response_code),
                "error_message": error_message or _status_error_message(response_code),
                "attempts": attempt_no,
                "max_attempts": max_attempts,
                "failed_at": now.isoformat(),
            },
            occurred_at=now,
        )
        self._repository.commit()
        return EgressDeliveryResult(
            webhook_event_id=str(webhook_event_id),
            worker_job_id=str(worker_job_id),
            delivery_status=terminal_status,
            attempts=attempt_no,
            max_attempts=max_attempts,
            response_code=response_code,
            retry_scheduled=False,
            terminal_failure=True,
            duplicate_consumption=False,
        )


def _optional_uuid(raw: Optional[str]) -> Optional[uuid.UUID]:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    return uuid.UUID(stripped)


def _is_retryable_status_code(status_code: Optional[int]) -> bool:
    if status_code is None:
        return True
    if status_code in RETRYABLE_HTTP_CODES:
        return True
    return 500 <= status_code <= 599


def _status_error_code(status_code: Optional[int]) -> str:
    if status_code is None:
        return "HTTP_TRANSPORT_ERROR"
    return f"HTTP_{status_code}"


def _status_error_message(status_code: Optional[int]) -> str:
    if status_code is None:
        return "HTTP transport failure"
    return f"HTTP request failed with status {status_code}"


def _compute_backoff_seconds(attempt_no: int) -> int:
    # Deterministic bounded exponential backoff (jitter can be added by worker policy later).
    return min(300, 2**max(1, attempt_no))

