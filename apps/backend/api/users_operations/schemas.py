from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    code: str
    message: str


class OperationUserSummaryResponse(BaseModel):
    user_id: str
    email: str
    is_active: bool
    has_operation_role: bool
    updated_at: datetime


class OperationUserListResponse(BaseModel):
    items: list[OperationUserSummaryResponse]
    page: int
    page_size: int
    total: int


class AssignOperationRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID


class AssignOperationRoleResponse(BaseModel):
    user_id: str
    assigned_role: str
    assigned_at: datetime


class UpdateOperationUserAccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class UpdateOperationUserAccessResponse(BaseModel):
    user_id: str
    enabled: bool
    updated_at: datetime
