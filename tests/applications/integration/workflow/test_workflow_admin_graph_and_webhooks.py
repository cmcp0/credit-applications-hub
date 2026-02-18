from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.applications.execution.infrastructure.adapters.execution_orm_model import WorkerJobOrm
from src.applications.workflow.infrastructure.adapters.workflow_orm_model import WebhookEventOrm


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_workflow_draft(
    client: TestClient,
    token: str,
    *,
    country: str,
    version: int,
) -> dict[str, object]:
    response = client.post(
        "/api/workflows",
        json={
            "country": country,
            "version": version,
            "statuses": [
                {
                    "code": "PENDING_REVIEW",
                    "label": "Pending review",
                    "is_initial": True,
                    "is_terminal": False,
                    "sort_order": 1,
                },
                {
                    "code": "APPROVED",
                    "label": "Approved",
                    "is_initial": False,
                    "is_terminal": True,
                    "sort_order": 2,
                },
                {
                    "code": "REJECTED",
                    "label": "Rejected",
                    "is_initial": False,
                    "is_terminal": True,
                    "sort_order": 3,
                },
            ],
            "transitions": [
                {"from": "PENDING_REVIEW", "to": "APPROVED"},
                {"from": "PENDING_REVIEW", "to": "REJECTED"},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_admin_upserts_workflow_graph_and_blocks_post_publish_edits(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    admin_token = _token_for(
        client,
        seeded_users["admin"]["email"],
        seeded_users["admin"]["password"],
    )
    created = _create_workflow_draft(client, admin_token, country="MX", version=2)
    workflow_id = str(created["id"])

    upsert_response = client.put(
        f"/api/workflows/{workflow_id}/graph",
        json={
            "expected_version": 2,
            "operations": [
                {
                    "name": "provider_enrichment",
                    "sort_order": 1,
                    "active": True,
                    "sub_operations": [
                        {
                            "sort_order": 1,
                            "execution_type": "THIRD_PARTY_HTTP_REQUEST",
                            "target_ref": "webhook_endpoint:11111111-1111-1111-1111-111111111111",
                            "input_template": {"application_id": "{{ application.id }}"},
                            "output_alias": "provider_response",
                            "active": True,
                            "triggers": [
                                {
                                    "trigger_type": "TRIGGER_EVENT",
                                    "trigger_name": "credit.workflow.execution.completed",
                                    "payload_template": {},
                                }
                            ],
                        }
                    ],
                }
            ],
            "deleted_operation_ids": [],
            "deleted_sub_operation_ids": [],
            "deleted_trigger_ids": [],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert upsert_response.status_code == 200
    body = upsert_response.json()
    assert body["workflow_id"] == workflow_id
    assert body["graph_revision"] == 1
    assert body["counts"]["operations"] == 1
    assert body["counts"]["sub_operations"] == 1
    assert body["counts"]["triggers"] == 1
    assert body["etag"].startswith('W/"workflow:')

    publish_response = client.post(
        f"/api/workflows/{workflow_id}/publish",
        json={"expected_version": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200

    post_publish_upsert = client.put(
        f"/api/workflows/{workflow_id}/graph",
        json={
            "expected_version": 2,
            "operations": [],
            "deleted_operation_ids": [],
            "deleted_sub_operation_ids": [],
            "deleted_trigger_ids": [],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert post_publish_upsert.status_code == 409
    assert post_publish_upsert.json()["code"] == "WORKFLOW_NOT_DRAFT"


def test_admin_manages_webhook_endpoint_lifecycle(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
) -> None:
    admin_token = _token_for(
        client,
        seeded_users["admin"]["email"],
        seeded_users["admin"]["password"],
    )
    created = _create_workflow_draft(client, admin_token, country="BR", version=2)
    workflow_id = str(created["id"])

    create_endpoint_response = client.post(
        f"/api/workflows/{workflow_id}/webhooks/endpoints",
        json={
            "direction": "EGRESS",
            "provider_code": "provider_x",
            "event_type": "ApplicationStatusUpdated",
            "method": "POST",
            "url": "https://provider.example/webhooks/status",
            "secret_ref": "secrets://webhooks/provider_x/status",
            "timeout_ms": 5000,
            "active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_endpoint_response.status_code == 201
    endpoint_id = create_endpoint_response.json()["endpoint_id"]

    update_response = client.patch(
        f"/api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}",
        json={
            "active": False,
            "timeout_ms": 7000,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["active"] is False
    assert update_response.json()["workflow_id"] == workflow_id

    rotate_response = client.post(
        f"/api/workflows/{workflow_id}/webhooks/endpoints/{endpoint_id}/rotate-secret",
        json={"reason": "scheduled_rotation_q1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rotate_response.status_code == 200
    assert "/rotated/" in rotate_response.json()["secret_ref"]


def test_admin_replay_webhook_event_duplicate_and_cooldown_controls(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
) -> None:
    admin_user_id = uuid.UUID("44444444-4444-4444-4444-444444444443")
    admin_token = _token_for(
        client,
        seeded_users["admin"]["email"],
        seeded_users["admin"]["password"],
    )
    created = _create_workflow_draft(client, admin_token, country="CO", version=2)
    workflow_id = str(created["id"])

    create_endpoint_response = client.post(
        f"/api/workflows/{workflow_id}/webhooks/endpoints",
        json={
            "direction": "EGRESS",
            "provider_code": "provider_y",
            "event_type": "ApplicationStatusUpdated",
            "method": "POST",
            "url": "https://provider.example/webhooks/status",
            "secret_ref": "secrets://webhooks/provider_y/status",
            "timeout_ms": 5000,
            "active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_endpoint_response.status_code == 201
    endpoint_id = uuid.UUID(create_endpoint_response.json()["endpoint_id"])

    webhook_event_id = uuid.uuid4()
    with session_factory() as session:
        session.add(
            WebhookEventOrm(
                id=webhook_event_id,
                endpoint_id=endpoint_id,
                workflow_id=uuid.UUID(workflow_id),
                application_id=None,
                provider_code="provider_y",
                direction="EGRESS",
                event_type="ApplicationStatusUpdated",
                payload={"status": "APPROVED"},
                payload_hash="sha256:test",
                signature_valid=None,
                external_event_id=None,
                correlation_id=uuid.uuid4(),
                delivery_status="FAILED",
                occurred_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    first_command_id = uuid.uuid4()
    replay_response = client.post(
        f"/api/workflows/{workflow_id}/webhooks/events/{webhook_event_id}/replay",
        json={
            "command_id": str(first_command_id),
            "reason": "manual_replay_after_provider_fix",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert replay_response.status_code == 202
    assert replay_response.json()["queued"] is True

    duplicate_command_response = client.post(
        f"/api/workflows/{workflow_id}/webhooks/events/{webhook_event_id}/replay",
        json={
            "command_id": str(first_command_id),
            "reason": "manual_replay_after_provider_fix",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert duplicate_command_response.status_code == 409
    assert duplicate_command_response.json()["code"] == "REPLAY_COMMAND_DUPLICATE"

    cooldown_response = client.post(
        f"/api/workflows/{workflow_id}/webhooks/events/{webhook_event_id}/replay",
        json={
            "command_id": str(uuid.uuid4()),
            "reason": "manual_replay_after_provider_fix",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cooldown_response.status_code == 409
    assert cooldown_response.json()["code"] == "REPLAY_COOLDOWN_ACTIVE"


def test_admin_execution_and_webhook_queries_support_filters_sorting_and_validation(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
) -> None:
    admin_token = _token_for(
        client,
        seeded_users["admin"]["email"],
        seeded_users["admin"]["password"],
    )
    created = _create_workflow_draft(client, admin_token, country="PE", version=2)
    workflow_id = str(created["id"])

    create_endpoint_response = client.post(
        f"/api/workflows/{workflow_id}/webhooks/endpoints",
        json={
            "direction": "EGRESS",
            "provider_code": "provider_q",
            "event_type": "ApplicationStatusUpdated",
            "method": "POST",
            "url": "https://provider.example/webhooks/status",
            "secret_ref": "secrets://webhooks/provider_q/status",
            "timeout_ms": 5000,
            "active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_endpoint_response.status_code == 201
    endpoint_id = uuid.UUID(create_endpoint_response.json()["endpoint_id"])
    workflow_uuid = uuid.UUID(workflow_id)

    with session_factory() as session:
        now = datetime.now(timezone.utc)
        older = now.replace(minute=max(0, now.minute - 1))
        session.add_all(
            [
                WebhookEventOrm(
                    id=uuid.uuid4(),
                    endpoint_id=endpoint_id,
                    workflow_id=workflow_uuid,
                    application_id=None,
                    provider_code="provider_q",
                    direction="EGRESS",
                    event_type="ApplicationStatusUpdated",
                    payload={"status": "APPROVED"},
                    payload_hash="sha256:event-1",
                    signature_valid=None,
                    external_event_id=None,
                    correlation_id=uuid.uuid4(),
                    delivery_status="FAILED",
                    occurred_at=older,
                    created_at=older,
                ),
                WebhookEventOrm(
                    id=uuid.uuid4(),
                    endpoint_id=endpoint_id,
                    workflow_id=workflow_uuid,
                    application_id=None,
                    provider_code="provider_q",
                    direction="INGRESS",
                    event_type="ProviderCallback",
                    payload={"status": "OK"},
                    payload_hash="sha256:event-2",
                    signature_valid=True,
                    external_event_id=None,
                    correlation_id=uuid.uuid4(),
                    delivery_status="RECEIVED",
                    occurred_at=now,
                    created_at=now,
                ),
            ]
        )
        session.add_all(
            [
                WorkerJobOrm(
                    id=uuid.uuid4(),
                    workflow_id=workflow_uuid,
                    workflow_revision=2,
                    application_id=None,
                    operation_id=None,
                    sub_operation_id=None,
                    status="FAILED",
                    idempotency_key=f"job:{workflow_id}:failed",
                    payload_summary={"redacted": True},
                    attempts=3,
                    max_attempts=5,
                    available_at=older,
                    locked_at=None,
                    completed_at=None,
                    last_error_code="HTTP_TIMEOUT",
                    last_error_message="provider timeout",
                    correlation_id=uuid.uuid4(),
                    created_at=older,
                    updated_at=older,
                ),
                WorkerJobOrm(
                    id=uuid.uuid4(),
                    workflow_id=workflow_uuid,
                    workflow_revision=2,
                    application_id=None,
                    operation_id=None,
                    sub_operation_id=None,
                    status="SUCCEEDED",
                    idempotency_key=f"job:{workflow_id}:succeeded",
                    payload_summary={"redacted": True},
                    attempts=1,
                    max_attempts=5,
                    available_at=now,
                    locked_at=None,
                    completed_at=now,
                    last_error_code=None,
                    last_error_message=None,
                    correlation_id=uuid.uuid4(),
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()

    webhooks_response = client.get(
        f"/api/workflows/{workflow_id}/webhooks/events",
        params={
            "direction": "EGRESS",
            "delivery_status": "FAILED",
            "sort_by": "created_at",
            "sort_dir": "asc",
            "page": 1,
            "page_size": 20,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert webhooks_response.status_code == 200
    webhooks_body = webhooks_response.json()
    assert webhooks_body["total"] == 1
    assert webhooks_body["items"][0]["direction"] == "EGRESS"
    assert webhooks_body["items"][0]["delivery_status"] == "FAILED"
    assert webhooks_body["sort_by"] == "created_at"
    assert webhooks_body["sort_dir"] == "asc"

    invalid_webhook_query = client.get(
        f"/api/workflows/{workflow_id}/webhooks/events",
        params={"sort_by": "updated_at"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert invalid_webhook_query.status_code == 422
    assert invalid_webhook_query.json()["code"] == "INVALID_QUERY_PARAMS"

    executions_response = client.get(
        f"/api/workflows/{workflow_id}/executions",
        params={
            "status": "FAILED",
            "sort_by": "available_at",
            "sort_dir": "asc",
            "page": 1,
            "page_size": 20,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert executions_response.status_code == 200
    executions_body = executions_response.json()
    assert executions_body["total"] == 1
    assert executions_body["items"][0]["status"] == "FAILED"
    assert executions_body["items"][0]["payload_summary"]["redacted"] is True
    assert executions_body["sort_by"] == "available_at"
    assert executions_body["sort_dir"] == "asc"

    invalid_execution_query = client.get(
        f"/api/workflows/{workflow_id}/executions",
        params={"application_id": "invalid-uuid"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert invalid_execution_query.status_code == 422
    assert invalid_execution_query.json()["code"] == "INVALID_QUERY_PARAMS"
