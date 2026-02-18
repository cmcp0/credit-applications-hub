from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from src.applications.webhook.application.services.signature_verifier import (
    verify_hmac_sha256_signature,
)
from src.applications.webhook.domain.entities import IngressWebhookAccepted
from src.applications.webhook.domain.ports.webhook_runtime_repository import (
    WebhookRuntimeRepository,
)

WEBHOOKS_EVENTS_EXCHANGE = "webhooks.events"
WEBHOOK_INGRESS_RECEIVED_ROUTING_KEY = "credit.webhook.ingress.received"


class IngressEndpointNotFoundError(Exception):
    pass


class IngressWebhookService:
    def __init__(
        self,
        repository: WebhookRuntimeRepository,
        *,
        secret_resolver: Callable[[str], Optional[str]],
    ) -> None:
        self._repository = repository
        self._secret_resolver = secret_resolver

    def accept_webhook(
        self,
        *,
        provider_code: str,
        event_type: str,
        payload: dict[str, object],
        raw_payload: bytes,
        signature_header: Optional[str],
        external_event_id: Optional[str],
        correlation_id: Optional[str],
        occurred_at: Optional[datetime] = None,
    ) -> IngressWebhookAccepted:
        normalized_provider = provider_code.strip()
        normalized_event_type = event_type.strip()
        endpoint = self._repository.resolve_ingress_endpoint(
            provider_code=normalized_provider,
            event_type=normalized_event_type,
        )
        if endpoint is None:
            raise IngressEndpointNotFoundError(
                f"No active ingress endpoint for {normalized_provider}:{normalized_event_type}"
            )

        now = occurred_at or datetime.now(timezone.utc)
        resolved_correlation_id = _safe_uuid(correlation_id) or uuid.uuid4()
        resolved_signature = signature_header.strip() if signature_header else ""
        secret = self._secret_resolver(endpoint.secret_ref)

        signature_valid: Optional[bool]
        if not resolved_signature:
            signature_valid = None
        elif not secret:
            signature_valid = False
        else:
            signature_valid = verify_hmac_sha256_signature(
                payload_bytes=raw_payload,
                provided_signature=resolved_signature,
                secret=secret,
            )

        payload_hash = "sha256:" + hashlib.sha256(raw_payload).hexdigest()
        webhook_event_id = self._repository.create_webhook_event(
            endpoint_id=uuid.UUID(endpoint.endpoint_id),
            workflow_id=uuid.UUID(endpoint.workflow_id),
            provider_code=endpoint.provider_code,
            direction="INGRESS",
            event_type=endpoint.event_type,
            payload=payload,
            payload_hash=payload_hash,
            signature_valid=signature_valid,
            external_event_id=external_event_id.strip() if external_event_id else None,
            application_id=None,
            correlation_id=resolved_correlation_id,
            delivery_status="RECEIVED",
            occurred_at=now,
            created_at=now,
        )

        self._repository.enqueue_outbox_event(
            aggregate_type="webhook_event",
            aggregate_id=webhook_event_id,
            exchange_name=WEBHOOKS_EVENTS_EXCHANGE,
            routing_key=WEBHOOK_INGRESS_RECEIVED_ROUTING_KEY,
            event_name="WebhookIngressReceived",
            schema_version="v1",
            correlation_id=resolved_correlation_id,
            payload={
                "webhook_event_id": str(webhook_event_id),
                "workflow_id": endpoint.workflow_id,
                "endpoint_id": endpoint.endpoint_id,
                "provider_code": endpoint.provider_code,
                "event_type": endpoint.event_type,
                "payload_hash": payload_hash,
                "signature_valid": signature_valid,
                "received_at": now.isoformat(),
                "payload": _safe_payload(payload),
            },
            occurred_at=now,
        )

        self._repository.commit()
        return IngressWebhookAccepted(
            webhook_event_id=str(webhook_event_id),
            workflow_id=endpoint.workflow_id,
            endpoint_id=endpoint.endpoint_id,
            correlation_id=str(resolved_correlation_id),
            signature_valid=signature_valid,
            occurred_at=now,
        )


def _safe_uuid(raw: Optional[str]) -> Optional[uuid.UUID]:
    if not raw:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        return uuid.UUID(stripped)
    except ValueError:
        return None


def _safe_payload(payload: dict[str, object]) -> dict[str, object]:
    # Enforce JSON-serializable dict payloads in outbox projections.
    return json.loads(json.dumps(payload))

