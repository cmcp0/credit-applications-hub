from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    token_type: str
    expires_in: int

