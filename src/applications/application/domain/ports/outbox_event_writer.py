from __future__ import annotations

from typing import Protocol

from src.applications.application.domain.events import IntegrationEvent


class OutboxEventWriter(Protocol):
    def write(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
        exchange_name: str,
        routing_key: str,
        event: IntegrationEvent,
    ) -> None:
        ...
