from __future__ import annotations

from collections.abc import Mapping

PERMISSIONS = (
    "applications:create",
    "applications:list_own",
    "applications:list_all",
    "applications:update_customer",
    "users:manage_operations",
    "workflows:manage",
)

ROLE_PERMISSION_MAP: Mapping[str, tuple[str, ...]] = {
    "customer": (
        "applications:create",
        "applications:list_own",
    ),
    "operation": (
        "applications:list_all",
        "applications:update_customer",
    ),
    "admin": (
        "users:manage_operations",
        "workflows:manage",
    ),
}


def permissions_for_roles(roles: tuple[str, ...]) -> tuple[str, ...]:
    resolved: set[str] = set()
    for role in roles:
        resolved.update(ROLE_PERMISSION_MAP.get(role, ()))
    return tuple(sorted(resolved))
