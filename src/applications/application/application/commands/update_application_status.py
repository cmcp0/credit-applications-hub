from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class UpdateApplicationStatusCommand:
    command_id: str
    application_id: str
    target_status_code: str
    actor_user_id: str
    actor_role: str
    reason_code: Optional[str]
    expected_version: int
    request_id: str
    correlation_id: str
    requested_at: datetime
