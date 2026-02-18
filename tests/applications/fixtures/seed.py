from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.applications.workflow.infrastructure.adapters.workflow_orm_model import (
    StatusOrm,
    StatusTransitionOrm,
    WorkflowOrm,
)

WORKFLOW_IDS = {
    "MX": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0001"),
    "BR": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002"),
    "CO": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003"),
    "CL": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0004"),
    "PE": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0005"),
    "ES": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0006"),
}

STATUS_IDS = {
    "MX": {
        "PENDING_REVIEW": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc1001"),
        "APPROVED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc1002"),
        "REJECTED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc1003"),
    },
    "BR": {
        "PENDING_REVIEW": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc2001"),
        "APPROVED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc2002"),
        "REJECTED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc2003"),
    },
    "CO": {
        "PENDING_REVIEW": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc3001"),
        "APPROVED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc3002"),
        "REJECTED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc3003"),
    },
    "CL": {
        "PENDING_REVIEW": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc4001"),
        "APPROVED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc4002"),
        "REJECTED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc4003"),
    },
    "PE": {
        "PENDING_REVIEW": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc5001"),
        "APPROVED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc5002"),
        "REJECTED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc5003"),
    },
    "ES": {
        "PENDING_REVIEW": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6001"),
        "ADDITIONAL_REVIEW": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6002"),
        "APPROVED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6003"),
        "REJECTED": uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccc6004"),
    },
}

TEST_ADMIN_USER_ID = uuid.UUID("44444444-4444-4444-4444-444444444443")


def seed_workflow_data(session: Session) -> None:
    now = datetime.now(timezone.utc)

    for country, workflow_id in WORKFLOW_IDS.items():
        workflow = session.get(WorkflowOrm, workflow_id)
        if workflow is None:
            workflow = WorkflowOrm(
                id=workflow_id,
                country=country,
                active=True,
                version=1,
                version_status="PUBLISHED",
                published_by=TEST_ADMIN_USER_ID,
                published_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(workflow)

        for status_code, status_id in STATUS_IDS[country].items():
            existing_status = session.get(StatusOrm, status_id)
            if existing_status is not None:
                continue

            sort_order = {
                "PENDING_REVIEW": 1,
                "ADDITIONAL_REVIEW": 2,
                "APPROVED": 3,
                "REJECTED": 4,
            }[status_code]
            session.add(
                StatusOrm(
                    id=status_id,
                    workflow_id=workflow_id,
                    code=status_code,
                    label=status_code.replace("_", " ").title(),
                    is_terminal=status_code in {"APPROVED", "REJECTED"},
                    is_initial=status_code == "PENDING_REVIEW",
                    sort_order=sort_order,
                )
            )

        transitions = [("PENDING_REVIEW", "APPROVED"), ("PENDING_REVIEW", "REJECTED")]
        if country == "ES":
            transitions.extend(
                [
                    ("PENDING_REVIEW", "ADDITIONAL_REVIEW"),
                    ("ADDITIONAL_REVIEW", "APPROVED"),
                    ("ADDITIONAL_REVIEW", "REJECTED"),
                ]
            )

        for from_status, to_status in transitions:
            from_status_id = STATUS_IDS[country][from_status]
            to_status_id = STATUS_IDS[country][to_status]
            transition_exists = (
                session.query(StatusTransitionOrm)
                .filter(
                    StatusTransitionOrm.from_status_id == from_status_id,
                    StatusTransitionOrm.to_status_id == to_status_id,
                )
                .first()
            )
            if transition_exists is None:
                session.add(
                    StatusTransitionOrm(
                        id=uuid.uuid4(),
                        from_status_id=from_status_id,
                        to_status_id=to_status_id,
                    )
                )

    session.commit()
