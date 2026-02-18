from __future__ import annotations

from fastapi import APIRouter

from apps.backend.api.applications.router import router as applications_router
from apps.backend.api.users_operations.router import router as users_operations_router
from apps.backend.api.workflows.router import router as workflows_router

router = APIRouter(tags=["api"])
router.include_router(applications_router)
router.include_router(users_operations_router)
router.include_router(workflows_router)
