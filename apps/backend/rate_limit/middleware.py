from __future__ import annotations

import json
import logging
from typing import Optional
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from apps.backend.rate_limit.key_builder import (
    client_ip,
    login_email_ip_key,
    login_ip_key,
    public_key,
)
from apps.backend.rate_limit.policies import resolve_policies
from apps.backend.rate_limit.redis_storage import (
    RateLimitStorageUnavailable,
    RedisSlidingWindowStorage,
)
from apps.backend.settings import Settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        settings: Settings,
        storage: RedisSlidingWindowStorage,
    ) -> None:
        super().__init__(app)
        self._settings = settings
        self._storage = storage

    async def dispatch(self, request: Request, call_next):
        if not self._settings.rate_limit_enabled:
            return await call_next(request)

        route_template = _resolve_route_template(request)
        resolved_policies = resolve_policies(
            path=request.url.path,
            method=request.method,
            route_template=route_template,
            settings=self._settings,
        )

        if resolved_policies is None:
            return await call_next(request)

        ip_address = client_ip(request)
        normalized_email = None
        if resolved_policies.is_login_route:
            request, body_payload = await _read_json_body(request)
            email_value = body_payload.get("email") if isinstance(body_payload, dict) else None
            if isinstance(email_value, str):
                normalized_email = email_value.strip().lower()

        for policy in resolved_policies.policies:
            try:
                rate_key = _build_key(
                    policy_name=policy.name,
                    route_template=route_template,
                    ip_address=ip_address,
                    normalized_email=normalized_email,
                    settings=self._settings,
                )
                result = await self._storage.check_and_increment(
                    key=rate_key,
                    window_seconds=policy.window_seconds,
                    max_requests=policy.max_requests,
                )
            except RateLimitStorageUnavailable:
                if policy.fail_closed_on_storage_error:
                    return JSONResponse(
                        status_code=503,
                        content={
                            "code": "RATE_LIMITER_UNAVAILABLE",
                            "message": "Rate limiter is unavailable",
                        },
                    )

                logger.error(
                    "rate_limiter_unavailable",
                    extra={
                        "route": route_template,
                        "ip": ip_address,
                        "policy": policy.name,
                    },
                )
                continue

            if not result.allowed:
                headers = {
                    "Retry-After": str(result.retry_after_seconds),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_epoch_seconds),
                }
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                    },
                    headers=headers,
                )

        return await call_next(request)


def _build_key(
    *,
    policy_name: str,
    route_template: str,
    ip_address: str,
    normalized_email: Optional[str],
    settings: Settings,
) -> str:
    if policy_name == "login_ip":
        return login_ip_key(ip_address)

    if policy_name == "login_email_ip":
        safe_email = normalized_email or "unknown"
        return login_email_ip_key(safe_email, ip_address, settings.rate_limit_key_pepper)

    return public_key(route_template, ip_address)


async def _read_json_body(request: Request) -> tuple[Request, dict[str, Any]]:
    body = await request.body()

    async def receive() -> dict[str, Any]:
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    cloned_request = Request(request.scope, receive)

    if not body:
        return cloned_request, {}

    try:
        return cloned_request, json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return cloned_request, {}


def _resolve_route_template(request: Request) -> str:
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL and hasattr(route, "path"):
            return route.path
    return request.url.path
