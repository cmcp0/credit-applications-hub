from __future__ import annotations

from fastapi.testclient import TestClient


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_list_and_detail_responses_exclude_sensitive_fields(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )

    create_response = client.post(
        "/api/applications",
        json={
            "country": "MX",
            "full_name": "Sensitive Name",
            "identity_document": "ABC123456",
            "requested_amount": 4500,
            "monthly_income": 2300,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]

    list_response = client.get(
        "/api/applications",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert list_response.status_code == 200
    listed_item = list_response.json()["items"][0]

    detail_response = client.get(
        f"/api/applications/{application_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert detail_response.status_code == 200
    detail_item = detail_response.json()

    for sensitive_field in ("identity_document", "monthly_income", "full_name"):
        assert sensitive_field not in listed_item
        assert sensitive_field not in detail_item


def test_create_returns_structured_validation_errors(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )

    response = client.post(
        "/api/applications",
        json={
            "country": "MX",
            "full_name": "AA",
            "identity_document": "12",
            "requested_amount": -1,
            "monthly_income": 0,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Validation failed"
    assert isinstance(body["errors"], list)
    fields = {entry["field"] for entry in body["errors"]}
    assert {"full_name", "identity_document", "requested_amount", "monthly_income"}.issubset(fields)
