from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

from src.shared.infrastructure.sqlalchemy_metadata import SHARED_SQLALCHEMY_METADATA


class AuthBase(DeclarativeBase):
    """Shared SQLAlchemy metadata for auth bounded context."""

    metadata = SHARED_SQLALCHEMY_METADATA
