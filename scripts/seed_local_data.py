from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from apps.backend.database import create_session_factory
from apps.backend.security.password_hasher import Argon2PasswordHasher
from apps.backend.settings import Settings
from scripts.local_fixtures import (
    FIXTURE_ADMIN_USER_ID,
    LOCAL_PASSWORD,
    LOCAL_USERS,
    PERMISSION_IDS,
    ROLE_IDS,
    WORKFLOW_FIXTURES,
)
from src.applications.workflow.infrastructure.adapters.workflow_orm_model import (
    StatusOrm,
    StatusTransitionOrm,
    WebhookEndpointOrm,
    WorkflowOperationOrm,
    WorkflowOrm,
    WorkflowSubOperationOrm,
    WorkflowSubOperationTriggerOrm,
)
from src.auth.authentication.infrastructure.adapters.auth_user_orm_model import AuthUser
from src.auth.authorization.infrastructure.adapters.rbac_orm_models import (
    AuthPermission,
    AuthRole,
    AuthRolePermission,
    AuthUserRole,
)
from src.auth.authorization.infrastructure.adapters.role_permission_mapper import ROLE_PERMISSION_MAP


def run() -> None:
    settings = Settings.from_env()
    session_factory = create_session_factory(settings.database_url)

    with session_factory() as session:
        seed_users_and_roles(session)
        seed_workflows(session)

    print("Local fixtures seeded successfully.")
    print("Credentials:")
    print(f"- customer@example.com / {LOCAL_PASSWORD}")
    print(f"- operation@example.com / {LOCAL_PASSWORD}")
    print(f"- admin@example.com / {LOCAL_PASSWORD}")


def seed_users_and_roles(session: Session) -> None:
    now = datetime.now(timezone.utc)

    for role_code, role_id in ROLE_IDS.items():
        role = session.get(AuthRole, role_id)
        if role is None:
            session.add(AuthRole(id=role_id, code=role_code, description=f"{role_code} role"))

    for permission_code, permission_id in PERMISSION_IDS.items():
        permission = session.get(AuthPermission, permission_id)
        if permission is None:
            session.add(
                AuthPermission(
                    id=permission_id,
                    code=permission_code,
                    description=f"{permission_code} permission",
                )
            )

    for role_code, permission_codes in ROLE_PERMISSION_MAP.items():
        role_id = ROLE_IDS[role_code]
        for permission_code in permission_codes:
            permission_id = PERMISSION_IDS[permission_code]
            existing = session.get(AuthRolePermission, (role_id, permission_id))
            if existing is None:
                session.add(AuthRolePermission(role_id=role_id, permission_id=permission_id))

    hasher = Argon2PasswordHasher()

    for user in LOCAL_USERS:
        user_id = user["id"]
        auth_user = session.get(AuthUser, user_id)
        if auth_user is None:
            auth_user = AuthUser(
                id=user_id,
                email=user["email"],
                password_hash=hasher.hash_password(LOCAL_PASSWORD),
                is_active=bool(user.get("is_active", True)),
                created_at=now,
                updated_at=now,
                last_login_at=None,
            )
            session.add(auth_user)
        else:
            auth_user.email = user["email"]
            auth_user.is_active = bool(user.get("is_active", True))
            auth_user.updated_at = now

        role_id = ROLE_IDS[str(user["role"])]
        existing_membership = session.get(AuthUserRole, (user_id, role_id))
        if existing_membership is None:
            session.add(AuthUserRole(user_id=user_id, role_id=role_id))

    session.commit()


