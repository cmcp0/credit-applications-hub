from __future__ import annotations

from typing import Optional, Protocol

from src.applications.workflow.domain.entities import WorkflowStatus


class WorkflowRepository(Protocol):
    def get_initial_status_code(self, country: str) -> Optional[str]:
        ...

    def is_transition_allowed(self, country: str, from_status_code: str, to_status_code: str) -> bool:
        ...

    def get_status(self, country: str, status_code: str) -> Optional[WorkflowStatus]:
        ...

    def list_allowed_transitions(self, country: str, status_code: str) -> tuple[str, ...]:
        ...
