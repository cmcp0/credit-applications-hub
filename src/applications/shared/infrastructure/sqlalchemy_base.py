from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

from src.shared.infrastructure.sqlalchemy_metadata import SHARED_SQLALCHEMY_METADATA


class ApplicationsBase(DeclarativeBase):
    """Shared SQLAlchemy metadata for applications bounded context."""

    metadata = SHARED_SQLALCHEMY_METADATA
