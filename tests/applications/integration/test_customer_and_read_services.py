from __future__ import annotations

from fastapi.testclient import TestClient

from apps.backend.auth.jwt_codec import JwtCodec, JwtCodecConfig
from apps.backend.settings import Settings


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_application(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/applications",
        json={
            "country": "MX",
            "full_name": "Jane Doe",
            "identity_document": "ABC123456",
            "requested_amount": 5000,
            "monthly_income": 2500,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_customer_create_list_and_get_detail(client: TestClient, seeded_users: dict[str, dict[str, str]]) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )

    create_response = client.post(
        "/api/applications",
        json={
            "country": "MX",
            "full_name": "Jane Doe",
            "identity_document": "ABC123456",
            "requested_amount": 5000,
            "monthly_income": 2500,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    assert create_response.status_code == 201
    assert set(create_response.json().keys()) == {"id", "country", "status_code", "created_at"}
    application_id = create_response.json()["id"]

    list_response = client.get(
        "/api/applications?country=MX&status=PENDING_REVIEW&page=1&page_size=20",
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] == 1
    assert list_body["page"] == 1
    assert list_body["page_size"] == 20
    assert list_body["items"][0]["id"] == application_id

    detail_response = client.get(
        f"/api/applications/{application_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert detail_response.status_code == 200

    detail = detail_response.json()
    assert detail["id"] == application_id
    assert detail["status_code"] == "PENDING_REVIEW"
    assert set(detail["status_metadata"]["allowed_transitions"]) == {"APPROVED", "REJECTED"}


def test_customer_cannot_read_other_customer_application(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    settings: Settings,
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )
    application_id = _create_application(client, customer_token)

    codec = JwtCodec(
        JwtCodecConfig(
            secret=settings.auth_jwt_secret,
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            ttl_seconds=settings.auth_jwt_ttl_seconds,
        )
    )
    other_customer_token = codec.issue_token(
        subject="55555555-5555-5555-5555-555555555555",
        roles=["customer"],
        permissions=["applications:list_own"],
    ).access_token

    detail_response = client.get(
        f"/api/applications/{application_id}",
        headers={"Authorization": f"Bearer {other_customer_token}"},
    )

    assert detail_response.status_code == 404
    assert detail_response.json()["code"] == "APPLICATION_NOT_FOUND"


def test_es_dni_verification_and_additional_review_threshold(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )

    invalid_dni_response = client.post(
        "/api/applications",
        json={
            "country": "ES",
            "full_name": "Jane Doe",
            "identity_document": "12345678A",
            "requested_amount": 11000,
            "monthly_income": 3500,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert invalid_dni_response.status_code == 400
    assert invalid_dni_response.json()["code"] == "VALIDATION_ERROR"
    assert any(
        error["code"] == "INVALID_VERIFICATION"
        for error in invalid_dni_response.json().get("errors", [])
    )

    valid_high_amount_response = client.post(
        "/api/applications",
        json={
            "country": "ES",
            "full_name": "Jane Doe",
            "identity_document": "12345678Z",
            "requested_amount": 13000,
            "monthly_income": 3500,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert valid_high_amount_response.status_code == 201
    assert valid_high_amount_response.json()["status_code"] == "ADDITIONAL_REVIEW"
