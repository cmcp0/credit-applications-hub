from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.backend.settings import Settings


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    max_requests: int
    window_seconds: int
    fail_closed_on_storage_error: bool


@dataclass(frozen=True)
class ResolvedPolicies:
    route_template: str
    policies: tuple[RateLimitPolicy, ...]
    is_login_route: bool


def resolve_policies(
    path: str,
    method: str,
    route_template: str,
    settings: Settings,
) -> Optional[ResolvedPolicies]:
    if path == "/auth/login" and method.upper() == "POST":
        return ResolvedPolicies(
            route_template=route_template,
            is_login_route=True,
            policies=(
                RateLimitPolicy(
                    name="login_ip",
                    max_requests=settings.rate_limit_login_ip_max_requests,
                    window_seconds=settings.rate_limit_login_ip_window_seconds,
                    fail_closed_on_storage_error=True,
                ),
                RateLimitPolicy(
                    name="login_email_ip",
                    max_requests=settings.rate_limit_login_email_ip_max_requests,
                    window_seconds=settings.rate_limit_login_email_ip_window_seconds,
                    fail_closed_on_storage_error=True,
                ),
            ),
        )

    if path.startswith("/api"):
        return None

    return ResolvedPolicies(
        route_template=route_template,
        is_login_route=False,
        policies=(
            RateLimitPolicy(
                name="public",
                max_requests=settings.rate_limit_public_max_requests,
                window_seconds=settings.rate_limit_public_window_seconds,
                fail_closed_on_storage_error=False,
            ),
        ),
    )
