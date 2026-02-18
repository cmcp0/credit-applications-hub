from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from apps.backend.auth.jwt_codec import JwtCodec, JwtCodecConfig
from apps.backend.realtime.applications_stream import (
    ApplicationsRealtimeHub,
    ApplicationsRealtimeEnvelope,
    build_realtime_message,
)
from apps.backend.settings import Settings
from src.auth.authorization.application.services.authorize_request_service import (
    AuthorizeRequestService,
)
from src.auth.authorization.domain.entities import AuthenticatedPrincipal
from src.auth.shared.domain.errors import AuthError, TokenInvalidError

router = APIRouter(prefix="/realtime", tags=["realtime"])

_WS_CLOSE_UNAUTHORIZED = 4401
_WS_CLOSE_FORBIDDEN = 4403
_WS_CLOSE_UNAVAILABLE = 1013
_HEARTBEAT_INTERVAL_SECONDS = 25


@router.websocket("/applications/ws")
async def stream_application_updates(websocket: WebSocket) -> None:
    settings = _get_settings(websocket)
    principal = _authenticate_websocket_principal(websocket, settings)
    if principal is None:
        await websocket.accept()
        await websocket.close(code=_WS_CLOSE_UNAUTHORIZED, reason="AUTH_REQUIRED")
        return

    if "admin" in principal.roles:
        await websocket.accept()
        await websocket.close(code=_WS_CLOSE_FORBIDDEN, reason="ROLE_FORBIDDEN")
        return

    if not principal.permissions.intersection({"applications:list_own", "applications:list_all"}):
        await websocket.accept()
        await websocket.close(code=_WS_CLOSE_FORBIDDEN, reason="PERMISSION_DENIED")
        return

    if not settings.applications_realtime_enabled:
        await websocket.accept()
        await websocket.close(code=_WS_CLOSE_UNAVAILABLE, reason="REALTIME_DISABLED")
        return

    hub = _get_or_create_hub(websocket)
    queue = await hub.subscribe()
    await websocket.accept()
    try:
        await _stream_updates(websocket, queue, principal)
    except WebSocketDisconnect:
        return
    finally:
        await hub.unsubscribe(queue)


async def _stream_updates(
    websocket: WebSocket,
    queue: asyncio.Queue[ApplicationsRealtimeEnvelope],
    principal: AuthenticatedPrincipal,
) -> None:
    while True:
        try:
            envelope = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            await websocket.send_text(_heartbeat_frame())
            continue

        if principal.is_customer() and envelope.owner_id != principal.user_id:
            continue

        await websocket.send_text(build_realtime_message(envelope))


def _authenticate_websocket_principal(
    websocket: WebSocket,
    settings: Settings,
) -> Optional[AuthenticatedPrincipal]:
    token = _resolve_access_token(websocket)
    if token is None:
        return None

    jwt_codec = JwtCodec(
        JwtCodecConfig(
            secret=settings.auth_jwt_secret,
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            ttl_seconds=settings.auth_jwt_ttl_seconds,
        )
    )
    authorize_request_service = AuthorizeRequestService()
    try:
        claims = jwt_codec.decode_token(token)
        return authorize_request_service.principal_from_claims(claims)
    except AuthError:
        return None


def _resolve_access_token(websocket: WebSocket) -> Optional[str]:
    query_token = (websocket.query_params.get("access_token") or "").strip()
    if query_token:
        return query_token

    authorization = websocket.headers.get("authorization")
    if not authorization:
        return None

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise TokenInvalidError("Authorization header must use Bearer token")
    return parts[1].strip()


def _get_settings(websocket: WebSocket) -> Settings:
    return websocket.app.state.settings


def _get_or_create_hub(websocket: WebSocket) -> ApplicationsRealtimeHub:
    hub = getattr(websocket.app.state, "applications_realtime_hub", None)
    if isinstance(hub, ApplicationsRealtimeHub):
        return hub

    hub = ApplicationsRealtimeHub()
    websocket.app.state.applications_realtime_hub = hub
    return hub


def _heartbeat_frame() -> str:
    payload = {
        "type": "heartbeat",
        "emitted_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(payload, separators=(",", ":"))
