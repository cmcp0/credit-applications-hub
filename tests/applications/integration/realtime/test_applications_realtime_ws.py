from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


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


def test_realtime_socket_requires_authentication(client: TestClient) -> None:
    with client.websocket_connect("/api/realtime/applications/ws") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()
    assert exc_info.value.code == 4401


def test_realtime_socket_denies_admin_role(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    admin_token = _token_for(
        client,
        seeded_users["admin"]["email"],
        seeded_users["admin"]["password"],
    )

    with client.websocket_connect(
        f"/api/realtime/applications/ws?access_token={admin_token}"
    ) as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()
    assert exc_info.value.code == 4403


def test_customer_receives_own_status_update_event(
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

    with client.websocket_connect(
        f"/api/realtime/applications/ws?access_token={customer_token}"
    ) as websocket:
        update_response = client.patch(
            f"/api/applications/{application_id}/status",
            json={
                "status": "APPROVED",
                "reason_code": "MANUAL_REVIEW_COMPLETED",
                "expected_version": 1,
            },
            headers={"Authorization": f"Bearer {operation_token}"},
        )
        assert update_response.status_code == 200

        approved_event = None
        for _ in range(3):
            frame = websocket.receive_json()
            if not isinstance(frame, dict):
                continue

            event = frame.get("event")
            if not isinstance(event, dict):
                continue
            application = event.get("application")
            if not isinstance(application, dict):
                continue
            if application.get("id") != application_id:
                continue
            if application.get("status_code") != "APPROVED":
                continue
            approved_event = event
            break

        assert approved_event is not None
        assert approved_event["version"] == 2
