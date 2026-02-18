from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorResponse(BaseModel):
    code: str
    message: str


class WorkflowSummaryResponse(BaseModel):
    id: str
    country: str
    version: int
    version_status: str
    active: bool
    published_at: Optional[datetime] = None


class WorkflowListResponse(BaseModel):
    items: list[WorkflowSummaryResponse]


class WorkflowStatusDefinitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str = Field(min_length=1, max_length=120)
    is_initial: bool
    is_terminal: bool
    sort_order: int = Field(ge=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class WorkflowTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_code: str = Field(alias="from")
    to_code: str = Field(alias="to")

    @field_validator("from_code", "to_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CreateWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str
    version: int = Field(ge=1)
    statuses: list[WorkflowStatusDefinitionRequest]
    transitions: list[WorkflowTransitionRequest]

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.strip().upper()


class CreateWorkflowResponse(BaseModel):
    id: str
    country: str
    version: int
    version_status: str


class WorkflowGraphTriggerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[uuid.UUID] = None
    trigger_type: str
    trigger_name: str = Field(min_length=1, max_length=200)
    payload_template: dict[str, object] = Field(default_factory=dict)
    condition_expr: Optional[str] = Field(default=None, max_length=500)

    @field_validator("trigger_type")
    @classmethod
    def normalize_trigger_type(cls, value: str) -> str:
        return value.strip().upper()


class WorkflowGraphSubOperationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[uuid.UUID] = None
    sort_order: int = Field(ge=1)
    execution_type: str
    target_ref: str = Field(min_length=1, max_length=255)
    input_template: dict[str, object] = Field(default_factory=dict)
    output_alias: Optional[str] = Field(default=None, max_length=120)
    active: bool
    triggers: list[WorkflowGraphTriggerRequest] = Field(default_factory=list)

    @field_validator("execution_type")
    @classmethod
    def normalize_execution_type(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("target_ref")
    @classmethod
    def normalize_target_ref(cls, value: str) -> str:
        return value.strip()


class WorkflowGraphOperationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[uuid.UUID] = None
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = Field(ge=1)
    active: bool
    sub_operations: list[WorkflowGraphSubOperationRequest] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class UpsertWorkflowGraphRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: Optional[int] = Field(default=None, ge=1)
    operations: list[WorkflowGraphOperationRequest] = Field(default_factory=list)
    deleted_operation_ids: list[uuid.UUID] = Field(default_factory=list)
    deleted_sub_operation_ids: list[uuid.UUID] = Field(default_factory=list)
    deleted_trigger_ids: list[uuid.UUID] = Field(default_factory=list)


class WorkflowGraphCountsResponse(BaseModel):
    operations: int
    sub_operations: int
    triggers: int


class UpsertWorkflowGraphResponse(BaseModel):
    workflow_id: str
    version: int
    graph_revision: int
    etag: str
    counts: WorkflowGraphCountsResponse
    updated_at: datetime


class PublishWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


class PublishWorkflowResponse(BaseModel):
    workflow_id: str
    country: str
    version: int
    version_status: str
    active: bool
    published_at: datetime


class CreateWebhookEndpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str
    provider_code: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=120)
    method: str
    url: str = Field(min_length=1, max_length=2000)
    secret_ref: str = Field(min_length=1, max_length=500)
    timeout_ms: int = Field(default=5000, ge=1)
    active: bool = True

    @field_validator("direction")
    @classmethod
    def normalize_direction(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("provider_code", "event_type", "url", "secret_ref")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class CreateWebhookEndpointResponse(BaseModel):
    endpoint_id: str
    direction: str
    active: bool


class UpdateWebhookEndpointRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: Optional[bool] = None
    method: Optional[str] = None
    url: Optional[str] = None
    timeout_ms: Optional[int] = Field(default=None, ge=1)

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip()


class UpdateWebhookEndpointResponse(BaseModel):
    endpoint_id: str
    workflow_id: str
    active: bool
    updated_at: datetime


class RotateWebhookEndpointSecretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=200)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class RotateWebhookEndpointSecretResponse(BaseModel):
    endpoint_id: str
    secret_ref: str
    rotated_at: datetime


class ReplayWebhookEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=200)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class ReplayWebhookEventResponse(BaseModel):
    queued: bool
    command_id: str


class WorkflowExecutionSummaryResponse(BaseModel):
    job_id: str
    workflow_id: str
    workflow_revision: int
    application_id: Optional[str] = None
    operation: Optional[dict[str, object]] = None
    sub_operation: Optional[dict[str, object]] = None
    status: str
    attempts: int
    max_attempts: int
    available_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    correlation_id: str
    payload_summary: dict[str, object] = Field(default_factory=dict)
    updated_at: datetime
    created_at: datetime


class WorkflowExecutionListResponse(BaseModel):
    items: list[WorkflowExecutionSummaryResponse]
    page: int
    page_size: int
    total: int
    sort_by: str
    sort_dir: str


class WorkflowWebhookEventLastAttemptResponse(BaseModel):
    attempt_no: int
    delivery_status: str
    response_code: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    created_at: datetime


class WorkflowWebhookEventSummaryResponse(BaseModel):
    id: str
    endpoint_id: str
    provider_code: str
    direction: str
    event_type: str
    application_id: Optional[str] = None
    payload_hash: str
    signature_valid: Optional[bool] = None
    delivery_status: str
    correlation_id: str
    occurred_at: datetime
    created_at: datetime
    last_attempt: Optional[WorkflowWebhookEventLastAttemptResponse] = None


class WorkflowWebhookEventListResponse(BaseModel):
    items: list[WorkflowWebhookEventSummaryResponse]
    page: int
    page_size: int
    total: int
    sort_by: str
    sort_dir: str
