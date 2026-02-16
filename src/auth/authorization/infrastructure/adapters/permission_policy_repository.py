from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.auth.authorization.domain.ports.permission_policy_reader import PermissionPolicyReader
from src.auth.authorization.infrastructure.adapters.rbac_orm_models import (
    AuthPermission,
    AuthRole,
    AuthRolePermission,
    AuthUserRole,
)


class PermissionPolicyRepository(PermissionPolicyReader):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_roles_for_user(self, user_id: str) -> tuple[str, ...]:
        user_uuid = _to_uuid(user_id)
        statement: Select[tuple[str]] = (
            select(AuthRole.code)
            .join(AuthUserRole, AuthUserRole.role_id == AuthRole.id)
            .where(AuthUserRole.user_id == user_uuid)
        )
        roles = self._session.execute(statement).scalars().all()
        return tuple(sorted(set(roles)))

    def get_permissions_for_roles(self, roles: Sequence[str]) -> tuple[str, ...]:
        if not roles:
            return tuple()

        statement: Select[tuple[str]] = (
            select(AuthPermission.code)
            .join(AuthRolePermission, AuthRolePermission.permission_id == AuthPermission.id)
            .join(AuthRole, AuthRole.id == AuthRolePermission.role_id)
            .where(AuthRole.code.in_(list(roles)))
        )
        permissions = self._session.execute(statement).scalars().all()
        return tuple(sorted(set(permissions)))

    def get_permissions_for_user(self, user_id: str) -> tuple[str, ...]:
        user_uuid = _to_uuid(user_id)
        statement: Select[tuple[str]] = (
            select(AuthPermission.code)
            .join(AuthRolePermission, AuthRolePermission.permission_id == AuthPermission.id)
            .join(AuthRole, AuthRole.id == AuthRolePermission.role_id)
            .join(AuthUserRole, AuthUserRole.role_id == AuthRole.id)
            .where(AuthUserRole.user_id == user_uuid)
        )
        permissions = self._session.execute(statement).scalars().all()
        return tuple(sorted(set(permissions)))


def _to_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)

