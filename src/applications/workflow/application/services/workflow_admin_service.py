from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.applications.workflow.domain.admin_entities import (
    WebhookEndpointSummary,
    WebhookReplayQueuedResult,
    WorkflowCatalogItem,
    WorkflowGraphUpsertResult,
)
from src.applications.workflow.domain.ports.workflow_admin_repository import WorkflowAdminRepository


@dataclass(frozen=True)
class WorkflowExecutionListPage:
    items: tuple[dict[str, object], ...]
    page: int
    page_size: int
    total: int
    sort_by: str
    sort_dir: str


@dataclass(frozen=True)
class WorkflowWebhookEventListPage:
    items: tuple[dict[str, object], ...]
    page: int
    page_size: int
    total: int
    sort_by: str
    sort_dir: str


class WorkflowAdminService:
    def __init__(self, repository: WorkflowAdminRepository) -> None:
        self._repository = repository

    def list_workflows(
        self,
        *,
        country: Optional[str],
        active: Optional[bool],
        version_status: Optional[str],
    ) -> tuple[WorkflowCatalogItem, ...]:
        normalized_country = country.strip().upper() if country else None
        normalized_status = version_status.strip().upper() if version_status else None
        return self._repository.list_workflows(
            country=normalized_country,
            active=active,
            version_status=normalized_status,
        )

    def create_workflow(
        self,
        *,
        country: str,
        version: int,
        statuses: tuple[dict[str, object], ...],
        transitions: tuple[dict[str, object], ...],
    ) -> WorkflowCatalogItem:
        now = datetime.now(timezone.utc)
        return self._repository.create_workflow(
            country=country.strip().upper(),
            version=version,
            statuses=statuses,
            transitions=transitions,
            created_at=now,
        )

    def publish_workflow(
        self,
        *,
        workflow_id: uuid.UUID,
        expected_version: int,
        actor_user_id: uuid.UUID,
    ) -> WorkflowCatalogItem:
        return self._repository.publish_workflow(
            workflow_id=workflow_id,
            expected_version=expected_version,
            actor_user_id=actor_user_id,
            published_at=datetime.now(timezone.utc),
        )

    def list_executions(
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
    ) -> WorkflowExecutionListPage:
        normalized_status = status.strip().upper() if status else None
        items, total = self._repository.list_execution_summaries(
            workflow_id=workflow_id,
            status=normalized_status,
            application_id=application_id.strip() if application_id else None,
            operation_id=operation_id.strip() if operation_id else None,
            sub_operation_id=sub_operation_id.strip() if sub_operation_id else None,
            from_ts=from_ts.strip() if from_ts else None,
            to_ts=to_ts.strip() if to_ts else None,
            correlation_id=correlation_id.strip() if correlation_id else None,
            sort_by=sort_by.strip().lower(),
            sort_dir=sort_dir.strip().lower(),
            page=page,
            page_size=page_size,
        )
        return WorkflowExecutionListPage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            sort_by=sort_by.strip().lower(),
            sort_dir=sort_dir.strip().lower(),
        )

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
    ) -> WorkflowWebhookEventListPage:
        items, total = self._repository.list_webhook_events(
            workflow_id=workflow_id,
            direction=direction.strip().upper() if direction else None,
            event_type=event_type.strip() if event_type else None,
            delivery_status=delivery_status.strip().upper() if delivery_status else None,
            application_id=application_id.strip() if application_id else None,
            correlation_id=correlation_id.strip() if correlation_id else None,
            sort_by=sort_by.strip().lower(),
            sort_dir=sort_dir.strip().lower(),
            page=page,
            page_size=page_size,
        )
        return WorkflowWebhookEventListPage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            sort_by=sort_by.strip().lower(),
            sort_dir=sort_dir.strip().lower(),
        )

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
    ) -> WorkflowGraphUpsertResult:
        return self._repository.upsert_workflow_graph(
            workflow_id=workflow_id,
            expected_version=expected_version,
            operations=operations,
            deleted_operation_ids=deleted_operation_ids,
            deleted_sub_operation_ids=deleted_sub_operation_ids,
            deleted_trigger_ids=deleted_trigger_ids,
            if_match=if_match,
            updated_at=datetime.now(timezone.utc),
        )

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
    ) -> WebhookEndpointSummary:
        return self._repository.create_webhook_endpoint(
            workflow_id=workflow_id,
            direction=direction,
            provider_code=provider_code,
            event_type=event_type,
            method=method,
            url=url,
            secret_ref=secret_ref,
            timeout_ms=timeout_ms,
            active=active,
            actor_user_id=actor_user_id,
            created_at=datetime.now(timezone.utc),
        )

    def update_webhook_endpoint(
        self,
        *,
        workflow_id: uuid.UUID,
        endpoint_id: uuid.UUID,
        active: Optional[bool],
        method: Optional[str],
        url: Optional[str],
        timeout_ms: Optional[int],
    ) -> WebhookEndpointSummary:
        return self._repository.update_webhook_endpoint(
            workflow_id=workflow_id,
            endpoint_id=endpoint_id,
            active=active,
            method=method,
            url=url,
            timeout_ms=timeout_ms,
            updated_at=datetime.now(timezone.utc),
        )

    def rotate_webhook_endpoint_secret(
        self,
        *,
        workflow_id: uuid.UUID,
        endpoint_id: uuid.UUID,
        reason: str,
    ) -> WebhookEndpointSummary:
        return self._repository.rotate_webhook_endpoint_secret(
            workflow_id=workflow_id,
            endpoint_id=endpoint_id,
            reason=reason,
            rotated_at=datetime.now(timezone.utc),
        )

    def replay_webhook_event(
        self,
        *,
        workflow_id: uuid.UUID,
        webhook_event_id: uuid.UUID,
        command_id: uuid.UUID,
        reason: str,
        requested_by: uuid.UUID,
    ) -> WebhookReplayQueuedResult:
        return self._repository.replay_webhook_event(
            workflow_id=workflow_id,
            webhook_event_id=webhook_event_id,
            command_id=command_id,
            reason=reason,
            requested_by=requested_by,
            requested_at=datetime.now(timezone.utc),
        )
