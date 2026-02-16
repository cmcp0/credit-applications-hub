from __future__ import annotations

from fastapi.testclient import TestClient


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_customer_create_and_list_own_only(client: TestClient, seeded_users: dict[str, dict[str, str]]) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )

    create_response = client.post(
        "/api/applications",
        json={"country": "MX", "requested_amount": 2000},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert create_response.status_code == 200

    client.app.state.applications_store.append(
        {
            "id": "app-external",
            "country": "CO",
            "requested_amount": 4000,
            "owner_id": "other-user",
            "status": "created",
        }
    )

    list_response = client.get(
        "/api/applications",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert list_response.status_code == 200

    listed_ids = {item["id"] for item in list_response.json()}
    assert "app-external" not in listed_ids


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
        json={"country": "BR", "requested_amount": 1000},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    app_id = create_response.json()["id"]

    list_response = client.get(
        "/api/applications",
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert list_response.status_code == 200
    assert any(item["id"] == app_id for item in list_response.json())

    status_response = client.patch(
        f"/api/applications/{app_id}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {operation_token}"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "approved"


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
        "/api/applications/app-unknown/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert users_response.status_code == 200
    assert workflows_response.status_code == 200
    assert status_response.status_code == 403
    assert status_response.json()["code"] == "PERMISSION_DENIED"

