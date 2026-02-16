from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from apps.backend.auth.dependencies import get_password_hasher
from apps.backend.main import create_app
from apps.backend.rate_limit.redis_storage import (
    InMemorySlidingWindowStorage,
    RateLimitStorageUnavailable,
)
from apps.backend.settings import Settings
from tests.auth.fixtures.test_password_hasher import TestPasswordHasher


def test_public_endpoint_rate_limit_returns_429_with_headers(
    settings: Settings,
    session_factory,
) -> None:
    strict_settings = replace(
        settings,
        rate_limit_public_max_requests=2,
        rate_limit_public_window_seconds=60,
    )
    app = create_app(
        settings=strict_settings,
        session_factory=session_factory,
        rate_limit_storage=InMemorySlidingWindowStorage(),
    )
    client = _client_with_password_hasher_override(app)

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200

    response = client.get("/health")

    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in response.headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


def test_login_endpoint_uses_stricter_limit(
    settings: Settings,
    session_factory,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    strict_settings = replace(
        settings,
        rate_limit_login_ip_max_requests=5,
        rate_limit_login_ip_window_seconds=60,
        rate_limit_login_email_ip_max_requests=1,
        rate_limit_login_email_ip_window_seconds=300,
    )
    app = create_app(
        settings=strict_settings,
        session_factory=session_factory,
        rate_limit_storage=InMemorySlidingWindowStorage(),
    )
    client = _client_with_password_hasher_override(app)

    first = client.post("/auth/login", json=seeded_users["customer"])
    second = client.post("/auth/login", json=seeded_users["customer"])

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "RATE_LIMIT_EXCEEDED"


class UnavailableStorage:
    async def check_and_increment(self, **kwargs):
        raise RateLimitStorageUnavailable()


def test_redis_unavailable_login_fails_closed(
    settings: Settings,
    session_factory,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    app = create_app(
        settings=settings,
        session_factory=session_factory,
        rate_limit_storage=UnavailableStorage(),
    )
    client = _client_with_password_hasher_override(app)

    response = client.post("/auth/login", json=seeded_users["customer"])

    assert response.status_code == 503
    assert response.json()["code"] == "RATE_LIMITER_UNAVAILABLE"


def test_redis_unavailable_public_routes_fail_open(settings: Settings, session_factory) -> None:
    app = create_app(
        settings=settings,
        session_factory=session_factory,
        rate_limit_storage=UnavailableStorage(),
    )
    client = _client_with_password_hasher_override(app)

    response = client.get("/health")

    assert response.status_code == 200


def _client_with_password_hasher_override(app) -> TestClient:
    app.dependency_overrides[get_password_hasher] = lambda: TestPasswordHasher()
    return TestClient(app)
