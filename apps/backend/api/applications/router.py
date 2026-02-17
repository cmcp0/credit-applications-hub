from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Query, status

from apps.backend.api.applications.dependencies import (
    get_create_application_service,
    get_get_application_service,
    get_list_applications_service,
    get_update_application_status_service,
)
from apps.backend.api.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationCreateResponse,
    ApplicationDetailResponse,
    ApplicationListResponse,
    ApplicationStatusMetadataResponse,
    ApplicationStatusUpdateRequest,
    ApplicationStatusUpdateResponse,
    ErrorResponse,
    ValidationErrorResponse,
)
from apps.backend.auth.dependencies import (
    get_current_principal,
    require_any_permissions,
    require_permissions,
)
from src.applications.application.application.commands.create_application import CreateApplicationCommand
from src.applications.application.application.commands.update_application_status import (
    UpdateApplicationStatusCommand,
)
from src.applications.application.application.queries.get_application import GetApplicationQuery
from src.applications.application.application.queries.list_applications import ListApplicationsQuery
from src.applications.application.application.services.create_application_service import (
    CreateApplicationService,
)
from src.applications.application.application.services.get_application_service import GetApplicationService
from src.applications.application.application.services.list_applications_service import (
    ListApplicationsService,
)
from src.applications.application.application.services.update_application_status_service import (
    UpdateApplicationStatusService,
)
from src.applications.application.domain.value_objects import ApplicationDetail, ApplicationSummary
from src.applications.shared.domain.errors import ValidationError
from src.applications.shared.domain.value_objects import FieldValidationError
from src.auth.authorization.domain.entities import AuthenticatedPrincipal

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationCreateResponse,
    responses={
        400: {"model": ValidationErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("applications:create"))],
)
def create_application(
    payload: ApplicationCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    create_service: Annotated[CreateApplicationService, Depends(get_create_application_service)],
    x_request_id: Annotated[Optional[str], Header(alias="X-Request-Id")] = None,
    x_correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
) -> ApplicationCreateResponse:
    request_id, correlation_id = _resolve_trace_ids(x_request_id, x_correlation_id)
    result = create_service.create(
        CreateApplicationCommand(
            owner_id=principal.user_id,
            country=payload.country,
            full_name=payload.full_name,
            identity_document=payload.identity_document,
            requested_amount=payload.requested_amount,
            monthly_income=payload.monthly_income,
            request_id=request_id,
            correlation_id=correlation_id,
        )
    )
    return ApplicationCreateResponse(
        id=result.id,
        country=result.country,
        status_code=result.status_code,
        created_at=result.created_at,
    )


@router.get(
    "",
    response_model=ApplicationListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_any_permissions("applications:list_own", "applications:list_all"))],
)
def list_applications(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    list_service: Annotated[ListApplicationsService, Depends(get_list_applications_service)],
    country: Annotated[Optional[str], Query()] = None,
    status_code: Annotated[Optional[str], Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApplicationListResponse:
    page_result = list_service.list(
        ListApplicationsQuery(
            actor_user_id=principal.user_id,
            can_list_all="applications:list_all" in principal.permissions,
            country=country,
            status=status_code,
            page=page,
            page_size=page_size,
        )
    )

    return ApplicationListResponse(
        items=[_summary_response(item) for item in page_result.items],
        page=page_result.page,
        page_size=page_result.page_size,
        total=page_result.total,
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_any_permissions("applications:list_own", "applications:list_all"))],
)
def get_application(
    application_id: str,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    get_service: Annotated[GetApplicationService, Depends(get_get_application_service)],
) -> ApplicationDetailResponse:
    detail = get_service.get(
        GetApplicationQuery(
            actor_user_id=principal.user_id,
            can_list_all="applications:list_all" in principal.permissions,
            application_id=application_id,
        )
    )
    return _detail_response(detail)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationStatusUpdateResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("applications:update_customer"))],
)
def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    update_service: Annotated[
        UpdateApplicationStatusService,
        Depends(get_update_application_status_service),
    ],
    x_command_id: Annotated[Optional[str], Header(alias="X-Command-Id")] = None,
    x_request_id: Annotated[Optional[str], Header(alias="X-Request-Id")] = None,
    x_correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-Id")] = None,
) -> ApplicationStatusUpdateResponse:
    request_id, correlation_id = _resolve_trace_ids(x_request_id, x_correlation_id)
    command_id = _resolve_command_id(x_command_id)
    actor_role = principal.roles[0] if principal.roles else "operation"

    result = update_service.update(
        UpdateApplicationStatusCommand(
            command_id=command_id,
            application_id=application_id,
            target_status_code=payload.status,
            actor_user_id=principal.user_id,
            actor_role=actor_role,
            reason_code=payload.reason_code,
            expected_version=payload.expected_version,
            request_id=request_id,
            correlation_id=correlation_id,
            requested_at=datetime.now(timezone.utc),
        ),
        trusted_producer=True,
    )
    return ApplicationStatusUpdateResponse(
        id=result.id,
        previous_status_code=result.previous_status_code,
        status_code=result.status_code,
        updated_at=result.updated_at,
        version=result.version,
    )


def _resolve_trace_ids(
    request_id: Optional[str],
    correlation_id: Optional[str],
) -> tuple[str, str]:
    resolved_request_id = request_id or str(uuid.uuid4())
    resolved_correlation_id = correlation_id or resolved_request_id

    _validate_uuid(resolved_request_id, field="request_id")
    _validate_uuid(resolved_correlation_id, field="correlation_id")
    return resolved_request_id, resolved_correlation_id


def _resolve_command_id(command_id: Optional[str]) -> str:
    resolved = command_id or str(uuid.uuid4())
    _validate_uuid(resolved, field="command_id")
    return resolved


def _validate_uuid(value: str, *, field: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise ValidationError(
            errors=[
                FieldValidationError(
                    field=field,
                    code="INVALID_FORMAT",
                    message=f"{field} must be a valid UUID",
                )
            ]
        ) from exc


def _summary_response(summary: ApplicationSummary) -> dict[str, object]:
    return {
        "id": summary.id,
        "country": summary.country,
        "status_code": summary.status_code,
        "requested_amount": summary.requested_amount,
        "created_at": summary.created_at,
        "updated_at": summary.updated_at,
    }


def _detail_response(detail: ApplicationDetail) -> ApplicationDetailResponse:
    return ApplicationDetailResponse(
        id=detail.id,
        country=detail.country,
        status_code=detail.status_code,
        requested_amount=detail.requested_amount,
        created_at=detail.created_at,
        updated_at=detail.updated_at,
        version=detail.version,
        status_metadata=ApplicationStatusMetadataResponse(
            code=detail.status_metadata.code,
            label=detail.status_metadata.label,
            is_terminal=detail.status_metadata.is_terminal,
            allowed_transitions=list(detail.status_metadata.allowed_transitions),
        ),
    )
