from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Query, status

from apps.backend.api.workflows.dependencies import get_workflow_admin_service
from apps.backend.api.workflows.schemas import (
    CreateWebhookEndpointRequest,
    CreateWebhookEndpointResponse,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    ErrorResponse,
    PublishWorkflowRequest,
    PublishWorkflowResponse,
    ReplayWebhookEventRequest,
    ReplayWebhookEventResponse,
    RotateWebhookEndpointSecretRequest,
    RotateWebhookEndpointSecretResponse,
    UpdateWebhookEndpointRequest,
    UpdateWebhookEndpointResponse,
    UpsertWorkflowGraphRequest,
    UpsertWorkflowGraphResponse,
    WorkflowExecutionListResponse,
    WorkflowExecutionSummaryResponse,
    WorkflowGraphCountsResponse,
    WorkflowListResponse,
    WorkflowSummaryResponse,
    WorkflowWebhookEventLastAttemptResponse,
    WorkflowWebhookEventListResponse,
    WorkflowWebhookEventSummaryResponse,
)
from apps.backend.auth.dependencies import get_current_principal, require_permissions
from src.applications.workflow.application.services.workflow_admin_service import WorkflowAdminService
from src.auth.authorization.domain.entities import AuthenticatedPrincipal

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get(
    "",
    response_model=WorkflowListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def list_workflows(
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
    country: Annotated[Optional[str], Query()] = None,
    active: Annotated[Optional[bool], Query()] = None,
    version_status: Annotated[Optional[str], Query()] = None,
) -> WorkflowListResponse:
    items = service.list_workflows(country=country, active=active, version_status=version_status)
    return WorkflowListResponse(
        items=[
            WorkflowSummaryResponse(
                id=item.id,
                country=item.country,
                version=item.version,
                version_status=item.version_status,
                active=item.active,
                published_at=item.published_at,
            )
            for item in items
        ]
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateWorkflowResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def create_workflow(
    payload: CreateWorkflowRequest,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
) -> CreateWorkflowResponse:
    created = service.create_workflow(
        country=payload.country,
        version=payload.version,
        statuses=tuple(item.model_dump() for item in payload.statuses),
        transitions=tuple(item.model_dump(by_alias=True) for item in payload.transitions),
    )
    return CreateWorkflowResponse(
        id=created.id,
        country=created.country,
        version=created.version,
        version_status=created.version_status,
    )


@router.put(
    "/{workflow_id}/graph",
    response_model=UpsertWorkflowGraphResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        412: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        428: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def upsert_workflow_graph(
    workflow_id: uuid.UUID,
    payload: UpsertWorkflowGraphRequest,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
    if_match: Annotated[Optional[str], Header(alias="If-Match")] = None,
) -> UpsertWorkflowGraphResponse:
    result = service.upsert_workflow_graph(
        workflow_id=workflow_id,
        expected_version=payload.expected_version,
        operations=tuple(item.model_dump() for item in payload.operations),
        deleted_operation_ids=tuple(payload.deleted_operation_ids),
        deleted_sub_operation_ids=tuple(payload.deleted_sub_operation_ids),
        deleted_trigger_ids=tuple(payload.deleted_trigger_ids),
        if_match=if_match,
    )
    return UpsertWorkflowGraphResponse(
        workflow_id=result.workflow_id,
        version=result.version,
        graph_revision=result.graph_revision,
        etag=result.etag,
        counts=WorkflowGraphCountsResponse(
            operations=result.counts.operations,
            sub_operations=result.counts.sub_operations,
            triggers=result.counts.triggers,
        ),
        updated_at=result.updated_at,
    )


@router.post(
    "/{workflow_id}/publish",
    response_model=PublishWorkflowResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def publish_workflow(
    workflow_id: uuid.UUID,
    payload: PublishWorkflowRequest,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> PublishWorkflowResponse:
    published = service.publish_workflow(
        workflow_id=workflow_id,
        expected_version=payload.expected_version,
        actor_user_id=uuid.UUID(principal.user_id),
    )
    return PublishWorkflowResponse(
        workflow_id=published.id,
        country=published.country,
        version=published.version,
        version_status=published.version_status,
        active=published.active,
        published_at=published.published_at,  # type: ignore[arg-type]
    )


@router.post(
    "/{workflow_id}/webhooks/endpoints",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateWebhookEndpointResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def create_webhook_endpoint(
    workflow_id: uuid.UUID,
    payload: CreateWebhookEndpointRequest,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> CreateWebhookEndpointResponse:
    endpoint = service.create_webhook_endpoint(
        workflow_id=workflow_id,
        direction=payload.direction,
        provider_code=payload.provider_code,
        event_type=payload.event_type,
        method=payload.method,
        url=payload.url,
        secret_ref=payload.secret_ref,
        timeout_ms=payload.timeout_ms,
        active=payload.active,
        actor_user_id=uuid.UUID(principal.user_id),
    )
    return CreateWebhookEndpointResponse(
        endpoint_id=endpoint.endpoint_id,
        direction=endpoint.direction,
        active=endpoint.active,
    )


@router.patch(
    "/{workflow_id}/webhooks/endpoints/{endpoint_id}",
    response_model=UpdateWebhookEndpointResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def update_webhook_endpoint(
    workflow_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    payload: UpdateWebhookEndpointRequest,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
) -> UpdateWebhookEndpointResponse:
    endpoint = service.update_webhook_endpoint(
        workflow_id=workflow_id,
        endpoint_id=endpoint_id,
        active=payload.active,
        method=payload.method,
        url=payload.url,
        timeout_ms=payload.timeout_ms,
    )
    return UpdateWebhookEndpointResponse(
        endpoint_id=endpoint.endpoint_id,
        workflow_id=endpoint.workflow_id or str(workflow_id),
        active=endpoint.active,
        updated_at=endpoint.updated_at,  # type: ignore[arg-type]
    )


@router.post(
    "/{workflow_id}/webhooks/endpoints/{endpoint_id}/rotate-secret",
    response_model=RotateWebhookEndpointSecretResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def rotate_webhook_endpoint_secret(
    workflow_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    payload: RotateWebhookEndpointSecretRequest,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
) -> RotateWebhookEndpointSecretResponse:
    endpoint = service.rotate_webhook_endpoint_secret(
        workflow_id=workflow_id,
        endpoint_id=endpoint_id,
        reason=payload.reason,
    )
    return RotateWebhookEndpointSecretResponse(
        endpoint_id=endpoint.endpoint_id,
        secret_ref=endpoint.secret_ref or "",
        rotated_at=endpoint.updated_at,  # type: ignore[arg-type]
    )


@router.get(
    "/{workflow_id}/webhooks/events",
    response_model=WorkflowWebhookEventListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def list_workflow_webhook_events(
    workflow_id: uuid.UUID,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
    direction: Annotated[Optional[str], Query()] = None,
    event_type: Annotated[Optional[str], Query()] = None,
    delivery_status: Annotated[Optional[str], Query()] = None,
    application_id: Annotated[Optional[str], Query()] = None,
    correlation_id: Annotated[Optional[str], Query()] = None,
    sort_by: Annotated[str, Query()] = "occurred_at",
    sort_dir: Annotated[str, Query()] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> WorkflowWebhookEventListResponse:
    result = service.list_webhook_events(
        workflow_id=workflow_id,
        direction=direction,
        event_type=event_type,
        delivery_status=delivery_status,
        application_id=application_id,
        correlation_id=correlation_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return WorkflowWebhookEventListResponse(
        items=[
            WorkflowWebhookEventSummaryResponse(
                id=str(item["id"]),
                endpoint_id=str(item["endpoint_id"]),
                provider_code=str(item.get("provider_code", "")),
                direction=str(item["direction"]),
                event_type=str(item["event_type"]),
                application_id=str(item["application_id"]) if item.get("application_id") else None,
                payload_hash=str(item["payload_hash"]),
                signature_valid=(
                    bool(item["signature_valid"])
                    if item.get("signature_valid") is not None
                    else None
                ),
                delivery_status=str(item["delivery_status"]),
                correlation_id=str(item["correlation_id"]),
                occurred_at=item["occurred_at"],  # type: ignore[arg-type]
                created_at=item["created_at"],  # type: ignore[arg-type]
                last_attempt=(
                    WorkflowWebhookEventLastAttemptResponse(**item["last_attempt"])
                    if item.get("last_attempt")
                    else None
                ),
            )
            for item in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        sort_by=result.sort_by,
        sort_dir=result.sort_dir,
    )


@router.post(
    "/{workflow_id}/webhooks/events/{webhook_event_id}/replay",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ReplayWebhookEventResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def replay_webhook_event(
    workflow_id: uuid.UUID,
    webhook_event_id: uuid.UUID,
    payload: ReplayWebhookEventRequest,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> ReplayWebhookEventResponse:
    result = service.replay_webhook_event(
        workflow_id=workflow_id,
        webhook_event_id=webhook_event_id,
        command_id=payload.command_id,
        reason=payload.reason,
        requested_by=uuid.UUID(principal.user_id),
    )
    return ReplayWebhookEventResponse(queued=result.queued, command_id=result.command_id)


@router.get(
    "/{workflow_id}/executions",
    response_model=WorkflowExecutionListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def list_workflow_executions(
    workflow_id: uuid.UUID,
    service: Annotated[WorkflowAdminService, Depends(get_workflow_admin_service)],
    status: Annotated[Optional[str], Query()] = None,
    application_id: Annotated[Optional[str], Query()] = None,
    operation_id: Annotated[Optional[str], Query()] = None,
    sub_operation_id: Annotated[Optional[str], Query()] = None,
    from_ts: Annotated[Optional[str], Query(alias="from")] = None,
    to_ts: Annotated[Optional[str], Query(alias="to")] = None,
    correlation_id: Annotated[Optional[str], Query()] = None,
    sort_by: Annotated[str, Query()] = "updated_at",
    sort_dir: Annotated[str, Query()] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> WorkflowExecutionListResponse:
    result = service.list_executions(
        workflow_id=workflow_id,
        status=status,
        application_id=application_id,
        operation_id=operation_id,
        sub_operation_id=sub_operation_id,
        from_ts=from_ts,
        to_ts=to_ts,
        correlation_id=correlation_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return WorkflowExecutionListResponse(
        items=[
            WorkflowExecutionSummaryResponse(
                job_id=str(item["job_id"]),
                workflow_id=str(item["workflow_id"]),
                workflow_revision=int(item["workflow_revision"]),
                application_id=str(item["application_id"]) if item.get("application_id") else None,
                operation=(
                    dict(item["operation"]) if isinstance(item.get("operation"), dict) else None
                ),
                sub_operation=(
                    dict(item["sub_operation"])
                    if isinstance(item.get("sub_operation"), dict)
                    else None
                ),
                status=str(item["status"]),
                attempts=int(item["attempts"]),
                max_attempts=int(item["max_attempts"]),
                available_at=item.get("available_at"),  # type: ignore[arg-type]
                locked_at=item.get("locked_at"),  # type: ignore[arg-type]
                completed_at=item.get("completed_at"),  # type: ignore[arg-type]
                last_error_code=(
                    str(item["last_error_code"]) if item.get("last_error_code") else None
                ),
                last_error_message=(
                    str(item["last_error_message"]) if item.get("last_error_message") else None
                ),
                correlation_id=str(item["correlation_id"]),
                payload_summary=(
                    dict(item["payload_summary"])
                    if isinstance(item.get("payload_summary"), dict)
                    else {}
                ),
                updated_at=item["updated_at"],  # type: ignore[arg-type]
                created_at=item["created_at"],  # type: ignore[arg-type]
            )
            for item in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        sort_by=result.sort_by,
        sort_dir=result.sort_dir,
    )
