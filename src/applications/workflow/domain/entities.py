from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowStatus:
    code: str
    label: str
    is_terminal: bool
    is_initial: bool
    allowed_transitions: tuple[str, ...]


@dataclass(frozen=True)
class Workflow:
    id: str
    country: str
    active: bool
    statuses: tuple[WorkflowStatus, ...]
