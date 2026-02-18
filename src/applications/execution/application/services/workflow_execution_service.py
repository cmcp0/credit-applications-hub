from __future__ import annotations

from src.applications.execution.domain.ports.execution_repository import ExecutionRepository


class WorkflowExecutionService:
    def __init__(self, repository: ExecutionRepository) -> None:
        self._repository = repository

