from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    roles: tuple[str, ...]
    permissions: frozenset[str]

    def has_all_permissions(self, required_permissions: Iterable[str]) -> bool:
        return set(required_permissions).issubset(self.permissions)

    def is_customer(self) -> bool:
        return "customer" in self.roles

