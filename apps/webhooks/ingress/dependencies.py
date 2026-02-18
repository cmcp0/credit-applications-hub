from __future__ import annotations

import os
from collections.abc import Generator
from functools import lru_cache
from typing import Callable, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.applications.webhook.application.services.ingress_webhook_service import (
    IngressWebhookService,
)
from src.applications.webhook.infrastructure.adapters.webhook_runtime_repository import (
    SqlAlchemyWebhookRuntimeRepository,
)


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_ingress_webhook_service(
    db_session: Session = Depends(get_db_session),
) -> IngressWebhookService:
    repository = SqlAlchemyWebhookRuntimeRepository(db_session)
    return IngressWebhookService(
        repository=repository,
        secret_resolver=get_secret_resolver(),
    )


@lru_cache(maxsize=1)
def get_secret_resolver() -> Callable[[str], Optional[str]]:
    secrets_map = _parse_secrets_map(os.getenv("WEBHOOK_INGRESS_SECRETS", ""))
    default_secret = os.getenv("WEBHOOK_INGRESS_DEFAULT_SECRET", "").strip()

    def resolve(secret_ref: str) -> Optional[str]:
        normalized = secret_ref.strip()
        if normalized in secrets_map:
            return secrets_map[normalized]
        if default_secret:
            return default_secret
        return None

    return resolve


def _parse_secrets_map(raw: str) -> dict[str, str]:
    # Format: "secret_ref=secret_value,secret_ref_2=secret_value_2"
    mapping: dict[str, str] = {}
    for pair in raw.split(","):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            mapping[key] = value
    return mapping

