from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.auth.authentication.infrastructure.adapters.auth_user_orm_model import AuthUser
from src.auth.operations_admin.domain.entities import OperationUserSummary
from src.auth.operations_admin.domain.ports.operation_user_repository import OperationUserRepository
from src.auth.authorization.infrastructure.adapters.rbac_orm_models import AuthRole, AuthUserRole
from src.auth.shared.domain.errors import RoleAlreadyAssignedError, UserNotFoundError


class SqlAlchemyOperationUserRepository(OperationUserRepository):
    OPERATION_ROLE_CODE = "operation"

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_operation_users(
        self,
        *,
        active: Optional[bool],
        page: int,
        page_size: int,
    ) -> tuple[tuple[OperationUserSummary, ...], int]:
        role_id = self._operation_role_id()
        operation_user_ids = set(
            self._session.execute(
                select(AuthUserRole.user_id).where(AuthUserRole.role_id == role_id)
            ).scalars()
        )

        base_statement = select(AuthUser)
        count_statement = select(func.count()).select_from(AuthUser)
        if active is not None:
            base_statement = base_statement.where(AuthUser.is_active.is_(active))
            count_statement = count_statement.where(AuthUser.is_active.is_(active))

        total = int(self._session.execute(count_statement).scalar_one())
        offset = (page - 1) * page_size
        rows = self._session.execute(
            base_statement.order_by(AuthUser.updated_at.desc(), AuthUser.id.asc()).offset(offset).limit(page_size)
        ).scalars()

        items = tuple(
            OperationUserSummary(
                user_id=str(row.id),
                email=row.email,
                is_active=row.is_active,
                has_operation_role=row.id in operation_user_ids,
                updated_at=row.updated_at,
            )
            for row in rows
        )
        return items, total

    def assign_operation_role(self, *, user_id: uuid.UUID, assigned_at: datetime) -> datetime:
        user = self._session.get(AuthUser, user_id)
        if user is None:
            raise UserNotFoundError()

        role_id = self._operation_role_id()
        existing = self._session.get(
            AuthUserRole,
            {
                "user_id": user_id,
                "role_id": role_id,
            },
        )
        if existing is not None:
            raise RoleAlreadyAssignedError()

        self._session.add(
            AuthUserRole(
                user_id=user_id,
                role_id=role_id,
            )
        )
        user.updated_at = assigned_at
        self._session.commit()
        return assigned_at

    def set_operation_access(self, *, user_id: uuid.UUID, enabled: bool, updated_at: datetime) -> datetime:
        user = self._session.get(AuthUser, user_id)
        if user is None:
            raise UserNotFoundError()

        role_id = self._operation_role_id()
        existing = self._session.get(
            AuthUserRole,
            {
                "user_id": user_id,
                "role_id": role_id,
            },
        )
        if enabled and existing is None:
            self._session.add(AuthUserRole(user_id=user_id, role_id=role_id))
        elif not enabled and existing is not None:
            self._session.delete(existing)

        user.updated_at = updated_at
        self._session.commit()
        return updated_at

    def _operation_role_id(self) -> uuid.UUID:
        role_id = self._session.execute(
            select(AuthRole.id).where(AuthRole.code == self.OPERATION_ROLE_CODE)
        ).scalar_one_or_none()
        if role_id is None:
            raise RuntimeError("Missing required 'operation' role")
        return role_id

