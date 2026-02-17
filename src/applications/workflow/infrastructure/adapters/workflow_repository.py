from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.applications.workflow.domain.entities import WorkflowStatus
from src.applications.workflow.domain.ports.workflow_repository import WorkflowRepository
from src.applications.workflow.infrastructure.adapters.status_transition_repository import (
    StatusTransitionRepository,
)
from src.applications.workflow.infrastructure.adapters.workflow_orm_model import StatusOrm, WorkflowOrm


class SqlAlchemyWorkflowRepository(WorkflowRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self._status_transition_repository = StatusTransitionRepository(session)

    def get_initial_status_code(self, country: str) -> Optional[str]:
        status = self._session.execute(
            select(StatusOrm.code)
            .join(WorkflowOrm, WorkflowOrm.id == StatusOrm.workflow_id)
            .where(
                WorkflowOrm.country == country,
                WorkflowOrm.active.is_(True),
                StatusOrm.is_initial.is_(True),
            )
        ).scalar_one_or_none()
        return status

    def is_transition_allowed(self, country: str, from_status_code: str, to_status_code: str) -> bool:
        from_status = self._status_by_code(country, from_status_code)
        if from_status is None:
            return False
        allowed_codes = self._status_transition_repository.list_allowed_status_codes(from_status.id)
        return to_status_code in allowed_codes

    def get_status(self, country: str, status_code: str) -> Optional[WorkflowStatus]:
        status = self._status_by_code(country, status_code)
        if status is None:
            return None

        allowed = self._status_transition_repository.list_allowed_status_codes(status.id)
        return WorkflowStatus(
            code=status.code,
            label=status.label,
            is_terminal=status.is_terminal,
            is_initial=status.is_initial,
            allowed_transitions=allowed,
        )

    def list_allowed_transitions(self, country: str, status_code: str) -> tuple[str, ...]:
        status = self._status_by_code(country, status_code)
        if status is None:
            return tuple()
        return self._status_transition_repository.list_allowed_status_codes(status.id)

    def _status_by_code(self, country: str, status_code: str) -> Optional[StatusOrm]:
        return self._session.execute(
            select(StatusOrm)
            .join(WorkflowOrm, WorkflowOrm.id == StatusOrm.workflow_id)
            .where(
                WorkflowOrm.country == country,
                WorkflowOrm.active.is_(True),
                StatusOrm.code == status_code,
            )
        ).scalar_one_or_none()
