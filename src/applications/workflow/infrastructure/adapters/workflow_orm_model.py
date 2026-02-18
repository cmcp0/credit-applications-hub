from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.applications.shared.infrastructure.sqlalchemy_base import ApplicationsBase


class WorkflowOrm(ApplicationsBase):
    __tablename__ = "workflows"
    __table_args__ = (
        UniqueConstraint("country", "version", name="ux_workflows_country_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    graph_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version_status: Mapped[str] = mapped_column(String, nullable=False, default="PUBLISHED")
    published_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("auth_users.id"),
        nullable=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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


class WorkflowOperationOrm(ApplicationsBase):
    __tablename__ = "operations"
    __table_args__ = (
        UniqueConstraint("workflow_id", "sort_order", name="ux_operations_workflow_sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
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


class WorkflowSubOperationOrm(ApplicationsBase):
    __tablename__ = "sub_operations"
    __table_args__ = (
        UniqueConstraint("operation_id", "sort_order", name="ux_sub_operations_operation_sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("operations.id"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    input_template: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    output_alias: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
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


class WorkflowSubOperationTriggerOrm(ApplicationsBase):
    __tablename__ = "sub_operation_triggers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sub_operation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sub_operations.id"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_name: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_template: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    condition_expr: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
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


class WebhookEndpointOrm(ApplicationsBase):
    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    secret_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("auth_users.id"),
        nullable=False,
    )
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


class WebhookEventOrm(ApplicationsBase):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("webhook_endpoints.id"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("applications.id"),
        nullable=True,
        index=True,
    )
    provider_code: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    signature_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    external_event_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class WebhookDeliveryAttemptOrm(ApplicationsBase):
    __tablename__ = "webhook_delivery_attempts"
    __table_args__ = (
        UniqueConstraint("webhook_event_id", "attempt_no", name="ux_webhook_delivery_attempts_event_attempt"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    webhook_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("webhook_events.id"),
        nullable=False,
        index=True,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False)
    response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class WebhookReplayCommandOrm(ApplicationsBase):
    __tablename__ = "webhook_replay_commands"

    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    webhook_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("webhook_events.id"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("auth_users.id"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
