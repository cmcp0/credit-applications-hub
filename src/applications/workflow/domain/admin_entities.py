from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WorkflowCatalogItem:
    id: str
    country: str
    version: int
    version_status: str
    active: bool
    published_at: Optional[datetime]


@dataclass(frozen=True)
class WorkflowGraphCounts:
    operations: int
    sub_operations: int
    triggers: int


@dataclass(frozen=True)
class WorkflowGraphUpsertResult:
    workflow_id: str
    version: int
    graph_revision: int
    etag: str
    counts: WorkflowGraphCounts
    updated_at: datetime


@dataclass(frozen=True)
class WebhookEndpointSummary:
    endpoint_id: str
    direction: str
    active: bool
    workflow_id: Optional[str]
    updated_at: Optional[datetime]
    secret_ref: Optional[str]


@dataclass(frozen=True)
class WebhookReplayQueuedResult:
    queued: bool
    command_id: str
