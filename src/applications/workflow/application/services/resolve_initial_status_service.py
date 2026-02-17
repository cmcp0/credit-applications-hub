from __future__ import annotations

from src.applications.shared.domain.errors import WorkflowNotFoundError
from src.applications.workflow.domain.ports.workflow_repository import WorkflowRepository


class ResolveInitialStatusService:
    def __init__(self, workflow_repository: WorkflowRepository) -> None:
        self._workflow_repository = workflow_repository

    def resolve(self, country: str) -> str:
        initial_status = self._workflow_repository.get_initial_status_code(country)
        if initial_status is None:
            raise WorkflowNotFoundError()
        return initial_status
