from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    def verify(self, plain_password: str, password_hash: str) -> bool:
        ...

