from __future__ import annotations

import uuid
from src.applications.application.application.commands.update_application_status import (
    UpdateApplicationStatusCommand,
)
from src.applications.application.domain.events import ApplicationStatusUpdated
from src.applications.application.domain.ports.application_repository import ApplicationRepository
from src.applications.application.domain.ports.outbox_event_writer import OutboxEventWriter
from src.applications.application.domain.ports.status_history_repository import StatusHistoryRepository
from src.applications.application.domain.value_objects import StatusUpdateResult
from src.applications.shared.domain.errors import (
    ApplicationNotFoundError,
    UntrustedCommandProducerError,
    ValidationError,
    VersionConflictError,
)
from src.applications.shared.domain.value_objects import FieldValidationError
from src.applications.workflow.application.services.validate_status_transition_service import (
    ValidateStatusTransitionService,
)


class UpdateApplicationStatusService:
    def __init__(
        self,
        application_repository: ApplicationRepository,
        outbox_event_writer: OutboxEventWriter,
        status_history_repository: StatusHistoryRepository,
        validate_status_transition_service: ValidateStatusTransitionService,
    ) -> None:
        self._application_repository = application_repository
        self._outbox_event_writer = outbox_event_writer
        self._status_history_repository = status_history_repository
        self._validate_status_transition_service = validate_status_transition_service

    def update(
        self,
        command: UpdateApplicationStatusCommand,
        *,
        trusted_producer: bool = True,
    ) -> StatusUpdateResult:
        if not trusted_producer:
            raise UntrustedCommandProducerError()

        if command.expected_version < 1:
            raise ValidationError(
                [
                    FieldValidationError(
                        field="expected_version",
                        code="INVALID_VALUE",
                        message="Expected version must be greater than zero",
                    )
                ]
            )

        self._validate_command_id(command.command_id)

        existing_history = self._status_history_repository.get_by_command_id(command.command_id)
        if existing_history is not None:
            if existing_history.application_id != command.application_id:
                raise ValidationError(
                    [
                        FieldValidationError(
                            field="command_id",
                            code="ALREADY_USED",
                            message="Command id was already used for a different application",
                        )
                    ]
                )

            application = self._application_repository.get_by_id(command.application_id)
            if application is None:
                raise ApplicationNotFoundError()

            return StatusUpdateResult(
                id=application.id,
                previous_status_code=existing_history.from_status_code,
                status_code=application.status_code,
                updated_at=application.updated_at,
                version=application.version,
            )

        application = self._application_repository.get_by_id(command.application_id)
        if application is None:
            raise ApplicationNotFoundError()

        if application.status_code == command.target_status_code:
            return StatusUpdateResult(
                id=application.id,
                previous_status_code=application.status_code,
                status_code=application.status_code,
                updated_at=application.updated_at,
                version=application.version,
            )

        if application.version != command.expected_version:
            raise VersionConflictError()

        self._validate_status_transition_service.validate(
            country=application.country,
            from_status_code=application.status_code,
            to_status_code=command.target_status_code,
        )

        previous_status_code = application.transition_status(
            target_status_code=command.target_status_code,
            changed_at=command.requested_at,
        )

        event = ApplicationStatusUpdated(
            event_id=str(uuid.uuid4()),
            occurred_at=command.requested_at,
            request_id=command.request_id,
            correlation_id=command.correlation_id,
            application_id=application.id,
            country=application.country,
            previous_status_code=previous_status_code,
            current_status_code=application.status_code,
            actor_user_id=command.actor_user_id,
            actor_role=command.actor_role,
            version=application.version,
        ).to_integration_event()

        try:
            self._application_repository.save(
                application,
                expected_previous_version=command.expected_version,
            )
            self._status_history_repository.append(
                application_id=application.id,
                from_status_code=previous_status_code,
                to_status_code=application.status_code,
                application_version=application.version,
                reason_code=command.reason_code,
                actor_user_id=command.actor_user_id,
                actor_role=command.actor_role,
                command_id=command.command_id,
                correlation_id=command.correlation_id,
                changed_at=command.requested_at,
            )
            self._outbox_event_writer.write(
                aggregate_type="application",
                aggregate_id=application.id,
                exchange_name="applications.events",
                routing_key="credit.application.status.updated",
                event=event,
            )
            self._application_repository.commit()
        except Exception:
            self._application_repository.rollback()
            duplicate_history = self._status_history_repository.get_by_command_id(command.command_id)
            if duplicate_history is None:
                raise

            refreshed_application = self._application_repository.get_by_id(command.application_id)
            if refreshed_application is None:
                raise ApplicationNotFoundError()

            return StatusUpdateResult(
                id=refreshed_application.id,
                previous_status_code=duplicate_history.from_status_code,
                status_code=refreshed_application.status_code,
                updated_at=refreshed_application.updated_at,
                version=refreshed_application.version,
            )

        return StatusUpdateResult(
            id=application.id,
            previous_status_code=previous_status_code,
            status_code=application.status_code,
            updated_at=application.updated_at,
            version=application.version,
        )

    def _validate_command_id(self, command_id: str) -> None:
        try:
            uuid.UUID(command_id)
        except ValueError as exc:
            raise ValidationError(
                [
                    FieldValidationError(
                        field="command_id",
                        code="INVALID_FORMAT",
                        message="Command id must be a valid UUID",
                    )
                ]
            ) from exc
