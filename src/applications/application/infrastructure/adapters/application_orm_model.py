from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.applications.shared.infrastructure.sqlalchemy_base import ApplicationsBase


class ApplicationOrm(ApplicationsBase):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("auth_users.id"), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    identity_document: Mapped[str] = mapped_column(String, nullable=False)
    requested_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    monthly_income: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    application_date: Mapped[date] = mapped_column(Date, nullable=False)
    status_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
