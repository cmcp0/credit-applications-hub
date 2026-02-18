from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from src.applications.webhook.application.services.egress_webhook_delivery_service import (
    EgressWebhookDeliveryService,
)
from src.applications.webhook.infrastructure.adapters.webhook_runtime_repository import (
    SqlAlchemyWebhookRuntimeRepository,
)
from src.applications.webhook.infrastructure.services.http_client import UrllibWebhookHttpClient


def get_webhooks_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def build_egress_delivery_service(session: Session) -> EgressWebhookDeliveryService:
    repository = SqlAlchemyWebhookRuntimeRepository(session)
    return EgressWebhookDeliveryService(
        repository=repository,
        http_client=UrllibWebhookHttpClient(),
    )

