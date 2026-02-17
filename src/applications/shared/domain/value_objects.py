from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldValidationError:
    field: str
    code: str
    message: str


@dataclass(frozen=True)
class CorrelationMetadata:
    request_id: str
    correlation_id: str
