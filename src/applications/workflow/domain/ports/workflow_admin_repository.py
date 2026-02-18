from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Protocol

from src.applications.workflow.domain.admin_entities import (
    WebhookEndpointSummary,
    WebhookReplayQueuedResult,
    WorkflowCatalogItem,
    WorkflowGraphUpsertResult,
)


class WorkflowAdminRepository(Protocol):
    def list_workflows(
        self,
        *,
        country: Optional[str],
        active: Optional[bool],
        version_status: Optional[str],
    ) -> tuple[WorkflowCatalogItem, ...]:
        ...

    def create_workflow(
        self,
        *,
        country: str,
        version: int,
        statuses: tuple[dict[str, object], ...],
        transitions: tuple[dict[str, object], ...],
        created_at: datetime,
    ) -> WorkflowCatalogItem:
        ...

    def publish_workflow(
        self,
        *,
        workflow_id: uuid.UUID,
        expected_version: int,
        actor_user_id: uuid.UUID,
        published_at: datetime,
    ) -> WorkflowCatalogItem:
        ...

    def workflow_exists(self, workflow_id: uuid.UUID) -> bool:
        ...

    def list_execution_summaries(
        self,
        *,
        workflow_id: uuid.UUID,
        status: Optional[str],
        application_id: Optional[str],
        operation_id: Optional[str],
        sub_operation_id: Optional[str],
        from_ts: Optional[str],
        to_ts: Optional[str],
        correlation_id: Optional[str],
        sort_by: str,
        sort_dir: str,
        page: int,
        page_size: int,
    ) -> tuple[tuple[dict[str, object], ...], int]:
        ...

    def list_webhook_events(
        self,
        *,
        workflow_id: uuid.UUID,
        direction: Optional[str],
        event_type: Optional[str],
        delivery_status: Optional[str],
        application_id: Optional[str],
        correlation_id: Optional[str],
        sort_by: str,
        sort_dir: str,
        page: int,
        page_size: int,
    ) -> tuple[tuple[dict[str, object], ...], int]:
        ...

    def upsert_workflow_graph(
        self,
        *,
        workflow_id: uuid.UUID,
        expected_version: Optional[int],
        operations: tuple[dict[str, object], ...],
        deleted_operation_ids: tuple[uuid.UUID, ...],
        deleted_sub_operation_ids: tuple[uuid.UUID, ...],
        deleted_trigger_ids: tuple[uuid.UUID, ...],
        if_match: Optional[str],
        updated_at: datetime,
    ) -> WorkflowGraphUpsertResult:
        ...

    def create_webhook_endpoint(
        self,
        *,
        workflow_id: uuid.UUID,
        direction: str,
        provider_code: str,
        event_type: str,
        method: str,
        url: str,
        secret_ref: str,
        timeout_ms: int,
        active: bool,
        actor_user_id: uuid.UUID,
        created_at: datetime,
    ) -> WebhookEndpointSummary:
        ...

    def update_webhook_endpoint(
        self,
        *,
        workflow_id: uuid.UUID,
        endpoint_id: uuid.UUID,
        active: Optional[bool],
        method: Optional[str],
        url: Optional[str],
        timeout_ms: Optional[int],
        updated_at: datetime,
    ) -> WebhookEndpointSummary:
        ...

    def rotate_webhook_endpoint_secret(
        self,
        *,
        workflow_id: uuid.UUID,
        endpoint_id: uuid.UUID,
        reason: str,
        rotated_at: datetime,
    ) -> WebhookEndpointSummary:
        ...

    def replay_webhook_event(
        self,
        *,
        workflow_id: uuid.UUID,
        webhook_event_id: uuid.UUID,
        command_id: uuid.UUID,
        reason: str,
        requested_by: uuid.UUID,
        requested_at: datetime,
    ) -> WebhookReplayQueuedResult:
        ...
