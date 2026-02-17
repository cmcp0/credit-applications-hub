from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.backend.api.applications.router import router as applications_router
from apps.backend.auth.dependencies import require_permissions

router = APIRouter(tags=["api"])
router.include_router(applications_router)


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
