from __future__ import annotations

from src.auth.authorization.domain.ports.permission_policy_reader import PermissionPolicyReader
from src.auth.authorization.infrastructure.adapters.role_permission_mapper import permissions_for_roles


class PermissionResolutionService:
    def __init__(self, policy_reader: PermissionPolicyReader) -> None:
        self._policy_reader = policy_reader

    def roles_for_user(self, user_id: str) -> tuple[str, ...]:
        return self._policy_reader.get_roles_for_user(user_id)

    def permissions_for_roles(self, roles: tuple[str, ...]) -> tuple[str, ...]:
        resolved_permissions = self._policy_reader.get_permissions_for_roles(roles)
        if resolved_permissions:
            return resolved_permissions
        return permissions_for_roles(roles)

    def permissions_for_user(self, user_id: str) -> tuple[str, ...]:
        permissions = self._policy_reader.get_permissions_for_user(user_id)
        if permissions:
            return permissions
        roles = self.roles_for_user(user_id)
        return permissions_for_roles(roles)

