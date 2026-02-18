from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class WebhookEndpointRuntime:
    endpoint_id: str
    workflow_id: str
    country: str
    provider_code: str
    direction: str
    event_type: str
    method: str
    url: str
    secret_ref: str
    timeout_ms: int


@dataclass(frozen=True)
class IngressWebhookAccepted:
    webhook_event_id: str
    workflow_id: str
    endpoint_id: str
    correlation_id: str
    signature_valid: Optional[bool]
    occurred_at: datetime


@dataclass(frozen=True)
class EgressDeliveryResult:
    webhook_event_id: str
    worker_job_id: str
    delivery_status: str
    attempts: int
    max_attempts: int
    response_code: Optional[int]
    retry_scheduled: bool
    terminal_failure: bool
    duplicate_consumption: bool

