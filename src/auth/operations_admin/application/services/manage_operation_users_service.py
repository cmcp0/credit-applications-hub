from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.auth.operations_admin.domain.entities import OperationUserSummary
from src.auth.operations_admin.domain.ports.operation_user_repository import OperationUserRepository


@dataclass(frozen=True)
class OperationUserListPage:
    items: tuple[OperationUserSummary, ...]
    page: int
    page_size: int
    total: int


class ManageOperationUsersService:
    def __init__(self, repository: OperationUserRepository) -> None:
        self._repository = repository

    def list_operation_users(
        self,
        *,
        active: Optional[bool],
        page: int,
        page_size: int,
    ) -> OperationUserListPage:
        items, total = self._repository.list_operation_users(
            active=active,
            page=page,
            page_size=page_size,
        )
        return OperationUserListPage(items=items, page=page, page_size=page_size, total=total)

    def assign_operation_role(self, *, user_id: uuid.UUID) -> datetime:
        assigned_at = datetime.now(timezone.utc)
        return self._repository.assign_operation_role(user_id=user_id, assigned_at=assigned_at)

    def set_operation_access(self, *, user_id: uuid.UUID, enabled: bool) -> datetime:
        updated_at = datetime.now(timezone.utc)
        return self._repository.set_operation_access(
            user_id=user_id,
            enabled=enabled,
            updated_at=updated_at,
        )

