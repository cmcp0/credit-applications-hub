from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


WORKFLOWS_EVENTS_EXCHANGE = "workflows.events"
WORKFLOW_DEFINITION_PUBLISHED_ROUTING_KEY = "credit.workflow.definition.published"


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
class WorkflowDefinitionPublished:
    event_id: str
    occurred_at: datetime
    request_id: str
    correlation_id: str
    workflow_id: str
    country: str
    version: int
    graph_revision: int
    version_status: str
    published_by: str
    published_at: datetime

    def to_integration_event(self) -> IntegrationEvent:
        return IntegrationEvent(
            event_name="WorkflowDefinitionPublished",
            schema_version="v1",
            event_id=self.event_id,
            occurred_at=self.occurred_at,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            payload={
                "workflow_id": self.workflow_id,
                "country": self.country,
                "version": self.version,
                "graph_revision": self.graph_revision,
                "version_status": self.version_status,
                "published_by": self.published_by,
                "published_at": self.published_at.isoformat(),
            },
        )

