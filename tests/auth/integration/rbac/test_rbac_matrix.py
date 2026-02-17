from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from src.applications.application.infrastructure.adapters.application_orm_model import ApplicationOrm
from tests.auth.fixtures.seed import TEST_USERS


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_customer_create_and_list_own_only(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
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
            "full_name": "Customer One",
            "identity_document": "ABC123456",
            "requested_amount": 2000,
            "monthly_income": 4000,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert create_response.status_code == 201
    customer_application_id = create_response.json()["id"]

    with session_factory() as session:
        session.add(
            ApplicationOrm(
                id=uuid.uuid4(),
                user_id=TEST_USERS["operation"]["id"],
                country="CO",
                full_name="Other User",
                identity_document="ABC9999",
                requested_amount=4000,
                monthly_income=5000,
                application_date=date.today(),
                status_code="PENDING_REVIEW",
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    list_response = client.get(
        "/api/applications",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert list_response.status_code == 200

    listed_ids = {item["id"] for item in list_response.json()["items"]}
    assert listed_ids == {customer_application_id}


def test_operation_can_list_all_and_update_status(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )
    operation_token = _token_for(
        client,
        seeded_users["operation"]["email"],
        seeded_users["operation"]["password"],
    )

    create_response = client.post(
        "/api/applications",
        json={
            "country": "BR",
            "full_name": "Customer Two",
            "identity_document": "12345678901",
            "requested_amount": 1000,
            "monthly_income": 3000,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    app_id = create_response.json()["id"]

    list_response = client.get(
        "/api/applications",
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert list_response.status_code == 200
    assert any(item["id"] == app_id for item in list_response.json()["items"])

    status_response = client.patch(
        f"/api/applications/{app_id}/status",
        json={
            "status": "APPROVED",
            "reason_code": "MANUAL_REVIEW_COMPLETED",
            "expected_version": 1,
        },
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["previous_status_code"] == "PENDING_REVIEW"
    assert body["status_code"] == "APPROVED"
    assert body["version"] == 2


def test_admin_permissions_are_explicit_not_inherited(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    admin_token = _token_for(
        client,
        seeded_users["admin"]["email"],
        seeded_users["admin"]["password"],
    )

    users_response = client.get(
        "/api/users/operations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    workflows_response = client.get(
        "/api/workflows",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    status_response = client.patch(
        "/api/applications/00000000-0000-0000-0000-000000000000/status",
        json={"status": "APPROVED", "expected_version": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert users_response.status_code == 200
    assert workflows_response.status_code == 200
    assert status_response.status_code == 403
    assert status_response.json()["code"] == "PERMISSION_DENIED"
