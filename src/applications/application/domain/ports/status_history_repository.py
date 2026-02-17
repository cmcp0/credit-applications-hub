from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol


class ApplicationStatusHistoryRecord(Protocol):
    id: str
    application_id: str
    from_status_code: str
    to_status_code: str
    application_version: int
    reason_code: Optional[str]
    actor_user_id: Optional[str]
    actor_role: Optional[str]
    command_id: Optional[str]
    correlation_id: str
    changed_at: datetime


class StatusHistoryRepository(Protocol):
    def append(
        self,
        *,
        application_id: str,
        from_status_code: str,
        to_status_code: str,
        application_version: int,
        reason_code: Optional[str],
        actor_user_id: Optional[str],
        actor_role: Optional[str],
        command_id: Optional[str],
        correlation_id: str,
        changed_at: datetime,
    ) -> None:
        ...

    def get_by_command_id(self, command_id: str) -> Optional[ApplicationStatusHistoryRecord]:
        ...
