from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from src.applications.application.infrastructure.adapters.application_status_history_orm_model import (
    ApplicationStatusHistoryOrm,
)
from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_application(client: TestClient, customer_token: str) -> str:
    response = client.post(
        "/api/applications",
        json={
            "country": "BR",
            "full_name": "Customer Review",
            "identity_document": "12345678901",
            "requested_amount": 5000,
            "monthly_income": 2500,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_status_transition_invalid_and_version_conflict(
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
    application_id = _create_application(client, customer_token)

    conflict_response = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "APPROVED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 9},
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert conflict_response.status_code == 409
    assert conflict_response.json()["code"] == "VERSION_CONFLICT"

    first_transition = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "APPROVED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 1},
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert first_transition.status_code == 200

    invalid_transition = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "REJECTED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 2},
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["code"] == "INVALID_STATUS_TRANSITION"


def test_status_transition_idempotent_by_command_id(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
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
    application_id = _create_application(client, customer_token)

    command_id = str(uuid.uuid4())
    first = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "APPROVED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 1},
        headers={
            "Authorization": f"Bearer {operation_token}",
            "X-Command-Id": command_id,
            "X-Correlation-Id": str(uuid.uuid4()),
            "X-Request-Id": str(uuid.uuid4()),
        },
    )
    second = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "APPROVED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 1},
        headers={
            "Authorization": f"Bearer {operation_token}",
            "X-Command-Id": command_id,
            "X-Correlation-Id": str(uuid.uuid4()),
            "X-Request-Id": str(uuid.uuid4()),
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status_code"] == "APPROVED"
    assert second.json()["status_code"] == "APPROVED"

    with session_factory() as session:
        history_rows = session.execute(
            select(ApplicationStatusHistoryOrm).where(
                ApplicationStatusHistoryOrm.application_id == uuid.UUID(application_id)
            )
        ).scalars().all()
        status_updated_events = session.execute(
            select(OutboxEventOrm).where(
                OutboxEventOrm.aggregate_id == uuid.UUID(application_id),
                OutboxEventOrm.event_name == "ApplicationStatusUpdated",
            )
        ).scalars().all()

    assert len(history_rows) == 1
    assert len(status_updated_events) == 1


def test_status_transition_same_target_is_idempotent_even_with_stale_expected_version(
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
    application_id = _create_application(client, customer_token)

    first = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "APPROVED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 1},
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert first.status_code == 200

    second = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "APPROVED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 999},
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert second.status_code == 200
    assert second.json()["status_code"] == "APPROVED"
