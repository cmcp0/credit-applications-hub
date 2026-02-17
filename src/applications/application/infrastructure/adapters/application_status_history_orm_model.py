from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.applications.shared.infrastructure.sqlalchemy_base import ApplicationsBase


class ApplicationStatusHistoryOrm(ApplicationsBase):
    __tablename__ = "application_status_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )
    from_status_code: Mapped[str] = mapped_column(String, nullable=False)
    to_status_code: Mapped[str] = mapped_column(String, nullable=False)
    application_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    command_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


Index(
    "ux_application_status_history_application_version",
    ApplicationStatusHistoryOrm.application_id,
    ApplicationStatusHistoryOrm.application_version,
    unique=True,
)
Index(
    "ux_application_status_history_command_id",
    ApplicationStatusHistoryOrm.command_id,
    unique=True,
    postgresql_where=ApplicationStatusHistoryOrm.command_id.is_not(None),
)
Index(
    "ix_application_status_history_application_changed",
    ApplicationStatusHistoryOrm.application_id,
    ApplicationStatusHistoryOrm.changed_at.desc(),
)
