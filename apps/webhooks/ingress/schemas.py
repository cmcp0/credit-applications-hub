from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IngressWebhookAcceptedResponse(BaseModel):
    webhook_event_id: str
    workflow_id: str
    endpoint_id: str
    correlation_id: str
    signature_valid: Optional[bool]
    occurred_at: datetime

