from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from src.applications.execution.infrastructure.adapters.execution_orm_model import WorkerJobOrm
from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm
from src.applications.webhook.application.services.egress_webhook_delivery_service import (
    EgressDeliveryCommand,
    EgressWebhookDeliveryService,
    HttpResponse,
)
from src.applications.webhook.application.services.ingress_webhook_service import (
    IngressWebhookService,
)
from src.applications.webhook.infrastructure.adapters.webhook_runtime_repository import (
    SqlAlchemyWebhookRuntimeRepository,
)
from src.applications.workflow.infrastructure.adapters.workflow_orm_model import (
    WebhookDeliveryAttemptOrm,
    WebhookEndpointOrm,
    WebhookEventOrm,
)
from tests.applications.fixtures.seed import TEST_ADMIN_USER_ID, WORKFLOW_IDS


class _StubHttpClient:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self._responses = responses
        self._cursor = 0

    def send_json(
        self,
        *,
        method: str,
        url: str,
        payload: dict[str, object],
        timeout_ms: int,
        headers: dict[str, str],
    ) -> HttpResponse:
        _ = (method, url, payload, timeout_ms, headers)
        if self._cursor >= len(self._responses):
            return self._responses[-1]
        response = self._responses[self._cursor]
        self._cursor += 1
        return response


