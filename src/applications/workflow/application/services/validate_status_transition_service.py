from __future__ import annotations

from src.applications.shared.domain.errors import InvalidStatusTransitionError
from src.applications.workflow.domain.ports.workflow_repository import WorkflowRepository


class ValidateStatusTransitionService:
    def __init__(self, workflow_repository: WorkflowRepository) -> None:
        self._workflow_repository = workflow_repository

    def validate(self, *, country: str, from_status_code: str, to_status_code: str) -> None:
        from_status = self._workflow_repository.get_status(country, from_status_code)
        to_status = self._workflow_repository.get_status(country, to_status_code)
        if from_status is None or to_status is None:
            raise InvalidStatusTransitionError()

        if not self._workflow_repository.is_transition_allowed(country, from_status_code, to_status_code):
            raise InvalidStatusTransitionError()
