from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from apps.backend.auth.dependencies import get_db_session
from src.auth.operations_admin.application.services.manage_operation_users_service import (
    ManageOperationUsersService,
)
from src.auth.operations_admin.domain.ports.operation_user_repository import OperationUserRepository
from src.auth.operations_admin.infrastructure.adapters.operation_user_repository import (
    SqlAlchemyOperationUserRepository,
)


def get_operation_user_repository(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OperationUserRepository:
    return SqlAlchemyOperationUserRepository(db_session)


def get_manage_operation_users_service(
    repository: Annotated[OperationUserRepository, Depends(get_operation_user_repository)],
) -> ManageOperationUsersService:
    return ManageOperationUsersService(repository)

