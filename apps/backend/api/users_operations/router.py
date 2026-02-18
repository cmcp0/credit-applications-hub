from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from apps.backend.api.users_operations.dependencies import get_manage_operation_users_service
from apps.backend.api.users_operations.schemas import (
    AssignOperationRoleRequest,
    AssignOperationRoleResponse,
    ErrorResponse,
    OperationUserListResponse,
    OperationUserSummaryResponse,
    UpdateOperationUserAccessRequest,
    UpdateOperationUserAccessResponse,
)
from apps.backend.auth.dependencies import require_permissions
from src.auth.operations_admin.application.services.manage_operation_users_service import (
    ManageOperationUsersService,
)

router = APIRouter(prefix="/users/operations", tags=["users_operations"])


@router.get(
    "",
    response_model=OperationUserListResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("users:manage_operations"))],
)
def list_operation_users(
    service: Annotated[ManageOperationUsersService, Depends(get_manage_operation_users_service)],
    active: Annotated[Optional[bool], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OperationUserListResponse:
    result = service.list_operation_users(active=active, page=page, page_size=page_size)
    return OperationUserListResponse(
        items=[
            OperationUserSummaryResponse(
                user_id=item.user_id,
                email=item.email,
                is_active=item.is_active,
                has_operation_role=item.has_operation_role,
                updated_at=item.updated_at,
            )
            for item in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AssignOperationRoleResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("users:manage_operations"))],
)
def assign_operation_role(
    payload: AssignOperationRoleRequest,
    service: Annotated[ManageOperationUsersService, Depends(get_manage_operation_users_service)],
) -> AssignOperationRoleResponse:
    assigned_at = service.assign_operation_role(user_id=uuid.UUID(str(payload.user_id)))
    return AssignOperationRoleResponse(
        user_id=str(payload.user_id),
        assigned_role="operation",
        assigned_at=assigned_at,
    )


@router.patch(
    "/{user_id}",
    response_model=UpdateOperationUserAccessResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    dependencies=[Depends(require_permissions("users:manage_operations"))],
)
def update_operation_user_access(
    user_id: uuid.UUID,
    payload: UpdateOperationUserAccessRequest,
    service: Annotated[ManageOperationUsersService, Depends(get_manage_operation_users_service)],
) -> UpdateOperationUserAccessResponse:
    updated_at = service.set_operation_access(user_id=user_id, enabled=payload.enabled)
    return UpdateOperationUserAccessResponse(
        user_id=str(user_id),
        enabled=payload.enabled,
        updated_at=updated_at,
    )

