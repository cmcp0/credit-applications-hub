from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from apps.backend.auth.dependencies import get_db_session
from src.applications.workflow.application.services.workflow_admin_service import WorkflowAdminService
from src.applications.workflow.domain.ports.workflow_admin_repository import WorkflowAdminRepository
from src.applications.workflow.infrastructure.adapters.workflow_admin_repository import (
    SqlAlchemyWorkflowAdminRepository,
)


def get_workflow_admin_repository(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorkflowAdminRepository:
    return SqlAlchemyWorkflowAdminRepository(db_session)


def get_workflow_admin_service(
    repository: Annotated[WorkflowAdminRepository, Depends(get_workflow_admin_repository)],
) -> WorkflowAdminService:
    return WorkflowAdminService(repository)

