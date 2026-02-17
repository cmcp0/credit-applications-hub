from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.applications.workflow.infrastructure.adapters.workflow_orm_model import StatusOrm, StatusTransitionOrm


class StatusTransitionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_allowed_status_codes(self, from_status_id: uuid.UUID) -> tuple[str, ...]:
        to_codes = self._session.execute(
            select(StatusOrm.code)
            .join(StatusTransitionOrm, StatusTransitionOrm.to_status_id == StatusOrm.id)
            .where(StatusTransitionOrm.from_status_id == from_status_id)
            .order_by(StatusOrm.code.asc())
        ).scalars().all()
        return tuple(to_codes)
