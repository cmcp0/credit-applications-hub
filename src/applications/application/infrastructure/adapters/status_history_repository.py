from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.applications.application.domain.ports.status_history_repository import StatusHistoryRepository
from src.applications.application.infrastructure.adapters.application_status_history_orm_model import (
    ApplicationStatusHistoryOrm,
)


@dataclass(frozen=True)
class StatusHistoryRecord:
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


class SqlAlchemyStatusHistoryRepository(StatusHistoryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

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
        self._session.add(
            ApplicationStatusHistoryOrm(
                id=uuid.uuid4(),
                application_id=uuid.UUID(application_id),
                from_status_code=from_status_code,
                to_status_code=to_status_code,
                application_version=application_version,
                reason_code=reason_code,
                actor_user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
                actor_role=actor_role,
                command_id=uuid.UUID(command_id) if command_id else None,
                correlation_id=uuid.UUID(correlation_id),
                changed_at=changed_at,
            )
        )

    def get_by_command_id(self, command_id: str) -> Optional[StatusHistoryRecord]:
        try:
            command_uuid = uuid.UUID(command_id)
        except ValueError:
            return None

        row = self._session.execute(
            select(ApplicationStatusHistoryOrm).where(ApplicationStatusHistoryOrm.command_id == command_uuid)
        ).scalar_one_or_none()
        if row is None:
            return None

        return StatusHistoryRecord(
            id=str(row.id),
            application_id=str(row.application_id),
            from_status_code=row.from_status_code,
            to_status_code=row.to_status_code,
            application_version=row.application_version,
            reason_code=row.reason_code,
            actor_user_id=str(row.actor_user_id) if row.actor_user_id else None,
            actor_role=row.actor_role,
            command_id=str(row.command_id) if row.command_id else None,
            correlation_id=str(row.correlation_id),
            changed_at=row.changed_at if row.changed_at.tzinfo else row.changed_at.replace(tzinfo=timezone.utc),
        )
