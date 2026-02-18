from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import and_, delete, func, inspect, select, text
from sqlalchemy.orm import Session

from src.applications.execution.infrastructure.adapters.execution_orm_model import WorkerJobOrm
from src.applications.shared.domain.errors import (
    EtagMismatchError,
    GraphValidationError,
    InvalidQueryParamsError,
    PreconditionRequiredError,
    ReplayCommandDuplicateError,
    ReplayCooldownActiveError,
    ReplayRateLimitExceededError,
    VersionConflictError,
    WebhookEndpointNotFoundError,
    WebhookEndpointValidationError,
    WebhookEndpointWorkflowMismatchError,
    WebhookEventNotFoundError,
    WorkflowAdminNotFoundError,
    WorkflowNotDraftError,
    WorkflowValidationFailedError,
)
from src.applications.shared.infrastructure.adapters.outbox_event_orm_model import OutboxEventOrm
from src.applications.workflow.domain.events import (
    WORKFLOW_DEFINITION_PUBLISHED_ROUTING_KEY,
    WORKFLOWS_EVENTS_EXCHANGE,
    WorkflowDefinitionPublished,
)
from src.applications.workflow.domain.admin_entities import (
    WebhookEndpointSummary,
    WebhookReplayQueuedResult,
    WorkflowCatalogItem,
    WorkflowGraphCounts,
    WorkflowGraphUpsertResult,
)
from src.applications.workflow.domain.ports.workflow_admin_repository import WorkflowAdminRepository
from src.applications.workflow.infrastructure.adapters.workflow_orm_model import (
    StatusOrm,
    StatusTransitionOrm,
    WebhookDeliveryAttemptOrm,
    WebhookEndpointOrm,
    WebhookEventOrm,
    WebhookReplayCommandOrm,
    WorkflowOperationOrm,
    WorkflowOrm,
    WorkflowSubOperationOrm,
    WorkflowSubOperationTriggerOrm,
)


