from __future__ import annotations

import uuid
from datetime import timezone
from typing import Optional

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.applications.application.domain.entities import Application
from src.applications.application.domain.ports.application_repository import ApplicationRepository
from src.applications.application.infrastructure.adapters.application_orm_model import ApplicationOrm
from src.applications.shared.domain.errors import VersionConflictError


class SqlAlchemyApplicationRepository(ApplicationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, application: Application) -> None:
        self._session.add(_to_model(application))

    def get_by_id(self, application_id: str) -> Optional[Application]:
        application_uuid = _safe_uuid(application_id)
        if application_uuid is None:
            return None

        model = self._session.get(ApplicationOrm, application_uuid)
        if model is None:
            return None
        return _to_entity(model)

    def save(self, application: Application, expected_previous_version: int) -> None:
        result = self._session.execute(
            update(ApplicationOrm)
            .where(
                ApplicationOrm.id == _as_uuid(application.id),
                ApplicationOrm.version == expected_previous_version,
            )
            .values(
                status_code=application.status_code,
                updated_at=application.updated_at,
                version=application.version,
            )
        )
        if result.rowcount != 1:
            raise VersionConflictError()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()


def _to_model(application: Application) -> ApplicationOrm:
    return ApplicationOrm(
        id=_as_uuid(application.id),
        user_id=_as_uuid(application.user_id),
        country=application.country,
        full_name=application.full_name,
        identity_document=application.identity_document,
        requested_amount=application.requested_amount,
        monthly_income=application.monthly_income,
        application_date=application.application_date,
        status_code=application.status_code,
        version=application.version,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


def _to_entity(model: ApplicationOrm) -> Application:
    return Application(
        id=str(model.id),
        user_id=str(model.user_id),
        country=model.country,
        full_name=model.full_name,
        identity_document=model.identity_document,
        requested_amount=float(model.requested_amount),
        monthly_income=float(model.monthly_income),
        application_date=model.application_date,
        status_code=model.status_code,
        version=model.version,
        created_at=model.created_at if model.created_at.tzinfo else model.created_at.replace(tzinfo=timezone.utc),
        updated_at=model.updated_at if model.updated_at.tzinfo else model.updated_at.replace(tzinfo=timezone.utc),
    )


def _as_uuid(value: str) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


def _safe_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return _as_uuid(value)
    except (TypeError, ValueError):
        return None
