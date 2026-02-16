from __future__ import annotations

from fastapi.testclient import TestClient

from apps.backend.auth.jwt_codec import JwtCodec, JwtCodecConfig
from apps.backend.settings import Settings


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_success(client: TestClient, seeded_users: dict[str, dict[str, str]]) -> None:
    response = client.post("/auth/login", json=seeded_users["customer"])

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
    assert "access_token" in data
    assert "password_hash" not in data


def test_login_invalid_credentials_returns_401(client: TestClient, seeded_users: dict[str, dict[str, str]]) -> None:
    response = client.post(
        "/auth/login",
        json={"email": seeded_users["customer"]["email"], "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_login_inactive_returns_403(client: TestClient, seeded_users: dict[str, dict[str, str]]) -> None:
    response = client.post("/auth/login", json=seeded_users["inactive"])

    assert response.status_code == 403
    assert response.json()["code"] == "USER_INACTIVE"


def test_private_routes_require_bearer(client: TestClient) -> None:
    response = client.get("/api/applications")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_HEADER_MISSING"


def test_private_routes_reject_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/applications",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_INVALID"


def test_private_routes_reject_tampered_token(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    valid_token = _login(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )
    tampered_token = f"{valid_token[:-1]}{'a' if valid_token[-1] != 'a' else 'b'}"

    response = client.get(
        "/api/applications",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_INVALID"


def test_private_routes_reject_expired_token(client: TestClient, settings: Settings) -> None:
    codec = JwtCodec(
        JwtCodecConfig(
            secret=settings.auth_jwt_secret,
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            ttl_seconds=-5,
        )
    )
    token = codec.issue_token(
        subject="expired-user",
        roles=["customer"],
        permissions=["applications:list_own"],
    ).access_token

    response = client.get(
        "/api/applications",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_EXPIRED"


def test_private_routes_accept_valid_token(client: TestClient, seeded_users: dict[str, dict[str, str]]) -> None:
    token = _login(client, seeded_users["customer"]["email"], seeded_users["customer"]["password"])

    response = client.get("/api/applications", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert isinstance(response.json(), list)
