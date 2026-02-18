from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


SUPPORTED_COUNTRIES = ("BR", "CL", "CO", "ES", "MX", "PE")


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class ApplicationSummary:
    id: str
    country: str
    status_code: str
    requested_amount: float
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ApplicationStatusMetadata:
    code: str
    label: str
    is_terminal: bool
    allowed_transitions: tuple[str, ...]


@dataclass(frozen=True)
class ApplicationDetail:
    id: str
    country: str
    status_code: str
    requested_amount: float
    created_at: datetime
    updated_at: datetime
    version: int
    status_metadata: ApplicationStatusMetadata


@dataclass(frozen=True)
class ApplicationListPage:
    items: tuple[ApplicationSummary, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True)
class StatusUpdateResult:
    id: str
    previous_status_code: str
    status_code: str
    updated_at: datetime
    version: int
