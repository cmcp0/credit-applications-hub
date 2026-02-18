from __future__ import annotations

from typing import Optional, Protocol

from src.applications.execution.domain.entities import (
    EventConsumptionCheckpoint,
    WorkerJobSummary,
)


class ExecutionRepository(Protocol):
    def list_worker_jobs(
        self,
        *,
        workflow_id: str,
        status: Optional[str],
        application_id: Optional[str],
        operation_id: Optional[str],
        sub_operation_id: Optional[str],
        correlation_id: Optional[str],
        page: int,
        page_size: int,
    ) -> tuple[tuple[WorkerJobSummary, ...], int]:
        ...

    def list_event_consumptions(
        self,
        *,
        consumer_name: Optional[str],
        queue_name: Optional[str],
        page: int,
        page_size: int,
    ) -> tuple[tuple[EventConsumptionCheckpoint, ...], int]:
        ...

