from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorResponse(BaseModel):
    code: str
    message: str


class ValidationErrorItem(BaseModel):
    field: str
    code: str
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[ValidationErrorItem]


class ApplicationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str
    full_name: str = Field(min_length=1, max_length=120)
    identity_document: str = Field(min_length=1, max_length=64)
    requested_amount: float
    monthly_income: float

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.strip().upper()


class ApplicationCreateResponse(BaseModel):
    id: str
    country: str
    status_code: str
    created_at: datetime


class ApplicationSummaryResponse(BaseModel):
    id: str
    country: str
    status_code: str
    requested_amount: float
    created_at: datetime
    updated_at: datetime


class ApplicationListResponse(BaseModel):
    items: list[ApplicationSummaryResponse]
    page: int
    page_size: int
    total: int


class ApplicationStatusMetadataResponse(BaseModel):
    code: str
    label: str
    is_terminal: bool
    allowed_transitions: list[str]


class ApplicationDetailResponse(BaseModel):
    id: str
    country: str
    status_code: str
    requested_amount: float
    created_at: datetime
    updated_at: datetime
    version: int
    status_metadata: ApplicationStatusMetadataResponse


class ApplicationStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    reason_code: Optional[str] = Field(default=None, max_length=120)
    expected_version: int = Field(ge=1)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().upper()


class ApplicationStatusUpdateResponse(BaseModel):
    id: str
    previous_status_code: str
    status_code: str
    updated_at: datetime
    version: int
