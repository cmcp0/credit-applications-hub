from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.applications.shared.infrastructure.sqlalchemy_base import ApplicationsBase


class WorkerJobOrm(ApplicationsBase):
    __tablename__ = "worker_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="ux_worker_jobs_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    workflow_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("applications.id"),
        nullable=True,
        index=True,
    )
    operation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("operations.id"),
        nullable=True,
        index=True,
    )
    sub_operation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("sub_operations.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
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


class EventConsumptionOrm(ApplicationsBase):
    __tablename__ = "event_consumptions"
    __table_args__ = (
        UniqueConstraint(
            "consumer_name",
            "queue_name",
            "message_id",
            name="ux_event_consumptions_consumer_queue_message",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    consumer_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    queue_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

