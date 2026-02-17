from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm
from src.applications.shared.infrastructure.adapters.outbox_event_publisher import (
    InMemoryExchangePublisher,
    OutboxEventPublisher,
)


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _publish_outbox_events(session_factory) -> None:
    outbox_publisher = OutboxEventPublisher(
        session_factory=session_factory,
        exchange_publisher=InMemoryExchangePublisher(),
    )
    outbox_publisher.publish_cycle(limit=100)


def test_application_created_event_contract_is_versioned_and_pii_safe(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )
    request_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())

    create_response = client.post(
        "/api/applications",
        json={
            "country": "MX",
            "full_name": "Jane Doe",
            "identity_document": "ABC123456",
            "requested_amount": 7000,
            "monthly_income": 3200,
        },
        headers={
            "Authorization": f"Bearer {customer_token}",
            "X-Request-Id": request_id,
            "X-Correlation-Id": correlation_id,
        },
    )
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]
    _publish_outbox_events(session_factory)

    with session_factory() as session:
        outbox_event = session.execute(
            select(OutboxEventOrm).where(
                OutboxEventOrm.aggregate_id == uuid.UUID(application_id),
                OutboxEventOrm.event_name == "ApplicationCreated",
            )
        ).scalar_one()

    payload = outbox_event.payload
    assert payload["event_name"] == "ApplicationCreated"
    assert payload["schema_version"] == "v1"
    assert payload["request_id"] == request_id
    assert payload["correlation_id"] == correlation_id
    assert payload["event_id"]
    assert payload["occurred_at"]
    assert payload["payload"]["application_id"] == application_id
    assert payload["payload"]["status_code"] == "PENDING_REVIEW"
    assert "identity_document" not in payload["payload"]
    assert "monthly_income" not in payload["payload"]
    assert "full_name" not in payload["payload"]
    assert outbox_event.exchange_name == "applications.events"
    assert outbox_event.routing_key == "credit.application.created"
    assert outbox_event.publish_status == "PUBLISHED"


def test_application_status_updated_event_contract_is_versioned_and_pii_safe(
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

    create_response = client.post(
        "/api/applications",
        json={
            "country": "BR",
            "full_name": "Jane Doe",
            "identity_document": "12345678901",
            "requested_amount": 7000,
            "monthly_income": 3200,
        },
        headers={
            "Authorization": f"Bearer {customer_token}",
            "X-Request-Id": str(uuid.uuid4()),
            "X-Correlation-Id": str(uuid.uuid4()),
        },
    )
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]

    correlation_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    update_response = client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "APPROVED", "reason_code": "MANUAL_REVIEW_COMPLETED", "expected_version": 1},
        headers={
            "Authorization": f"Bearer {operation_token}",
            "X-Request-Id": request_id,
            "X-Correlation-Id": correlation_id,
            "X-Command-Id": str(uuid.uuid4()),
        },
    )
    assert update_response.status_code == 200
    _publish_outbox_events(session_factory)

    with session_factory() as session:
        outbox_event = session.execute(
            select(OutboxEventOrm).where(
                OutboxEventOrm.aggregate_id == uuid.UUID(application_id),
                OutboxEventOrm.event_name == "ApplicationStatusUpdated",
            )
        ).scalar_one()

    payload = outbox_event.payload
    assert payload["event_name"] == "ApplicationStatusUpdated"
    assert payload["schema_version"] == "v1"
    assert payload["request_id"] == request_id
    assert payload["correlation_id"] == correlation_id
    assert payload["payload"]["application_id"] == application_id
    assert payload["payload"]["previous_status_code"] == "PENDING_REVIEW"
    assert payload["payload"]["current_status_code"] == "APPROVED"
    assert payload["payload"]["actor_role"] == "operation"
    assert "identity_document" not in payload["payload"]
    assert "monthly_income" not in payload["payload"]
    assert "full_name" not in payload["payload"]
    assert outbox_event.exchange_name == "applications.events"
    assert outbox_event.routing_key == "credit.application.status.updated"
    assert outbox_event.publish_status == "PUBLISHED"
