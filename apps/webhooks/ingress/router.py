from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from apps.webhooks.ingress.dependencies import get_ingress_webhook_service
from apps.webhooks.ingress.schemas import IngressWebhookAcceptedResponse
from src.applications.webhook.application.services.ingress_webhook_service import (
    IngressEndpointNotFoundError,
    IngressWebhookService,
)

router = APIRouter(prefix="/ingress", tags=["webhook_ingress"])


@router.post(
    "/{provider_code}/{event_type}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngressWebhookAcceptedResponse,
)
async def receive_provider_webhook(
    request: Request,
    provider_code: str,
    event_type: str,
    service: Annotated[IngressWebhookService, Depends(get_ingress_webhook_service)],
    signature: Annotated[Optional[str], Header(alias="X-Webhook-Signature")] = None,
    correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
    external_event_id: Annotated[Optional[str], Header(alias="X-External-Event-Id")] = None,
    occurred_at: Annotated[Optional[str], Header(alias="X-Occurred-At")] = None,
) -> IngressWebhookAcceptedResponse:
    raw_payload = await request.body()
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Webhook payload must be a JSON object",
        )

    parsed_occurred_at = _parse_occurred_at_header(occurred_at)
    try:
        accepted = service.accept_webhook(
            provider_code=provider_code,
            event_type=event_type,
            payload=payload,
            raw_payload=raw_payload,
            signature_header=signature,
            external_event_id=external_event_id,
            correlation_id=correlation_id,
            occurred_at=parsed_occurred_at,
        )
    except IngressEndpointNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return IngressWebhookAcceptedResponse(
        webhook_event_id=accepted.webhook_event_id,
        workflow_id=accepted.workflow_id,
        endpoint_id=accepted.endpoint_id,
        correlation_id=accepted.correlation_id,
        signature_valid=accepted.signature_valid,
        occurred_at=accepted.occurred_at,
    )


def _parse_occurred_at_header(raw: Optional[str]) -> Optional[datetime]:
    if raw is None or not raw.strip():
        return None
    normalized = raw.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)

