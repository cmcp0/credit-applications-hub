from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, Sequence

from src.applications.application.application.commands.update_application_status import (
    UpdateApplicationStatusCommand,
)
from src.applications.application.application.services.update_application_status_service import (
    UpdateApplicationStatusService,
)
from src.applications.application.domain.value_objects import StatusUpdateResult
from src.applications.shared.domain.errors import ValidationError
from src.applications.shared.domain.value_objects import FieldValidationError

UPDATE_STATUS_COMMAND_ROUTING_KEY = "credit.application.status.update"


@dataclass(frozen=True)
class UpdateApplicationStatusMessage:
    application_id: str
    target_status_code: str
    actor_user_id: str
    actor_role: str
    expected_version: int
    request_id: str
    correlation_id: str
    producer: str
    reason_code: Optional[str] = None
    command_id: Optional[str] = None
    message_id: Optional[str] = None
    requested_at: Optional[datetime] = None


@dataclass(frozen=True)
class AuthorizedStatusActor:
    actor_user_id: str
    actor_role: str


class StatusUpdateActorAuthorizer(Protocol):
    def authorize(self, *, actor_user_id: str, requested_actor_role: str) -> AuthorizedStatusActor:
        ...


class UpdateApplicationStatusCommandConsumer:
    def __init__(
        self,
        update_service: UpdateApplicationStatusService,
        *,
        trusted_producers: Sequence[str],
        actor_authorizer: Optional[StatusUpdateActorAuthorizer] = None,
    ) -> None:
        self._update_service = update_service
        self._trusted_producers = frozenset(trusted_producers)
        self._actor_authorizer = actor_authorizer

    def consume(self, message: UpdateApplicationStatusMessage) -> StatusUpdateResult:
        command_id = message.command_id or message.message_id
        if not command_id:
            raise ValidationError(
                [
                    FieldValidationError(
                        field="command_id",
                        code="REQUIRED",
                        message="Either command_id or message_id is required for idempotency",
                    )
                ]
            )
        requested_at = message.requested_at or datetime.now(timezone.utc)
        trusted_producer = message.producer in self._trusted_producers
        actor_user_id = message.actor_user_id
        actor_role = message.actor_role

        if self._actor_authorizer is not None:
            authorized_actor = self._actor_authorizer.authorize(
                actor_user_id=message.actor_user_id,
                requested_actor_role=message.actor_role,
            )
            actor_user_id = authorized_actor.actor_user_id
            actor_role = authorized_actor.actor_role

        result = self._update_service.update(
            UpdateApplicationStatusCommand(
                command_id=command_id,
                application_id=message.application_id,
                target_status_code=message.target_status_code,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason_code=message.reason_code,
                expected_version=message.expected_version,
                request_id=message.request_id,
                correlation_id=message.correlation_id,
                requested_at=requested_at,
            ),
            trusted_producer=trusted_producer,
        )
        return result
