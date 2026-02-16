from __future__ import annotations

from typing import Protocol, Sequence


class PermissionPolicyReader(Protocol):
    def get_roles_for_user(self, user_id: str) -> tuple[str, ...]:
        ...

    def get_permissions_for_roles(self, roles: Sequence[str]) -> tuple[str, ...]:
        ...

    def get_permissions_for_user(self, user_id: str) -> tuple[str, ...]:
        ...

