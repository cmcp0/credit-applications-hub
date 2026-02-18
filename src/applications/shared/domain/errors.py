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


class WorkflowAdminNotFoundError(ApplicationError):
    status_code = 404
    code = "WORKFLOW_NOT_FOUND"
    message = "Workflow was not found"


class WorkflowValidationFailedError(ApplicationError):
    status_code = 409
    code = "WORKFLOW_VALIDATION_FAILED"
    message = "Workflow validation failed"


class WorkflowNotDraftError(ApplicationError):
    status_code = 409
    code = "WORKFLOW_NOT_DRAFT"
    message = "Workflow is not editable because it is not in draft status"


class PreconditionRequiredError(ApplicationError):
    status_code = 428
    code = "PRECONDITION_REQUIRED"
    message = "Missing required optimistic concurrency precondition"


class EtagMismatchError(ApplicationError):
    status_code = 412
    code = "ETAG_MISMATCH"
    message = "Workflow graph precondition did not match latest server state"


class GraphValidationError(ApplicationError):
    status_code = 422
    code = "GRAPH_VALIDATION_ERROR"
    message = "Workflow graph validation failed"


class InvalidQueryParamsError(ApplicationError):
    status_code = 422
    code = "INVALID_QUERY_PARAMS"
    message = "Invalid query parameters"


class WebhookEndpointNotFoundError(ApplicationError):
    status_code = 404
    code = "ENDPOINT_NOT_FOUND"
    message = "Webhook endpoint was not found"


class WebhookEndpointWorkflowMismatchError(ApplicationError):
    status_code = 409
    code = "ENDPOINT_WORKFLOW_MISMATCH"
    message = "Webhook endpoint does not belong to the requested workflow"


class WebhookEndpointValidationError(ApplicationError):
    status_code = 422
    code = "WEBHOOK_ENDPOINT_VALIDATION_ERROR"
    message = "Webhook endpoint validation failed"


class WebhookEventNotFoundError(ApplicationError):
    status_code = 404
    code = "WEBHOOK_EVENT_NOT_FOUND"
    message = "Webhook event was not found"


class ReplayCommandDuplicateError(ApplicationError):
    status_code = 409
    code = "REPLAY_COMMAND_DUPLICATE"
    message = "Replay command already exists"


class ReplayCooldownActiveError(ApplicationError):
    status_code = 409
    code = "REPLAY_COOLDOWN_ACTIVE"
    message = "Replay cooldown is active for this webhook event"


class ReplayRateLimitExceededError(ApplicationError):
    status_code = 429
    code = "REPLAY_RATE_LIMIT_EXCEEDED"
    message = "Replay rate limit exceeded"