def seed_workflows(session: Session) -> None:
    now = datetime.now(timezone.utc)
    mock_provider_url = os.getenv(
        "MOCK_CO_BANK_PROVIDER_URL",
        "http://localhost:8085/providers/co/banking-data",
    )

    for fixture in WORKFLOW_FIXTURES:
        workflow = session.get(WorkflowOrm, fixture["workflow_id"])
        if workflow is None:
            workflow = WorkflowOrm(
                id=fixture["workflow_id"],
                country=fixture["country"],
                active=True,
                version=int(fixture["version"]),
                graph_revision=1,
                version_status="PUBLISHED",
                published_by=FIXTURE_ADMIN_USER_ID,
                published_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(workflow)
        else:
            workflow.active = True
            workflow.version = int(fixture["version"])
            workflow.graph_revision = max(1, int(workflow.graph_revision or 0))
            workflow.version_status = "PUBLISHED"
            workflow.published_by = FIXTURE_ADMIN_USER_ID
            workflow.published_at = now
            workflow.updated_at = now

        status_by_code: dict[str, uuid.UUID] = {}
        for status_fixture in fixture["statuses"]:
            status = session.get(StatusOrm, status_fixture["id"])
            if status is None:
                status = StatusOrm(
                    id=status_fixture["id"],
                    workflow_id=fixture["workflow_id"],
                    code=status_fixture["code"],
                    label=status_fixture["label"],
                    is_terminal=bool(status_fixture["is_terminal"]),
                    is_initial=bool(status_fixture["is_initial"]),
                    sort_order=int(status_fixture["sort_order"]),
                )
                session.add(status)
            else:
                status.workflow_id = fixture["workflow_id"]
                status.code = status_fixture["code"]
                status.label = status_fixture["label"]
                status.is_terminal = bool(status_fixture["is_terminal"])
                status.is_initial = bool(status_fixture["is_initial"])
                status.sort_order = int(status_fixture["sort_order"])
            status_by_code[status_fixture["code"]] = status_fixture["id"]

        for from_code, to_code in fixture["transitions"]:
            from_status_id = status_by_code[from_code]
            to_status_id = status_by_code[to_code]
            existing_transition = (
                session.query(StatusTransitionOrm)
                .filter(
                    StatusTransitionOrm.from_status_id == from_status_id,
                    StatusTransitionOrm.to_status_id == to_status_id,
                )
                .first()
            )
            if existing_transition is None:
                session.add(
                    StatusTransitionOrm(
                        id=uuid.uuid4(),
                        from_status_id=from_status_id,
                        to_status_id=to_status_id,
                    )
                )

        for endpoint_fixture in fixture.get("webhook_endpoints", ()):
            endpoint = session.get(WebhookEndpointOrm, endpoint_fixture["id"])
            endpoint_url = str(endpoint_fixture["url"]).format(mock_co_provider_url=mock_provider_url)
            if endpoint is None:
                endpoint = WebhookEndpointOrm(
                    id=endpoint_fixture["id"],
                    workflow_id=fixture["workflow_id"],
                    country=fixture["country"],
                    provider_code=endpoint_fixture["provider_code"],
                    direction=endpoint_fixture["direction"],
                    event_type=endpoint_fixture["event_type"],
                    method=endpoint_fixture["method"],
                    url=endpoint_url,
                    secret_ref=endpoint_fixture["secret_ref"],
                    timeout_ms=int(endpoint_fixture["timeout_ms"]),
                    active=bool(endpoint_fixture["active"]),
                    created_by=FIXTURE_ADMIN_USER_ID,
                    created_at=now,
                    updated_at=now,
                )
                session.add(endpoint)
            else:
                endpoint.workflow_id = fixture["workflow_id"]
                endpoint.country = fixture["country"]
                endpoint.provider_code = endpoint_fixture["provider_code"]
                endpoint.direction = endpoint_fixture["direction"]
                endpoint.event_type = endpoint_fixture["event_type"]
                endpoint.method = endpoint_fixture["method"]
                endpoint.url = endpoint_url
                endpoint.secret_ref = endpoint_fixture["secret_ref"]
                endpoint.timeout_ms = int(endpoint_fixture["timeout_ms"])
                endpoint.active = bool(endpoint_fixture["active"])
                endpoint.updated_at = now

        for operation_fixture in fixture.get("operations", ()):
            operation = session.get(WorkflowOperationOrm, operation_fixture["id"])
            if operation is None:
                operation = WorkflowOperationOrm(
                    id=operation_fixture["id"],
                    workflow_id=fixture["workflow_id"],
                    name=operation_fixture["name"],
                    sort_order=int(operation_fixture["sort_order"]),
                    active=bool(operation_fixture["active"]),
                    created_at=now,
                    updated_at=now,
                )
                session.add(operation)
            else:
                operation.workflow_id = fixture["workflow_id"]
                operation.name = operation_fixture["name"]
                operation.sort_order = int(operation_fixture["sort_order"])
                operation.active = bool(operation_fixture["active"])
                operation.updated_at = now

            for sub_operation_fixture in operation_fixture.get("sub_operations", ()):
                sub_operation = session.get(WorkflowSubOperationOrm, sub_operation_fixture["id"])
                if sub_operation is None:
                    sub_operation = WorkflowSubOperationOrm(
                        id=sub_operation_fixture["id"],
                        operation_id=operation_fixture["id"],
                        sort_order=int(sub_operation_fixture["sort_order"]),
                        execution_type=sub_operation_fixture["execution_type"],
                        target_ref=sub_operation_fixture["target_ref"],
                        input_template=dict(sub_operation_fixture.get("input_template") or {}),
                        output_alias=sub_operation_fixture.get("output_alias"),
                        active=bool(sub_operation_fixture["active"]),
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(sub_operation)
                else:
                    sub_operation.operation_id = operation_fixture["id"]
                    sub_operation.sort_order = int(sub_operation_fixture["sort_order"])
                    sub_operation.execution_type = sub_operation_fixture["execution_type"]
                    sub_operation.target_ref = sub_operation_fixture["target_ref"]
                    sub_operation.input_template = dict(sub_operation_fixture.get("input_template") or {})
                    sub_operation.output_alias = sub_operation_fixture.get("output_alias")
                    sub_operation.active = bool(sub_operation_fixture["active"])
                    sub_operation.updated_at = now

                for trigger_fixture in sub_operation_fixture.get("triggers", ()):
                    trigger = session.get(WorkflowSubOperationTriggerOrm, trigger_fixture["id"])
                    if trigger is None:
                        trigger = WorkflowSubOperationTriggerOrm(
                            id=trigger_fixture["id"],
                            sub_operation_id=sub_operation_fixture["id"],
                            trigger_type=trigger_fixture["trigger_type"],
                            trigger_name=trigger_fixture["trigger_name"],
                            payload_template=dict(trigger_fixture.get("payload_template") or {}),
                            condition_expr=trigger_fixture.get("condition_expr"),
                            created_at=now,
                            updated_at=now,
                        )
                        session.add(trigger)
                    else:
                        trigger.sub_operation_id = sub_operation_fixture["id"]
                        trigger.trigger_type = trigger_fixture["trigger_type"]
                        trigger.trigger_name = trigger_fixture["trigger_name"]
                        trigger.payload_template = dict(trigger_fixture.get("payload_template") or {})
                        trigger.condition_expr = trigger_fixture.get("condition_expr")
                        trigger.updated_at = now

    session.commit()


if __name__ == "__main__":
    run()
