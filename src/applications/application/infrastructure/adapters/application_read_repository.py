from __future__ import annotations

import uuid
from datetime import timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.applications.application.application.queries.get_application import GetApplicationQuery
from src.applications.application.application.queries.list_applications import ListApplicationsQuery
from src.applications.application.domain.ports.application_read_repository import ApplicationReadRepository
from src.applications.application.domain.value_objects import (
    ApplicationDetail,
    ApplicationListPage,
    ApplicationStatusMetadata,
    ApplicationSummary,
)
from src.applications.application.infrastructure.adapters.application_orm_model import ApplicationOrm
from src.applications.workflow.domain.ports.workflow_repository import WorkflowRepository


class SqlAlchemyApplicationReadRepository(ApplicationReadRepository):
    def __init__(self, session: Session, workflow_repository: WorkflowRepository) -> None:
        self._session = session
        self._workflow_repository = workflow_repository

    def list_applications(self, query: ListApplicationsQuery) -> ApplicationListPage:
        filters = [ApplicationOrm.id.is_not(None)]

        actor_uuid = _safe_uuid(query.actor_user_id)
        if not query.can_list_all:
            if actor_uuid is None:
                return ApplicationListPage(items=tuple(), page=query.page, page_size=query.page_size, total=0)
            filters.append(ApplicationOrm.user_id == actor_uuid)

        if query.country:
            filters.append(ApplicationOrm.country == query.country.strip().upper())

        if query.status:
            filters.append(ApplicationOrm.status_code == query.status.strip().upper())

        total = self._session.execute(
            select(func.count()).select_from(select(ApplicationOrm.id).where(*filters).subquery())
        ).scalar_one()

        rows = self._session.execute(
            select(ApplicationOrm)
            .where(*filters)
            .order_by(ApplicationOrm.created_at.desc(), ApplicationOrm.id.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        ).scalars().all()

        items = tuple(
            ApplicationSummary(
                id=str(row.id),
                country=row.country,
                status_code=row.status_code,
                requested_amount=float(row.requested_amount),
                created_at=row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc),
                updated_at=row.updated_at if row.updated_at.tzinfo else row.updated_at.replace(tzinfo=timezone.utc),
            )
            for row in rows
        )
        return ApplicationListPage(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total=int(total),
        )

    def get_application(self, query: GetApplicationQuery) -> Optional[ApplicationDetail]:
        actor_uuid = _safe_uuid(query.actor_user_id)
        application_id = _safe_uuid(query.application_id)
        if application_id is None:
            return None

        filters = [ApplicationOrm.id == application_id]
        if not query.can_list_all:
            if actor_uuid is None:
                return None
            filters.append(ApplicationOrm.user_id == actor_uuid)

        row = self._session.execute(select(ApplicationOrm).where(*filters)).scalar_one_or_none()
        if row is None:
            return None

        status = self._workflow_repository.get_status(row.country, row.status_code)
        if status is None:
            status_metadata = ApplicationStatusMetadata(
                code=row.status_code,
                label=row.status_code,
                is_terminal=False,
                allowed_transitions=tuple(),
            )
        else:
            status_metadata = ApplicationStatusMetadata(
                code=status.code,
                label=status.label,
                is_terminal=status.is_terminal,
                allowed_transitions=status.allowed_transitions,
            )

        return ApplicationDetail(
            id=str(row.id),
            country=row.country,
            status_code=row.status_code,
            requested_amount=float(row.requested_amount),
            created_at=row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc),
            updated_at=row.updated_at if row.updated_at.tzinfo else row.updated_at.replace(tzinfo=timezone.utc),
            version=row.version,
            status_metadata=status_metadata,
        )


def _safe_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None
