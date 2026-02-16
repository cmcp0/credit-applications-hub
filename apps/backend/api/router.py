from __future__ import annotations

from typing import Optional
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from apps.backend.auth.dependencies import (
    get_current_principal,
    owner_scope_for_customer,
    require_any_permissions,
    require_permissions,
)
from apps.backend.auth.schemas import ApplicationCreateRequest, ApplicationStatusUpdateRequest
from src.auth.authorization.domain.entities import AuthenticatedPrincipal

router = APIRouter(tags=["api"])


@router.post("/applications", dependencies=[Depends(require_permissions("applications:create"))])
def create_application(
    payload: ApplicationCreateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> dict[str, object]:
    application = {
        "id": f"app-{len(_app_store(request)) + 1}",
        "country": payload.country,
        "requested_amount": payload.requested_amount,
        "owner_id": principal.user_id,
        "status": "created",
    }
    _app_store(request).append(application)
    return application


@router.get(
    "/applications",
    dependencies=[Depends(require_any_permissions("applications:list_own", "applications:list_all"))],
)
def list_applications(
    request: Request,
    owner_scope: Annotated[Optional[str], Depends(owner_scope_for_customer)],
) -> list[dict[str, object]]:
    applications = _app_store(request)
    if owner_scope:
        return [item for item in applications if item.get("owner_id") == owner_scope]
    return list(applications)


@router.patch(
    "/applications/{application_id}/status",
    dependencies=[Depends(require_permissions("applications:update_customer"))],
)
def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdateRequest,
    request: Request,
) -> dict[str, object]:
    for application in _app_store(request):
        if application["id"] == application_id:
            application["status"] = payload.status
            return application

    return {"id": application_id, "status": payload.status, "updated": False}


@router.get(
    "/users/operations",
    dependencies=[Depends(require_permissions("users:manage_operations"))],
)
def list_operation_users() -> dict[str, object]:
    return {"items": []}


@router.get(
    "/workflows",
    dependencies=[Depends(require_permissions("workflows:manage"))],
)
def list_workflows() -> dict[str, object]:
    return {"items": []}


def _app_store(request: Request) -> list[dict[str, object]]:
    if not hasattr(request.app.state, "applications_store"):
        request.app.state.applications_store = []
    return request.app.state.applications_store
