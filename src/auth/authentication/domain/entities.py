from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredUserCredentials:
    user_id: str
    email: str
    password_hash: str
    is_active: bool
    roles: tuple[str, ...]
    permissions: tuple[str, ...]

