from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.auth.authentication.domain.entities import StoredUserCredentials
from src.auth.authentication.domain.ports.user_credentials_reader import UserCredentialsReader
from src.auth.authentication.infrastructure.adapters.auth_user_orm_model import AuthUser
from src.auth.authorization.infrastructure.adapters.rbac_orm_models import (
    AuthPermission,
    AuthRole,
    AuthRolePermission,
    AuthUserRole,
)


class AuthUserCredentialsRepository(UserCredentialsReader):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_normalized_email(self, normalized_email: str) -> Optional[StoredUserCredentials]:
        user = self._session.execute(
            select(AuthUser).where(func.lower(AuthUser.email) == normalized_email)
        ).scalar_one_or_none()

        if user is None:
            return None

        roles = self._session.execute(
            select(AuthRole.code)
            .join(AuthUserRole, AuthUserRole.role_id == AuthRole.id)
            .where(AuthUserRole.user_id == user.id)
        ).scalars().all()

        permissions = self._session.execute(
            select(AuthPermission.code)
            .join(AuthRolePermission, AuthRolePermission.permission_id == AuthPermission.id)
            .join(AuthRole, AuthRole.id == AuthRolePermission.role_id)
            .join(AuthUserRole, AuthUserRole.role_id == AuthRole.id)
            .where(AuthUserRole.user_id == user.id)
        ).scalars().all()

        return StoredUserCredentials(
            user_id=str(user.id),
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            roles=tuple(sorted(set(roles))),
            permissions=tuple(sorted(set(permissions))),
        )

    def mark_login_success(self, user_id: str) -> None:
        user = self._session.get(AuthUser, uuid.UUID(user_id))
        if user is None:
            return

        now = datetime.now(timezone.utc)
        user.last_login_at = now
        user.updated_at = now
        self._session.add(user)
        self._session.commit()
