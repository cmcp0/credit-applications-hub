from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from src.applications.shared.domain.value_objects import FieldValidationError


class ApplicationError(Exception):
    status_code = 400
    code = "APPLICATION_ERROR"
    message = "Application error"

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or self.message)
        self.message = message or self.message


class ValidationError(ApplicationError):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "Validation failed"

    def __init__(
        self,
        errors: Sequence[FieldValidationError],
        message: Optional[str] = None,
    ) -> None:
        super().__init__(message or self.message)
        self.errors = list(errors)


class ApplicationNotFoundError(ApplicationError):
    status_code = 404
    code = "APPLICATION_NOT_FOUND"
    message = "Application was not found"


class InvalidStatusTransitionError(ApplicationError):
    status_code = 409
    code = "INVALID_STATUS_TRANSITION"
    message = "Invalid status transition"


class VersionConflictError(ApplicationError):
    status_code = 409
    code = "VERSION_CONFLICT"
    message = "Version conflict"


class WorkflowNotFoundError(ApplicationError):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "No active workflow configured for country"


class UntrustedCommandProducerError(ApplicationError):
    status_code = 403
    code = "UNTRUSTED_COMMAND_PRODUCER"
    message = "Command producer is not trusted"


class ApplicationPermissionDeniedError(ApplicationError):
    status_code = 403
    code = "PERMISSION_DENIED"
    message = "Permission denied"
