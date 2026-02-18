from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Protocol

from src.auth.operations_admin.domain.entities import OperationUserSummary


class OperationUserRepository(Protocol):
    def list_operation_users(
        self,
        *,
        active: Optional[bool],
        page: int,
        page_size: int,
    ) -> tuple[tuple[OperationUserSummary, ...], int]:
        ...

    def assign_operation_role(self, *, user_id: uuid.UUID, assigned_at: datetime) -> datetime:
        ...

    def set_operation_access(self, *, user_id: uuid.UUID, enabled: bool, updated_at: datetime) -> datetime:
        ...

