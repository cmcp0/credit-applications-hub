from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.auth.shared.infrastructure.sqlalchemy_base import AuthBase


class AuthRole(AuthBase):
    __tablename__ = "auth_roles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)


class AuthPermission(AuthBase):
    __tablename__ = "auth_permissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)


class AuthUserRole(AuthBase):
    __tablename__ = "auth_user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("auth_users.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("auth_roles.id"), primary_key=True)


class AuthRolePermission(AuthBase):
    __tablename__ = "auth_role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("auth_roles.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("auth_permissions.id"),
        primary_key=True,
    )

