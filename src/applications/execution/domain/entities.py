from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WorkerJobSummary:
    job_id: str
    workflow_id: str
    workflow_revision: int
    application_id: Optional[str]
    operation_id: Optional[str]
    sub_operation_id: Optional[str]
    status: str
    attempts: int
    max_attempts: int
    correlation_id: str
    available_at: Optional[datetime]
    locked_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_error_code: Optional[str]
    last_error_message: Optional[str]
    payload_summary: dict[str, object]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EventConsumptionCheckpoint:
    id: str
    consumer_name: str
    queue_name: str
    message_id: str
    correlation_id: Optional[str]
    payload_hash: Optional[str]
    consumed_at: datetime

