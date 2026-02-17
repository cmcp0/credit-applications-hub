from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.applications.shared.infrastructure.sqlalchemy_base import ApplicationsBase


class WorkflowOrm(ApplicationsBase):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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


class StatusOrm(ApplicationsBase):
    __tablename__ = "statuses"
    __table_args__ = (
        UniqueConstraint("workflow_id", "code", name="ux_statuses_workflow_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StatusTransitionOrm(ApplicationsBase):
    __tablename__ = "status_transitions"
    __table_args__ = (
        UniqueConstraint("from_status_id", "to_status_id", name="ux_status_transitions_from_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    from_status_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("statuses.id"),
        nullable=False,
        index=True,
    )
    to_status_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("statuses.id"),
        nullable=False,
        index=True,
    )
