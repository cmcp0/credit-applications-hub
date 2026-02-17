from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class IntegrationEvent:
    event_name: str
    schema_version: str
    event_id: str
    occurred_at: datetime
    request_id: str
    correlation_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ApplicationCreated:
    event_id: str
    occurred_at: datetime
    request_id: str
    correlation_id: str
    application_id: str
    owner_id: str
    country: str
    status_code: str
    application_date: date
    version: int

    def to_integration_event(self) -> IntegrationEvent:
        return IntegrationEvent(
            event_name="ApplicationCreated",
            schema_version="v1",
            event_id=self.event_id,
            occurred_at=self.occurred_at,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            payload={
                "application_id": self.application_id,
                "owner_id": self.owner_id,
                "country": self.country,
                "status_code": self.status_code,
                "application_date": self.application_date.isoformat(),
                "version": self.version,
            },
        )


@dataclass(frozen=True)
class ApplicationStatusUpdated:
    event_id: str
    occurred_at: datetime
    request_id: str
    correlation_id: str
    application_id: str
    country: str
    previous_status_code: str
    current_status_code: str
    actor_user_id: str
    actor_role: str
    version: int

    def to_integration_event(self) -> IntegrationEvent:
        return IntegrationEvent(
            event_name="ApplicationStatusUpdated",
            schema_version="v1",
            event_id=self.event_id,
            occurred_at=self.occurred_at,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            payload={
                "application_id": self.application_id,
                "country": self.country,
                "previous_status_code": self.previous_status_code,
                "current_status_code": self.current_status_code,
                "actor_user_id": self.actor_user_id,
                "actor_role": self.actor_role,
                "version": self.version,
            },
        )
