from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from src.applications.application.application.commands.create_application import CreateApplicationCommand
from src.applications.application.domain.entities import Application
from src.applications.application.domain.events import ApplicationCreated
from src.applications.application.domain.ports.application_repository import ApplicationRepository
from src.applications.application.domain.ports.outbox_event_writer import OutboxEventWriter
from src.applications.application.domain.value_objects import SUPPORTED_COUNTRIES
from src.applications.shared.domain.errors import ValidationError
from src.applications.shared.domain.value_objects import FieldValidationError
from src.applications.workflow.application.services.resolve_initial_status_service import (
    ResolveInitialStatusService,
)

IDENTITY_DOCUMENT_PATTERNS: dict[str, re.Pattern[str]] = {
    "MX": re.compile(r"^[A-Z0-9]{6,18}$"),
    "BR": re.compile(r"^[0-9]{11}$"),
    "CO": re.compile(r"^[A-Z0-9]{6,14}$"),
    "CL": re.compile(r"^[A-Z0-9\-]{6,14}$"),
    "PE": re.compile(r"^[0-9]{8,12}$"),
}


@dataclass(frozen=True)
class CreateApplicationResult:
    id: str
    country: str
    status_code: str
    created_at: datetime


class CreateApplicationService:
    def __init__(
        self,
        application_repository: ApplicationRepository,
        outbox_event_writer: OutboxEventWriter,
        resolve_initial_status_service: ResolveInitialStatusService,
    ) -> None:
        self._application_repository = application_repository
        self._outbox_event_writer = outbox_event_writer
        self._resolve_initial_status_service = resolve_initial_status_service

    def create(self, command: CreateApplicationCommand) -> CreateApplicationResult:
        normalized_country = command.country.strip().upper()
        validation_errors = self._validate_command(command, normalized_country)
        if validation_errors:
            raise ValidationError(validation_errors)

        created_at = datetime.now(timezone.utc)
        application = Application.create(
            application_id=str(uuid.uuid4()),
            user_id=command.owner_id,
            country=normalized_country,
            full_name=command.full_name.strip(),
            identity_document=command.identity_document.strip().upper(),
            requested_amount=float(command.requested_amount),
            monthly_income=float(command.monthly_income),
            application_date=date.today(),
            initial_status_code=self._resolve_initial_status_service.resolve(normalized_country),
            created_at=created_at,
        )

        event = ApplicationCreated(
            event_id=str(uuid.uuid4()),
            occurred_at=created_at,
            request_id=command.request_id,
            correlation_id=command.correlation_id,
            application_id=application.id,
            owner_id=application.user_id,
            country=application.country,
            status_code=application.status_code,
            application_date=application.application_date,
            version=application.version,
        ).to_integration_event()

        try:
            self._application_repository.add(application)
            self._outbox_event_writer.write(
                aggregate_type="application",
                aggregate_id=application.id,
                exchange_name="applications.events",
                routing_key="credit.application.created",
                event=event,
            )
            self._application_repository.commit()
        except Exception:
            self._application_repository.rollback()
            raise

        return CreateApplicationResult(
            id=application.id,
            country=application.country,
            status_code=application.status_code,
            created_at=application.created_at,
        )

    def _validate_command(
        self,
        command: CreateApplicationCommand,
        normalized_country: str,
    ) -> list[FieldValidationError]:
        errors: list[FieldValidationError] = []

        if normalized_country not in SUPPORTED_COUNTRIES:
            errors.append(
                FieldValidationError(
                    field="country",
                    code="UNSUPPORTED_COUNTRY",
                    message="Country is not supported",
                )
            )

        if len(command.full_name.strip()) < 3:
            errors.append(
                FieldValidationError(
                    field="full_name",
                    code="INVALID_VALUE",
                    message="Full name must have at least 3 characters",
                )
            )

        pattern = IDENTITY_DOCUMENT_PATTERNS.get(normalized_country)
        normalized_document = command.identity_document.strip().upper()
        if not normalized_document or pattern is None or not pattern.match(normalized_document):
            errors.append(
                FieldValidationError(
                    field="identity_document",
                    code="INVALID_FORMAT",
                    message="Identity document format is invalid for selected country",
                )
            )

        if command.requested_amount <= 0:
            errors.append(
                FieldValidationError(
                    field="requested_amount",
                    code="INVALID_VALUE",
                    message="Requested amount must be greater than zero",
                )
            )

        if command.monthly_income <= 0:
            errors.append(
                FieldValidationError(
                    field="monthly_income",
                    code="INVALID_VALUE",
                    message="Monthly income must be greater than zero",
                )
            )

        return errors
