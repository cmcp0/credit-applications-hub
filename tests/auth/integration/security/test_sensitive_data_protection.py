from __future__ import annotations

from fastapi.testclient import TestClient

from apps.backend.auth.jwt_codec import JwtCodec, JwtCodecConfig
from apps.backend.security.pii_redaction import redact_headers, redact_payload
from apps.backend.settings import Settings


def test_login_response_uses_allowlist_fields(client: TestClient, seeded_users: dict[str, dict[str, str]]) -> None:
    response = client.post("/auth/login", json=seeded_users["customer"])

    assert response.status_code == 200
    assert set(response.json().keys()) == {"access_token", "token_type", "expires_in"}


def test_jwt_claims_exclude_pii(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    settings: Settings,
) -> None:
    response = client.post("/auth/login", json=seeded_users["customer"])
    token = response.json()["access_token"]

    codec = JwtCodec(
        JwtCodecConfig(
            secret=settings.auth_jwt_secret,
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            ttl_seconds=settings.auth_jwt_ttl_seconds,
        )
    )
    claims = codec.decode_token(token)

    assert "email" not in claims
    assert "identity_document" not in claims
    assert "monthly_income" not in claims
    assert "sub" in claims
    assert "roles" in claims
    assert "permissions" in claims


def test_redaction_masks_sensitive_fields() -> None:
    payload = {
        "email": "user@example.com",
        "password": "secret",
        "authorization": "Bearer token",
        "profile": {
            "identity_document": "ABC123",
            "monthly_income": 1200,
        },
    }

    redacted = redact_payload(payload)
    headers = redact_headers({"authorization": "Bearer token", "x-request-id": "1"})

    assert redacted["password"] == "***REDACTED***"
    assert redacted["authorization"] == "***REDACTED***"
    assert redacted["profile"]["identity_document"] == "***REDACTED***"
    assert redacted["profile"]["monthly_income"] == "***REDACTED***"
    assert headers["authorization"] == "***REDACTED***"