class SqlAlchemyWorkflowAdminRepository(WorkflowAdminRepository):
    DRAFT_STATUS = "DRAFT"
    PUBLISHED_STATUS = "PUBLISHED"
    ALLOWED_EXECUTION_TYPES = {
        "QUERY_USE_CASE",
        "COMMAND_USE_CASE",
        "THIRD_PARTY_HTTP_REQUEST",
    }
    ALLOWED_TRIGGER_TYPES = {
        "TRIGGER_EVENT",
        "TRIGGER_COMMAND",
        "TRIGGER_WEBHOOK_EGRESS",
    }
    ALLOWED_DIRECTIONS = {"INGRESS", "EGRESS"}
    ALLOWED_WEBHOOK_DELIVERY_STATUSES = {
        "RECEIVED",
        "QUEUED",
        "DELIVERED",
        "FAILED",
        "DEAD_LETTERED",
    }
    ALLOWED_EXECUTION_STATUSES = {"PENDING", "RUNNING", "SUCCEEDED", "FAILED", "DEAD_LETTERED"}
    ALLOWED_METHODS = {"POST", "PUT", "PATCH"}
    REPLAY_COOLDOWN_SECONDS = 60
    REPLAY_RATE_WINDOW_SECONDS = 60
    REPLAY_RATE_LIMIT_MAX = 20

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_workflows(
        self,
        *,
        country: Optional[str],
        active: Optional[bool],
        version_status: Optional[str],
    ) -> tuple[WorkflowCatalogItem, ...]:
        statement = select(WorkflowOrm).order_by(
            WorkflowOrm.country.asc(),
            WorkflowOrm.version.desc(),
            WorkflowOrm.created_at.desc(),
        )
        if country:
            statement = statement.where(WorkflowOrm.country == country)
        if active is not None:
            statement = statement.where(WorkflowOrm.active.is_(active))
        if version_status:
            statement = statement.where(WorkflowOrm.version_status == version_status)

        rows = self._session.execute(statement).scalars().all()
        return tuple(self._catalog_item(row) for row in rows)

    def create_workflow(
        self,
        *,
        country: str,
        version: int,
        statuses: tuple[dict[str, object], ...],
        transitions: tuple[dict[str, object], ...],
        created_at: datetime,
    ) -> WorkflowCatalogItem:
        self._validate_status_graph(statuses=statuses, transitions=transitions)
        existing = self._session.execute(
            select(WorkflowOrm.id).where(
                WorkflowOrm.country == country,
                WorkflowOrm.version == version,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise VersionConflictError()

        workflow = WorkflowOrm(
            id=uuid.uuid4(),
            country=country,
            active=False,
            version=version,
            graph_revision=0,
            version_status=self.DRAFT_STATUS,
            published_by=None,
            published_at=None,
            created_at=created_at,
            updated_at=created_at,
        )
        self._session.add(workflow)

        status_id_by_code: dict[str, uuid.UUID] = {}
        for raw_status in statuses:
            status_id = uuid.uuid4()
            code = str(raw_status["code"]).strip().upper()
            status_id_by_code[code] = status_id
            self._session.add(
                StatusOrm(
                    id=status_id,
                    workflow_id=workflow.id,
                    code=code,
                    label=str(raw_status["label"]).strip(),
                    is_terminal=bool(raw_status["is_terminal"]),
                    is_initial=bool(raw_status["is_initial"]),
                    sort_order=int(raw_status["sort_order"]),
                )
            )

        for raw_transition in transitions:
            from_code = str(raw_transition["from"]).strip().upper()
            to_code = str(raw_transition["to"]).strip().upper()
            self._session.add(
                StatusTransitionOrm(
                    id=uuid.uuid4(),
                    from_status_id=status_id_by_code[from_code],
                    to_status_id=status_id_by_code[to_code],
                )
            )

        self._session.commit()
        self._session.refresh(workflow)
        return self._catalog_item(workflow)

    def publish_workflow(
        self,
        *,
        workflow_id: uuid.UUID,
        expected_version: int,
        actor_user_id: uuid.UUID,
        published_at: datetime,
    ) -> WorkflowCatalogItem:
        workflow = self._session.get(WorkflowOrm, workflow_id)
        if workflow is None:
            raise WorkflowAdminNotFoundError()

        if workflow.version != expected_version:
            raise VersionConflictError()
        if workflow.version_status != self.DRAFT_STATUS:
            raise WorkflowNotDraftError()

        self._validate_publishable_status_graph(workflow_id=workflow.id)

        self._session.execute(
            text(
                """
                UPDATE workflows
                SET active = FALSE, updated_at = :updated_at
                WHERE country = :country
                  AND id != :workflow_id
                  AND version_status = :published_status
                  AND active = TRUE
                """
            ),
            {
                "updated_at": published_at,
                "country": workflow.country,
                "workflow_id": str(workflow.id),
                "published_status": self.PUBLISHED_STATUS,
            },
        )

        workflow.active = True
        workflow.version_status = self.PUBLISHED_STATUS
        workflow.published_by = actor_user_id
        workflow.published_at = published_at
        workflow.updated_at = published_at
        self._enqueue_workflow_definition_published_event(workflow=workflow, occurred_at=published_at)
        self._session.commit()
        self._session.refresh(workflow)
        return self._catalog_item(workflow)

    def workflow_exists(self, workflow_id: uuid.UUID) -> bool:
        existing = self._session.execute(
            select(WorkflowOrm.id).where(WorkflowOrm.id == workflow_id)
        ).scalar_one_or_none()
        return existing is not None

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
        if not self.workflow_exists(workflow_id):
            raise WorkflowAdminNotFoundError()

        if not self._has_table("worker_jobs"):
            return tuple(), 0

        normalized_sort_by = self._normalize_execution_sort_by(sort_by)
        normalized_sort_dir = self._normalize_sort_dir(sort_dir)
        sort_column_map = {
            "updated_at": WorkerJobOrm.updated_at,
            "available_at": WorkerJobOrm.available_at,
            "created_at": WorkerJobOrm.created_at,
        }
        sort_column = sort_column_map[normalized_sort_by]
        order_clause = sort_column.asc() if normalized_sort_dir == "asc" else sort_column.desc()

        filters = [WorkerJobOrm.workflow_id == workflow_id]
        if status:
            if status not in self.ALLOWED_EXECUTION_STATUSES:
                raise InvalidQueryParamsError("status must be one of PENDING, RUNNING, SUCCEEDED, FAILED, DEAD_LETTERED")
            filters.append(WorkerJobOrm.status == status)

        parsed_application_id = self._parse_query_uuid(application_id, field_name="application_id")
        if parsed_application_id is not None:
            filters.append(WorkerJobOrm.application_id == parsed_application_id)

        parsed_operation_id = self._parse_query_uuid(operation_id, field_name="operation_id")
        if parsed_operation_id is not None:
            filters.append(WorkerJobOrm.operation_id == parsed_operation_id)

        parsed_sub_operation_id = self._parse_query_uuid(
            sub_operation_id,
            field_name="sub_operation_id",
        )
        if parsed_sub_operation_id is not None:
            filters.append(WorkerJobOrm.sub_operation_id == parsed_sub_operation_id)

        parsed_correlation_id = self._parse_query_uuid(correlation_id, field_name="correlation_id")
        if parsed_correlation_id is not None:
            filters.append(WorkerJobOrm.correlation_id == parsed_correlation_id)

        parsed_from_ts = self._parse_query_datetime(from_ts, field_name="from")
        parsed_to_ts = self._parse_query_datetime(to_ts, field_name="to")
        if parsed_from_ts and parsed_to_ts and parsed_from_ts > parsed_to_ts:
            raise InvalidQueryParamsError("'from' must be before or equal to 'to'")
        if parsed_from_ts is not None:
            filters.append(WorkerJobOrm.created_at >= parsed_from_ts)
        if parsed_to_ts is not None:
            filters.append(WorkerJobOrm.created_at <= parsed_to_ts)

        offset = (page - 1) * page_size
        total = int(
            self._session.execute(
                select(func.count()).select_from(WorkerJobOrm).where(and_(*filters))
            ).scalar_one()
        )

        rows = self._session.execute(
            select(WorkerJobOrm, WorkflowOperationOrm, WorkflowSubOperationOrm)
            .outerjoin(WorkflowOperationOrm, WorkflowOperationOrm.id == WorkerJobOrm.operation_id)
            .outerjoin(WorkflowSubOperationOrm, WorkflowSubOperationOrm.id == WorkerJobOrm.sub_operation_id)
            .where(and_(*filters))
            .order_by(order_clause, WorkerJobOrm.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()

        items: list[dict[str, object]] = []
        for job, operation, sub_operation in rows:
            items.append(
                {
                    "job_id": job.id,
                    "workflow_id": job.workflow_id,
                    "workflow_revision": job.workflow_revision,
                    "application_id": job.application_id,
                    "operation": (
                        {
                            "id": str(operation.id),
                            "name": operation.name,
                            "sort_order": operation.sort_order,
                        }
                        if operation is not None
                        else None
                    ),
                    "sub_operation": (
                        {
                            "id": str(sub_operation.id),
                            "execution_type": sub_operation.execution_type,
                            "target_ref": sub_operation.target_ref,
                        }
                        if sub_operation is not None
                        else None
                    ),
                    "status": job.status,
                    "attempts": job.attempts,
                    "max_attempts": job.max_attempts,
                    "available_at": job.available_at,
                    "locked_at": job.locked_at,
                    "completed_at": job.completed_at,
                    "last_error_code": job.last_error_code,
                    "last_error_message": job.last_error_message,
                    "correlation_id": job.correlation_id,
                    "payload_summary": job.payload_summary or {},
                    "updated_at": job.updated_at,
                    "created_at": job.created_at,
                }
            )

        return tuple(items), total

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
        if not self.workflow_exists(workflow_id):
            raise WorkflowAdminNotFoundError()

        if not self._has_table("webhook_events"):
            return tuple(), 0
        attempts_available = self._has_table("webhook_delivery_attempts")

        normalized_sort_by = self._normalize_webhook_sort_by(sort_by)
        normalized_sort_dir = self._normalize_sort_dir(sort_dir)
        sort_column_map = {
            "occurred_at": WebhookEventOrm.occurred_at,
            "created_at": WebhookEventOrm.created_at,
        }
        sort_column = sort_column_map[normalized_sort_by]
        order_clause = sort_column.asc() if normalized_sort_dir == "asc" else sort_column.desc()

        filters = [WebhookEventOrm.workflow_id == workflow_id]
        if direction:
            if direction not in self.ALLOWED_DIRECTIONS:
                raise InvalidQueryParamsError("direction must be INGRESS or EGRESS")
            filters.append(WebhookEventOrm.direction == direction)
        if event_type:
            filters.append(WebhookEventOrm.event_type == event_type)
        if delivery_status:
            if delivery_status not in self.ALLOWED_WEBHOOK_DELIVERY_STATUSES:
                raise InvalidQueryParamsError(
                    "delivery_status must be one of RECEIVED, QUEUED, DELIVERED, FAILED, DEAD_LETTERED"
                )
            filters.append(WebhookEventOrm.delivery_status == delivery_status)

        parsed_application_id = self._parse_query_uuid(application_id, field_name="application_id")
        if parsed_application_id is not None:
            filters.append(WebhookEventOrm.application_id == parsed_application_id)

        parsed_correlation_id = self._parse_query_uuid(correlation_id, field_name="correlation_id")
        if parsed_correlation_id is not None:
            filters.append(WebhookEventOrm.correlation_id == parsed_correlation_id)

        offset = (page - 1) * page_size
        total = int(
            self._session.execute(
                select(func.count()).select_from(WebhookEventOrm).where(and_(*filters))
            ).scalar_one()
        )
        rows = self._session.execute(
            select(WebhookEventOrm)
            .where(and_(*filters))
            .order_by(order_clause, WebhookEventOrm.id.asc())
            .offset(offset)
            .limit(page_size)
        ).scalars()

        items: list[dict[str, object]] = []
        for row in rows:
            row_map = {
                "id": row.id,
                "endpoint_id": row.endpoint_id,
                "provider_code": row.provider_code,
                "direction": row.direction,
                "event_type": row.event_type,
                "application_id": row.application_id,
                "payload_hash": row.payload_hash,
                "signature_valid": row.signature_valid,
                "delivery_status": row.delivery_status,
                "correlation_id": row.correlation_id,
                "occurred_at": row.occurred_at,
                "created_at": row.created_at,
            }
            latest_attempt = None
            if attempts_available:
                latest_attempt = self._session.execute(
                    text(
                        """
                        SELECT
                          attempt_no,
                          delivery_status,
                          response_code,
                          error_code,
                          error_message,
                          next_retry_at,
                          created_at
                        FROM webhook_delivery_attempts
                        WHERE webhook_event_id = :webhook_event_id
                        ORDER BY attempt_no DESC, created_at DESC
                        LIMIT 1
                        """
                    ),
                    {"webhook_event_id": str(row.id)},
                ).mappings().one_or_none()
            row_map["last_attempt"] = dict(latest_attempt) if latest_attempt else None
            items.append(row_map)

        return tuple(items), total

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
        workflow = self._session.get(WorkflowOrm, workflow_id)
        if workflow is None:
            raise WorkflowAdminNotFoundError()
        if workflow.version_status != self.DRAFT_STATUS:
            raise WorkflowNotDraftError()
        if expected_version is None and not if_match:
            raise PreconditionRequiredError()
        if expected_version is not None and workflow.version != expected_version:
            raise VersionConflictError()

        current_etag = self._build_graph_etag(workflow)
        if if_match is not None and if_match.strip() != current_etag:
            raise EtagMismatchError()

        self._validate_operation_graph(operations)
        self._apply_graph_deletes(
            workflow_id=workflow.id,
            deleted_operation_ids=deleted_operation_ids,
            deleted_sub_operation_ids=deleted_sub_operation_ids,
            deleted_trigger_ids=deleted_trigger_ids,
        )
        self._upsert_operations(
            workflow_id=workflow.id,
            operations=operations,
            updated_at=updated_at,
        )

        workflow.graph_revision += 1
        workflow.updated_at = updated_at
        self._session.commit()
        self._session.refresh(workflow)

        counts = self._graph_counts(workflow.id)
        return WorkflowGraphUpsertResult(
            workflow_id=str(workflow.id),
            version=workflow.version,
            graph_revision=workflow.graph_revision,
            etag=self._build_graph_etag(workflow),
            counts=counts,
            updated_at=workflow.updated_at,
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
        created_at: datetime,
    ) -> WebhookEndpointSummary:
        workflow = self._session.get(WorkflowOrm, workflow_id)
        if workflow is None:
            raise WorkflowAdminNotFoundError()

        normalized_direction = direction.strip().upper()
        normalized_method = method.strip().upper()
        normalized_provider = provider_code.strip()
        normalized_event = event_type.strip()
        normalized_url = url.strip()
        normalized_secret_ref = secret_ref.strip()

        self._validate_webhook_endpoint_payload(
            direction=normalized_direction,
            method=normalized_method,
            url=normalized_url,
            timeout_ms=timeout_ms,
            secret_ref=normalized_secret_ref,
            provider_code=normalized_provider,
            event_type=normalized_event,
        )

        endpoint = WebhookEndpointOrm(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            country=workflow.country,
            provider_code=normalized_provider,
            direction=normalized_direction,
            event_type=normalized_event,
            method=normalized_method,
            url=normalized_url,
            secret_ref=normalized_secret_ref,
            timeout_ms=timeout_ms,
            active=active,
            created_by=actor_user_id,
            created_at=created_at,
            updated_at=created_at,
        )
        self._session.add(endpoint)
        self._session.commit()
        self._session.refresh(endpoint)
        return WebhookEndpointSummary(
            endpoint_id=str(endpoint.id),
            direction=endpoint.direction,
            active=endpoint.active,
            workflow_id=str(endpoint.workflow_id),
            updated_at=endpoint.updated_at,
            secret_ref=None,
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
        updated_at: datetime,
    ) -> WebhookEndpointSummary:
        endpoint = self._session.get(WebhookEndpointOrm, endpoint_id)
        if endpoint is None:
            raise WebhookEndpointNotFoundError()
        if endpoint.workflow_id != workflow_id:
            raise WebhookEndpointWorkflowMismatchError()

        if method is not None:
            normalized_method = method.strip().upper()
            if normalized_method not in self.ALLOWED_METHODS:
                raise WebhookEndpointValidationError("Unsupported webhook endpoint method")
            endpoint.method = normalized_method
        if url is not None:
            normalized_url = url.strip()
            self._validate_url(normalized_url)
            endpoint.url = normalized_url
        if timeout_ms is not None:
            if timeout_ms < 1000 or timeout_ms > 30000:
                raise WebhookEndpointValidationError("timeout_ms must be between 1000 and 30000")
            endpoint.timeout_ms = timeout_ms
        if active is not None:
            endpoint.active = active

        endpoint.updated_at = updated_at
        self._session.commit()
        self._session.refresh(endpoint)
        return WebhookEndpointSummary(
            endpoint_id=str(endpoint.id),
            direction=endpoint.direction,
            active=endpoint.active,
            workflow_id=str(endpoint.workflow_id),
            updated_at=endpoint.updated_at,
            secret_ref=None,
        )

    def rotate_webhook_endpoint_secret(
        self,
        *,
        workflow_id: uuid.UUID,
        endpoint_id: uuid.UUID,
        reason: str,
        rotated_at: datetime,
    ) -> WebhookEndpointSummary:
        endpoint = self._session.get(WebhookEndpointOrm, endpoint_id)
        if endpoint is None:
            raise WebhookEndpointNotFoundError()
        if endpoint.workflow_id != workflow_id:
            raise WebhookEndpointWorkflowMismatchError()
        if not reason.strip():
            raise WebhookEndpointValidationError("reason is required")

        timestamp = rotated_at.strftime("%Y%m%d%H%M%S")
        endpoint.secret_ref = f"{endpoint.secret_ref.rstrip('/')}/rotated/{timestamp}"
        endpoint.updated_at = rotated_at
        self._session.commit()
        self._session.refresh(endpoint)
        return WebhookEndpointSummary(
            endpoint_id=str(endpoint.id),
            direction=endpoint.direction,
            active=endpoint.active,
            workflow_id=str(endpoint.workflow_id),
            updated_at=endpoint.updated_at,
            secret_ref=endpoint.secret_ref,
        )

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
        if not self.workflow_exists(workflow_id):
            raise WorkflowAdminNotFoundError()

        event = self._session.get(WebhookEventOrm, webhook_event_id)
        if event is None or event.workflow_id != workflow_id:
            raise WebhookEventNotFoundError()
        if self._session.get(WebhookReplayCommandOrm, command_id) is not None:
            raise ReplayCommandDuplicateError()

        cooldown_cutoff = requested_at - timedelta(seconds=self.REPLAY_COOLDOWN_SECONDS)
        recent_same_event = self._session.execute(
            select(WebhookReplayCommandOrm.command_id).where(
                WebhookReplayCommandOrm.webhook_event_id == webhook_event_id,
                WebhookReplayCommandOrm.requested_at >= cooldown_cutoff,
            )
        ).scalar_one_or_none()
        if recent_same_event is not None:
            raise ReplayCooldownActiveError()

        rate_window_cutoff = requested_at - timedelta(seconds=self.REPLAY_RATE_WINDOW_SECONDS)
        replay_count = int(
            self._session.execute(
                select(func.count())
                .select_from(WebhookReplayCommandOrm)
                .where(
                    WebhookReplayCommandOrm.workflow_id == workflow_id,
                    WebhookReplayCommandOrm.requested_by == requested_by,
                    WebhookReplayCommandOrm.requested_at >= rate_window_cutoff,
                )
            ).scalar_one()
        )
        if replay_count >= self.REPLAY_RATE_LIMIT_MAX:
            raise ReplayRateLimitExceededError()

        self._session.add(
            WebhookReplayCommandOrm(
                command_id=command_id,
                workflow_id=workflow_id,
                webhook_event_id=webhook_event_id,
                requested_by=requested_by,
                reason=reason.strip(),
                requested_at=requested_at,
            )
        )
        event.delivery_status = "QUEUED"
        self._session.commit()
        return WebhookReplayQueuedResult(queued=True, command_id=str(command_id))

    def _validate_status_graph(
        self,
        *,
        statuses: tuple[dict[str, object], ...],
        transitions: tuple[dict[str, object], ...],
    ) -> None:
        if not statuses:
            raise WorkflowValidationFailedError("Workflow requires at least one status")

        status_codes = [str(status["code"]).strip().upper() for status in statuses]
        if len(set(status_codes)) != len(status_codes):
            raise WorkflowValidationFailedError("Status codes must be unique within a workflow version")

        initial_count = sum(1 for status in statuses if bool(status["is_initial"]))
        if initial_count != 1:
            raise WorkflowValidationFailedError("Workflow requires exactly one initial status")

        terminal_codes = {
            str(status["code"]).strip().upper()
            for status in statuses
            if bool(status["is_terminal"])
        }
        status_code_set = set(status_codes)
        for transition in transitions:
            from_code = str(transition["from"]).strip().upper()
            to_code = str(transition["to"]).strip().upper()
            if from_code not in status_code_set or to_code not in status_code_set:
                raise WorkflowValidationFailedError("Transition references unknown status code")
            if from_code in terminal_codes:
                raise WorkflowValidationFailedError("Terminal statuses cannot have outgoing transitions")

    def _validate_publishable_status_graph(self, *, workflow_id: uuid.UUID) -> None:
        initial_count = self._session.execute(
            select(func.count())
            .select_from(StatusOrm)
            .where(
                StatusOrm.workflow_id == workflow_id,
                StatusOrm.is_initial.is_(True),
            )
        ).scalar_one()
        if int(initial_count) != 1:
            raise WorkflowValidationFailedError("Workflow requires exactly one initial status")

        invalid_terminal_transition = self._session.execute(
            select(StatusTransitionOrm.id)
            .join(StatusOrm, StatusOrm.id == StatusTransitionOrm.from_status_id)
            .where(
                StatusOrm.workflow_id == workflow_id,
                StatusOrm.is_terminal.is_(True),
            )
            .limit(1)
        ).scalar_one_or_none()
        if invalid_terminal_transition is not None:
            raise WorkflowValidationFailedError("Terminal statuses cannot have outgoing transitions")

    def _validate_operation_graph(self, operations: tuple[dict[str, object], ...]) -> None:
        self._assert_contiguous_sort_order(
            [int(raw_operation.get("sort_order", 0)) for raw_operation in operations],
            "operations",
        )
        for raw_operation in operations:
            name = str(raw_operation.get("name", "")).strip()
            if not name:
                raise GraphValidationError("Operation name is required")

            raw_sub_operations = raw_operation.get("sub_operations", [])
            if not isinstance(raw_sub_operations, list):
                raise GraphValidationError("sub_operations must be a list")
            self._assert_contiguous_sort_order(
                [int(raw_sub_operation.get("sort_order", 0)) for raw_sub_operation in raw_sub_operations],
                "sub_operations",
            )

            for raw_sub_operation in raw_sub_operations:
                execution_type = str(raw_sub_operation.get("execution_type", "")).strip().upper()
                if execution_type not in self.ALLOWED_EXECUTION_TYPES:
                    raise GraphValidationError("Invalid execution_type")

                target_ref = str(raw_sub_operation.get("target_ref", "")).strip()
                if execution_type == "THIRD_PARTY_HTTP_REQUEST" and not target_ref:
                    raise GraphValidationError("target_ref is required for THIRD_PARTY_HTTP_REQUEST")

                raw_triggers = raw_sub_operation.get("triggers", [])
                if not isinstance(raw_triggers, list):
                    raise GraphValidationError("triggers must be a list")

                for raw_trigger in raw_triggers:
                    trigger_type = str(raw_trigger.get("trigger_type", "")).strip().upper()
                    if trigger_type not in self.ALLOWED_TRIGGER_TYPES:
                        raise GraphValidationError("Invalid trigger_type")
                    trigger_name = str(raw_trigger.get("trigger_name", "")).strip()
                    if not trigger_name:
                        raise GraphValidationError("trigger_name is required")

    def _assert_contiguous_sort_order(self, sort_orders: list[int], scope_name: str) -> None:
        if not sort_orders:
            return
        expected = list(range(1, len(sort_orders) + 1))
        if sorted(sort_orders) != expected:
            raise GraphValidationError(f"{scope_name} sort_order must be contiguous and unique")

    def _apply_graph_deletes(
        self,
        *,
        workflow_id: uuid.UUID,
        deleted_operation_ids: tuple[uuid.UUID, ...],
        deleted_sub_operation_ids: tuple[uuid.UUID, ...],
        deleted_trigger_ids: tuple[uuid.UUID, ...],
    ) -> None:
        if deleted_trigger_ids:
            trigger_scope = (
                select(WorkflowSubOperationTriggerOrm.id)
                .join(
                    WorkflowSubOperationOrm,
                    WorkflowSubOperationOrm.id == WorkflowSubOperationTriggerOrm.sub_operation_id,
                )
                .join(
                    WorkflowOperationOrm,
                    WorkflowOperationOrm.id == WorkflowSubOperationOrm.operation_id,
                )
                .where(WorkflowOperationOrm.workflow_id == workflow_id)
            )
            self._session.execute(
                delete(WorkflowSubOperationTriggerOrm).where(
                    WorkflowSubOperationTriggerOrm.id.in_(deleted_trigger_ids),
                    WorkflowSubOperationTriggerOrm.id.in_(trigger_scope),
                )
            )

        if deleted_sub_operation_ids:
            sub_operation_scope = (
                select(WorkflowSubOperationOrm.id)
                .join(WorkflowOperationOrm, WorkflowOperationOrm.id == WorkflowSubOperationOrm.operation_id)
                .where(WorkflowOperationOrm.workflow_id == workflow_id)
            )
            self._session.execute(
                delete(WorkflowSubOperationTriggerOrm).where(
                    WorkflowSubOperationTriggerOrm.sub_operation_id.in_(deleted_sub_operation_ids),
                    WorkflowSubOperationTriggerOrm.sub_operation_id.in_(sub_operation_scope),
                )
            )
            self._session.execute(
                delete(WorkflowSubOperationOrm).where(
                    WorkflowSubOperationOrm.id.in_(deleted_sub_operation_ids),
                    WorkflowSubOperationOrm.id.in_(sub_operation_scope),
                )
            )

        if deleted_operation_ids:
            operation_scope = select(WorkflowOperationOrm.id).where(
                WorkflowOperationOrm.workflow_id == workflow_id
            )
            sub_operation_ids = self._session.execute(
                select(WorkflowSubOperationOrm.id).where(
                    WorkflowSubOperationOrm.operation_id.in_(deleted_operation_ids),
                    WorkflowSubOperationOrm.operation_id.in_(operation_scope),
                )
            ).scalars().all()
            if sub_operation_ids:
                self._session.execute(
                    delete(WorkflowSubOperationTriggerOrm).where(
                        WorkflowSubOperationTriggerOrm.sub_operation_id.in_(sub_operation_ids)
                    )
                )
                self._session.execute(
                    delete(WorkflowSubOperationOrm).where(
                        WorkflowSubOperationOrm.id.in_(sub_operation_ids)
                    )
                )
            self._session.execute(
                delete(WorkflowOperationOrm).where(
                    WorkflowOperationOrm.id.in_(deleted_operation_ids),
                    WorkflowOperationOrm.id.in_(operation_scope),
                )
            )

    def _upsert_operations(
        self,
        *,
        workflow_id: uuid.UUID,
        operations: tuple[dict[str, object], ...],
        updated_at: datetime,
    ) -> None:
        existing_operations = {
            row.id: row
            for row in self._session.execute(
                select(WorkflowOperationOrm).where(WorkflowOperationOrm.workflow_id == workflow_id)
            ).scalars()
        }

        for raw_operation in operations:
            operation_id = self._parse_uuid(raw_operation.get("id"))
            operation_name = str(raw_operation["name"]).strip()
            operation_sort_order = int(raw_operation["sort_order"])
            operation_active = bool(raw_operation.get("active", True))
            if operation_id and operation_id in existing_operations:
                operation = existing_operations[operation_id]
                operation.name = operation_name
                operation.sort_order = operation_sort_order
                operation.active = operation_active
                operation.updated_at = updated_at
            else:
                operation = WorkflowOperationOrm(
                    id=operation_id or uuid.uuid4(),
                    workflow_id=workflow_id,
                    name=operation_name,
                    sort_order=operation_sort_order,
                    active=operation_active,
                    created_at=updated_at,
                    updated_at=updated_at,
                )
                self._session.add(operation)
                self._session.flush()

            self._upsert_sub_operations(
                operation_id=operation.id,
                raw_sub_operations=raw_operation.get("sub_operations", []),
                updated_at=updated_at,
            )

    def _upsert_sub_operations(
        self,
        *,
        operation_id: uuid.UUID,
        raw_sub_operations: Any,
        updated_at: datetime,
    ) -> None:
        if not isinstance(raw_sub_operations, list):
            raise GraphValidationError("sub_operations must be a list")

        existing_sub_operations = {
            row.id: row
            for row in self._session.execute(
                select(WorkflowSubOperationOrm).where(WorkflowSubOperationOrm.operation_id == operation_id)
            ).scalars()
        }

        for raw_sub_operation in raw_sub_operations:
            sub_operation_id = self._parse_uuid(raw_sub_operation.get("id"))
            execution_type = str(raw_sub_operation["execution_type"]).strip().upper()
            target_ref = str(raw_sub_operation["target_ref"]).strip()
            input_template = self._normalize_json_map(
                raw_sub_operation.get("input_template", {}),
                "input_template",
            )
            output_alias = raw_sub_operation.get("output_alias")
            if output_alias is not None:
                output_alias = str(output_alias).strip() or None

            if sub_operation_id and sub_operation_id in existing_sub_operations:
                sub_operation = existing_sub_operations[sub_operation_id]
                sub_operation.sort_order = int(raw_sub_operation["sort_order"])
                sub_operation.execution_type = execution_type
                sub_operation.target_ref = target_ref
                sub_operation.input_template = input_template
                sub_operation.output_alias = output_alias
                sub_operation.active = bool(raw_sub_operation.get("active", True))
                sub_operation.updated_at = updated_at
            else:
                sub_operation = WorkflowSubOperationOrm(
                    id=sub_operation_id or uuid.uuid4(),
                    operation_id=operation_id,
                    sort_order=int(raw_sub_operation["sort_order"]),
                    execution_type=execution_type,
                    target_ref=target_ref,
                    input_template=input_template,
                    output_alias=output_alias,
                    active=bool(raw_sub_operation.get("active", True)),
                    created_at=updated_at,
                    updated_at=updated_at,
                )
                self._session.add(sub_operation)
                self._session.flush()

            self._upsert_triggers(
                sub_operation_id=sub_operation.id,
                raw_triggers=raw_sub_operation.get("triggers", []),
                updated_at=updated_at,
            )

    def _upsert_triggers(
        self,
        *,
        sub_operation_id: uuid.UUID,
        raw_triggers: Any,
        updated_at: datetime,
    ) -> None:
        if not isinstance(raw_triggers, list):
            raise GraphValidationError("triggers must be a list")

        existing_triggers = {
            row.id: row
            for row in self._session.execute(
                select(WorkflowSubOperationTriggerOrm).where(
                    WorkflowSubOperationTriggerOrm.sub_operation_id == sub_operation_id
                )
            ).scalars()
        }

        for raw_trigger in raw_triggers:
            trigger_id = self._parse_uuid(raw_trigger.get("id"))
            payload_template = self._normalize_json_map(
                raw_trigger.get("payload_template", {}),
                "payload_template",
            )
            condition_expr = raw_trigger.get("condition_expr")
            if condition_expr is not None:
                condition_expr = str(condition_expr).strip() or None

            if trigger_id and trigger_id in existing_triggers:
                trigger = existing_triggers[trigger_id]
                trigger.trigger_type = str(raw_trigger["trigger_type"]).strip().upper()
                trigger.trigger_name = str(raw_trigger["trigger_name"]).strip()
                trigger.payload_template = payload_template
                trigger.condition_expr = condition_expr
                trigger.updated_at = updated_at
            else:
                trigger = WorkflowSubOperationTriggerOrm(
                    id=trigger_id or uuid.uuid4(),
                    sub_operation_id=sub_operation_id,
                    trigger_type=str(raw_trigger["trigger_type"]).strip().upper(),
                    trigger_name=str(raw_trigger["trigger_name"]).strip(),
                    payload_template=payload_template,
                    condition_expr=condition_expr,
                    created_at=updated_at,
                    updated_at=updated_at,
                )
                self._session.add(trigger)

    def _graph_counts(self, workflow_id: uuid.UUID) -> WorkflowGraphCounts:
        operations_count = int(
            self._session.execute(
                select(func.count()).select_from(WorkflowOperationOrm).where(
                    WorkflowOperationOrm.workflow_id == workflow_id
                )
            ).scalar_one()
        )
        sub_operations_count = int(
            self._session.execute(
                select(func.count())
                .select_from(WorkflowSubOperationOrm)
                .join(WorkflowOperationOrm, WorkflowOperationOrm.id == WorkflowSubOperationOrm.operation_id)
                .where(WorkflowOperationOrm.workflow_id == workflow_id)
            ).scalar_one()
        )
        triggers_count = int(
            self._session.execute(
                select(func.count())
                .select_from(WorkflowSubOperationTriggerOrm)
                .join(
                    WorkflowSubOperationOrm,
                    WorkflowSubOperationOrm.id == WorkflowSubOperationTriggerOrm.sub_operation_id,
                )
                .join(WorkflowOperationOrm, WorkflowOperationOrm.id == WorkflowSubOperationOrm.operation_id)
                .where(WorkflowOperationOrm.workflow_id == workflow_id)
            ).scalar_one()
        )
        return WorkflowGraphCounts(
            operations=operations_count,
            sub_operations=sub_operations_count,
            triggers=triggers_count,
        )

    def _validate_webhook_endpoint_payload(
        self,
        *,
        direction: str,
        method: str,
        url: str,
        timeout_ms: int,
        secret_ref: str,
        provider_code: str,
        event_type: str,
    ) -> None:
        if direction not in self.ALLOWED_DIRECTIONS:
            raise WebhookEndpointValidationError("Invalid webhook direction")
        if method not in self.ALLOWED_METHODS:
            raise WebhookEndpointValidationError("Unsupported webhook endpoint method")
        if timeout_ms < 1000 or timeout_ms > 30000:
            raise WebhookEndpointValidationError("timeout_ms must be between 1000 and 30000")
        if not secret_ref:
            raise WebhookEndpointValidationError("secret_ref is required")
        if not provider_code:
            raise WebhookEndpointValidationError("provider_code is required")
        if not event_type:
            raise WebhookEndpointValidationError("event_type is required")
        self._validate_url(url)

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise WebhookEndpointValidationError("url must be a valid http or https URL")

    def _normalize_json_map(self, payload: Any, field_name: str) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise GraphValidationError(f"{field_name} must be an object")
        return dict(payload)

    def _parse_uuid(self, raw_value: Any) -> Optional[uuid.UUID]:
        if raw_value is None:
            return None
        if isinstance(raw_value, uuid.UUID):
            return raw_value
        if isinstance(raw_value, str):
            stripped = raw_value.strip()
            if not stripped:
                return None
            try:
                return uuid.UUID(stripped)
            except ValueError as exc:
                raise GraphValidationError("Invalid UUID value in workflow graph payload") from exc
        raise GraphValidationError("Invalid UUID value in workflow graph payload")

    def _build_graph_etag(self, workflow: WorkflowOrm) -> str:
        return f'W/"workflow:{workflow.id}:v{workflow.version}:r{workflow.graph_revision}"'

    def _catalog_item(self, row: WorkflowOrm) -> WorkflowCatalogItem:
        return WorkflowCatalogItem(
            id=str(row.id),
            country=row.country,
            version=row.version,
            version_status=row.version_status,
            active=row.active,
            published_at=row.published_at,
        )

    def _enqueue_workflow_definition_published_event(
        self,
        *,
        workflow: WorkflowOrm,
        occurred_at: datetime,
    ) -> None:
        event_id = uuid.uuid4()
        correlation_id = uuid.uuid4()
        domain_event = WorkflowDefinitionPublished(
            event_id=str(event_id),
            occurred_at=occurred_at,
            request_id=str(event_id),
            correlation_id=str(correlation_id),
            workflow_id=str(workflow.id),
            country=workflow.country,
            version=workflow.version,
            graph_revision=workflow.graph_revision,
            version_status=workflow.version_status,
            published_by=str(workflow.published_by),
            published_at=workflow.published_at or occurred_at,
        ).to_integration_event()

        self._session.add(
            OutboxEventOrm(
                id=event_id,
                aggregate_type="workflow",
                aggregate_id=workflow.id,
                exchange_name=WORKFLOWS_EVENTS_EXCHANGE,
                routing_key=WORKFLOW_DEFINITION_PUBLISHED_ROUTING_KEY,
                event_name=domain_event.event_name,
                schema_version=domain_event.schema_version,
                correlation_id=correlation_id,
                payload={
                    "event_name": domain_event.event_name,
                    "schema_version": domain_event.schema_version,
                    "event_id": domain_event.event_id,
                    "occurred_at": domain_event.occurred_at.isoformat(),
                    "request_id": domain_event.request_id,
                    "correlation_id": domain_event.correlation_id,
                    "payload": domain_event.payload,
                },
                publish_status="PENDING",
                attempts=0,
                last_error=None,
                next_attempt_at=occurred_at,
                locked_at=None,
                locked_by=None,
                occurred_at=occurred_at,
                created_at=occurred_at,
            )
        )

    def _normalize_sort_dir(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"asc", "desc"}:
            raise InvalidQueryParamsError("sort_dir must be 'asc' or 'desc'")
        return normalized

    def _normalize_execution_sort_by(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"updated_at", "available_at", "created_at"}:
            raise InvalidQueryParamsError(
                "sort_by must be one of updated_at, available_at, created_at"
            )
        return normalized

    def _normalize_webhook_sort_by(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"occurred_at", "created_at"}:
            raise InvalidQueryParamsError("sort_by must be one of occurred_at, created_at")
        return normalized

    def _parse_query_uuid(self, raw: Optional[str], *, field_name: str) -> Optional[uuid.UUID]:
        if raw is None:
            return None
        stripped = raw.strip()
        if not stripped:
            return None
        try:
            return uuid.UUID(stripped)
        except ValueError as exc:
            raise InvalidQueryParamsError(f"{field_name} must be a valid UUID") from exc

    def _parse_query_datetime(self, raw: Optional[str], *, field_name: str) -> Optional[datetime]:
        if raw is None:
            return None
        stripped = raw.strip()
        if not stripped:
            return None
        try:
            parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvalidQueryParamsError(f"{field_name} must be an ISO-8601 datetime") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _has_table(self, table_name: str) -> bool:
        bind = self._session.get_bind()
        inspector = inspect(bind)
        return inspector.has_table(table_name)
