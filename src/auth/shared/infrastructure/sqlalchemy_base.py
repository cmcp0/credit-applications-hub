from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class AuthBase(DeclarativeBase):
    """Shared SQLAlchemy metadata for auth bounded context."""

