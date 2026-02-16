from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Protocol


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_in: int


class TokenIssuer(Protocol):
    def issue_access_token(
        self,
        *,
        subject: str,
        roles: Sequence[str],
        permissions: Sequence[str],
    ) -> IssuedToken:
        ...

