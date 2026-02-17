from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.backend.api.applications.actor_authorizer import StatusUpdateActorAuthorizer
from apps.backend.api.applications.command_consumer import (
    UpdateApplicationStatusCommandConsumer,
    UpdateApplicationStatusMessage,
)
from src.applications.application.application.services.update_application_status_service import (
    UpdateApplicationStatusService,
)
from src.applications.application.infrastructure.adapters.application_orm_model import ApplicationOrm
from src.applications.application.infrastructure.adapters.application_status_history_orm_model import (
    ApplicationStatusHistoryOrm,
)
from src.applications.application.infrastructure.adapters.application_repository import (
    SqlAlchemyApplicationRepository,
)
from src.applications.application.infrastructure.adapters.status_history_repository import (
    SqlAlchemyStatusHistoryRepository,
)
from src.applications.shared.domain.errors import (
    ApplicationPermissionDeniedError,
    UntrustedCommandProducerError,
)
from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm
from src.applications.shared.infrastructure.adapters.outbox_event_repository import (
    SqlAlchemyOutboxEventRepository,
)
from src.applications.workflow.application.services.validate_status_transition_service import (
    ValidateStatusTransitionService,
)
from src.applications.workflow.infrastructure.adapters.workflow_repository import SqlAlchemyWorkflowRepository
from tests.auth.fixtures.seed import TEST_USERS


def _token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_application(client: TestClient, customer_token: str) -> str:
    response = client.post(
        "/api/applications",
        json={
            "country": "BR",
            "full_name": "Async Customer",
            "identity_document": "12345678901",
            "requested_amount": 5000,
            "monthly_income": 2500,
        },
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _build_consumer(session_factory, trusted_producers: tuple[str, ...]):
    session = session_factory()
    workflow_repository = SqlAlchemyWorkflowRepository(session)
    update_service = UpdateApplicationStatusService(
        application_repository=SqlAlchemyApplicationRepository(session),
        outbox_event_writer=SqlAlchemyOutboxEventRepository(session),
        status_history_repository=SqlAlchemyStatusHistoryRepository(session),
        validate_status_transition_service=ValidateStatusTransitionService(workflow_repository),
    )
    consumer = UpdateApplicationStatusCommandConsumer(
        update_service=update_service,
        trusted_producers=trusted_producers,
        actor_authorizer=StatusUpdateActorAuthorizer(session),
    )
    return session, consumer


def test_async_update_status_rejects_untrusted_producer(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )
    application_id = _create_application(client, customer_token)

    session, consumer = _build_consumer(
        session_factory,
        trusted_producers=("backend.applications.update_status.q",),
    )
    try:
        with pytest.raises(UntrustedCommandProducerError):
            consumer.consume(
                UpdateApplicationStatusMessage(
                    application_id=application_id,
                    target_status_code="APPROVED",
                    actor_user_id=str(TEST_USERS["operation"]["id"]),
                    actor_role="operation",
                    expected_version=1,
                    reason_code="ASYNC_REVIEW",
                    request_id=str(uuid.uuid4()),
                    correlation_id=str(uuid.uuid4()),
                    producer="untrusted.worker",
                    message_id=str(uuid.uuid4()),
                )
            )
    finally:
        session.close()

    with session_factory() as verify_session:
        application_row = verify_session.get(ApplicationOrm, uuid.UUID(application_id))
        status_history_rows = verify_session.execute(
            select(ApplicationStatusHistoryOrm).where(
                ApplicationStatusHistoryOrm.application_id == uuid.UUID(application_id)
            )
        ).scalars().all()

    assert application_row is not None
    assert application_row.status_code == "PENDING_REVIEW"
    assert application_row.version == 1
    assert status_history_rows == []


def test_async_update_status_trusted_producer_uses_message_id_for_idempotency(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )
    application_id = _create_application(client, customer_token)

    session, consumer = _build_consumer(
        session_factory,
        trusted_producers=("backend.applications.update_status.q",),
    )
    message_id = str(uuid.uuid4())
    try:
        first = consumer.consume(
            UpdateApplicationStatusMessage(
                application_id=application_id,
                target_status_code="APPROVED",
                actor_user_id=str(TEST_USERS["operation"]["id"]),
                actor_role="operation",
                expected_version=1,
                reason_code="ASYNC_REVIEW",
                request_id=str(uuid.uuid4()),
                correlation_id=str(uuid.uuid4()),
                producer="backend.applications.update_status.q",
                message_id=message_id,
            )
        )
        second = consumer.consume(
            UpdateApplicationStatusMessage(
                application_id=application_id,
                target_status_code="APPROVED",
                actor_user_id=str(TEST_USERS["operation"]["id"]),
                actor_role="operation",
                expected_version=1,
                reason_code="ASYNC_REVIEW",
                request_id=str(uuid.uuid4()),
                correlation_id=str(uuid.uuid4()),
                producer="backend.applications.update_status.q",
                message_id=message_id,
            )
        )
    finally:
        session.close()

    assert first.status_code == "APPROVED"
    assert second.status_code == "APPROVED"

    with session_factory() as verify_session:
        history_rows = verify_session.execute(
            select(ApplicationStatusHistoryOrm).where(
                ApplicationStatusHistoryOrm.application_id == uuid.UUID(application_id)
            )
        ).scalars().all()
        status_updated_events = verify_session.execute(
            select(OutboxEventOrm).where(
                OutboxEventOrm.aggregate_id == uuid.UUID(application_id),
                OutboxEventOrm.event_name == "ApplicationStatusUpdated",
            )
        ).scalars().all()

    assert len(history_rows) == 1
    assert len(status_updated_events) == 1


def test_async_update_status_rejects_actor_without_required_permission(
    client: TestClient,
    seeded_users: dict[str, dict[str, str]],
    session_factory,
) -> None:
    customer_token = _token_for(
        client,
        seeded_users["customer"]["email"],
        seeded_users["customer"]["password"],
    )
    application_id = _create_application(client, customer_token)

    session, consumer = _build_consumer(
        session_factory,
        trusted_producers=("backend.applications.update_status.q",),
    )
    try:
        with pytest.raises(ApplicationPermissionDeniedError):
            consumer.consume(
                UpdateApplicationStatusMessage(
                    application_id=application_id,
                    target_status_code="APPROVED",
                    actor_user_id=str(TEST_USERS["customer"]["id"]),
                    actor_role="operation",
                    expected_version=1,
                    reason_code="ASYNC_REVIEW",
                    request_id=str(uuid.uuid4()),
                    correlation_id=str(uuid.uuid4()),
                    producer="backend.applications.update_status.q",
                    message_id=str(uuid.uuid4()),
                )
            )
    finally:
        session.close()

    with session_factory() as verify_session:
        application_row = verify_session.get(ApplicationOrm, uuid.UUID(application_id))
        status_history_rows = verify_session.execute(
            select(ApplicationStatusHistoryOrm).where(
                ApplicationStatusHistoryOrm.application_id == uuid.UUID(application_id)
            )
        ).scalars().all()

    assert application_row is not None
    assert application_row.status_code == "PENDING_REVIEW"
    assert application_row.version == 1
    assert status_history_rows == []
