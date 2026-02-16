from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from apps.backend.auth.dependencies import get_login_service, get_settings
from apps.backend.auth.schemas import ErrorResponse, LoginRequest, LoginResponse
from apps.backend.security.pii_redaction import fingerprint
from apps.backend.settings import Settings
from src.auth.authentication.application.dto import LoginCommand
from src.auth.authentication.application.services.login_service import LoginService
from src.auth.authentication.infrastructure.adapters.login_audit_mapper import map_login_audit_event
from src.auth.shared.domain.errors import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
def login(
    payload: LoginRequest,
    request: Request,
    login_service: Annotated[LoginService, Depends(get_login_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    normalized_email = payload.email.strip().lower()
    pepper = settings.rate_limit_key_pepper or settings.auth_jwt_secret
    email_fingerprint = fingerprint(normalized_email, pepper)

    try:
        login_result = login_service.login(
            LoginCommand(email=payload.email, password=payload.password)
        )
    except AuthError as exc:
        audit_payload = map_login_audit_event(
            hashed_email=email_fingerprint,
            outcome=exc.code,
            ip_address=request.client.host if request.client else None,
        )
        logger.warning("login_failed", extra={"auth": audit_payload})
        raise

    audit_payload = map_login_audit_event(
        hashed_email=email_fingerprint,
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else None,
    )
    logger.info("login_success", extra={"auth": audit_payload})

    return LoginResponse(
        access_token=login_result.access_token,
        token_type=login_result.token_type,
        expires_in=login_result.expires_in,
    )