def _create_endpoint(
    session,
    *,
    workflow_id: uuid.UUID,
    direction: str,
    provider_code: str,
    event_type: str,
    method: str = "POST",
    url: str = "https://provider.example/webhooks/status",
    secret_ref: str = "secrets://webhooks/provider/default",
) -> uuid.UUID:
    endpoint_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session.add(
        WebhookEndpointOrm(
            id=endpoint_id,
            workflow_id=workflow_id,
            country="MX",
            provider_code=provider_code,
            direction=direction,
            event_type=event_type,
            method=method,
            url=url,
            secret_ref=secret_ref,
            timeout_ms=5000,
            active=True,
            created_by=TEST_ADMIN_USER_ID,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    return endpoint_id


def test_ingress_webhook_service_persists_event_and_outbox(session_factory) -> None:
    workflow_id = WORKFLOW_IDS["MX"]
    with session_factory() as session:
        endpoint_id = _create_endpoint(
            session,
            workflow_id=workflow_id,
            direction="INGRESS",
            provider_code="provider_ingress",
            event_type="ApplicationStatusUpdated",
            secret_ref="secrets://ingress/provider_ingress",
        )

    payload = {"status": "APPROVED", "application_id": "app-1"}
    raw_payload = b'{"status":"APPROVED","application_id":"app-1"}'
    signature = hmac.new(
        key=b"test-secret",
        msg=raw_payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    with session_factory() as session:
        repository = SqlAlchemyWebhookRuntimeRepository(session)
        service = IngressWebhookService(
            repository=repository,
            secret_resolver=lambda secret_ref: "test-secret" if secret_ref else None,
        )
        accepted = service.accept_webhook(
            provider_code="provider_ingress",
            event_type="ApplicationStatusUpdated",
            payload=payload,
            raw_payload=raw_payload,
            signature_header=f"sha256={signature}",
            external_event_id="ext-123",
            correlation_id=str(uuid.uuid4()),
        )

    assert accepted.endpoint_id == str(endpoint_id)
    assert accepted.signature_valid is True

    with session_factory() as session:
        webhook_event = session.execute(
            select(WebhookEventOrm).where(WebhookEventOrm.id == uuid.UUID(accepted.webhook_event_id))
        ).scalar_one()
        assert webhook_event.direction == "INGRESS"
        assert webhook_event.delivery_status == "RECEIVED"
        assert webhook_event.payload_hash.startswith("sha256:")

        outbox_event = session.execute(
            select(OutboxEventOrm).where(OutboxEventOrm.aggregate_id == webhook_event.id)
        ).scalar_one()
        assert outbox_event.exchange_name == "webhooks.events"
        assert outbox_event.routing_key == "credit.webhook.ingress.received"


def test_egress_webhook_delivery_service_records_success_outcome(session_factory) -> None:
    workflow_id = WORKFLOW_IDS["MX"]
    with session_factory() as session:
        endpoint_id = _create_endpoint(
            session,
            workflow_id=workflow_id,
            direction="EGRESS",
            provider_code="provider_egress",
            event_type="ApplicationStatusUpdated",
        )

    with session_factory() as session:
        repository = SqlAlchemyWebhookRuntimeRepository(session)
        service = EgressWebhookDeliveryService(
            repository=repository,
            http_client=_StubHttpClient(
                responses=[HttpResponse(status_code=200, body='{"ok":true}', latency_ms=14)]
            ),
        )
        result = service.deliver(
            EgressDeliveryCommand(
                workflow_id=str(workflow_id),
                target_ref=f"webhook_endpoint:{endpoint_id}",
                input_template={"application_id": "{{ application.id }}"},
                execution_context={"application": {"id": "app-1"}},
                correlation_id=str(uuid.uuid4()),
                idempotency_key=f"egress:{uuid.uuid4()}",
                workflow_revision=1,
                max_attempts=3,
                request_id=str(uuid.uuid4()),
            )
        )

    assert result.delivery_status == "DELIVERED"
    assert result.retry_scheduled is False
    assert result.terminal_failure is False

    with session_factory() as session:
        webhook_event = session.get(WebhookEventOrm, uuid.UUID(result.webhook_event_id))
        assert webhook_event is not None
        assert webhook_event.delivery_status == "DELIVERED"

        attempts = session.execute(
            select(WebhookDeliveryAttemptOrm).where(
                WebhookDeliveryAttemptOrm.webhook_event_id == webhook_event.id
            )
        ).scalars().all()
        assert len(attempts) == 1
        assert attempts[0].delivery_status == "DELIVERED"
        assert attempts[0].response_code == 200

        worker_job = session.get(WorkerJobOrm, uuid.UUID(result.worker_job_id))
        assert worker_job is not None
        assert worker_job.status == "SUCCEEDED"
        assert worker_job.attempts == 1

        delivered_event = session.execute(
            select(OutboxEventOrm).where(
                OutboxEventOrm.routing_key == "credit.webhook.egress.delivered",
                OutboxEventOrm.aggregate_id == webhook_event.id,
            )
        ).scalar_one()
        assert delivered_event.exchange_name == "webhooks.events"


def test_egress_webhook_delivery_service_handles_retry_and_terminal_failure(session_factory) -> None:
    workflow_id = WORKFLOW_IDS["MX"]
    with session_factory() as session:
        endpoint_id = _create_endpoint(
            session,
            workflow_id=workflow_id,
            direction="EGRESS",
            provider_code="provider_retry",
            event_type="ApplicationStatusUpdated",
        )

    idempotency_key = f"egress-retry:{uuid.uuid4()}"
    correlation_id = str(uuid.uuid4())

    with session_factory() as session:
        repository = SqlAlchemyWebhookRuntimeRepository(session)
        service = EgressWebhookDeliveryService(
            repository=repository,
            http_client=_StubHttpClient(
                responses=[
                    HttpResponse(status_code=503, body="unavailable", latency_ms=40),
                    HttpResponse(status_code=503, body="unavailable", latency_ms=39),
                ]
            ),
        )
        first = service.deliver(
            EgressDeliveryCommand(
                workflow_id=str(workflow_id),
                target_ref=f"webhook_endpoint:{endpoint_id}",
                input_template={"application_id": "{{ application.id }}"},
                execution_context={"application": {"id": "app-2"}},
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                workflow_revision=1,
                max_attempts=2,
            )
        )
        second = service.deliver(
            EgressDeliveryCommand(
                workflow_id=str(workflow_id),
                target_ref=f"webhook_endpoint:{endpoint_id}",
                input_template={"application_id": "{{ application.id }}"},
                execution_context={"application": {"id": "app-2"}},
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                workflow_revision=1,
                max_attempts=2,
                webhook_event_id=first.webhook_event_id,
            )
        )

    assert first.delivery_status == "QUEUED"
    assert first.retry_scheduled is True
    assert first.terminal_failure is False

    assert second.delivery_status == "DEAD_LETTERED"
    assert second.retry_scheduled is False
    assert second.terminal_failure is True

    with session_factory() as session:
        webhook_event = session.get(WebhookEventOrm, uuid.UUID(first.webhook_event_id))
        assert webhook_event is not None
        assert webhook_event.delivery_status == "DEAD_LETTERED"

        worker_job = session.get(WorkerJobOrm, uuid.UUID(first.worker_job_id))
        assert worker_job is not None
        assert worker_job.status == "DEAD_LETTERED"
        assert worker_job.attempts == 2

        attempts = session.execute(
            select(WebhookDeliveryAttemptOrm).where(
                WebhookDeliveryAttemptOrm.webhook_event_id == webhook_event.id
            )
        ).scalars().all()
        assert len(attempts) == 2
        assert attempts[-1].delivery_status == "DEAD_LETTERED"

        failed_event = session.execute(
            select(OutboxEventOrm).where(
                OutboxEventOrm.routing_key == "credit.webhook.egress.failed",
                OutboxEventOrm.aggregate_id == webhook_event.id,
            )
        ).scalar_one()
        assert failed_event.exchange_name == "webhooks.events"

