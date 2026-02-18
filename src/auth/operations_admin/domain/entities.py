from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OperationUserSummary:
    user_id: str
    email: str
    is_active: bool
    has_operation_role: bool
    updated_at: datetime

