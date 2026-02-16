from __future__ import annotations

from typing import Optional
from typing import Protocol

from src.auth.authentication.domain.entities import StoredUserCredentials


class UserCredentialsReader(Protocol):
    def get_by_normalized_email(self, normalized_email: str) -> Optional[StoredUserCredentials]:
        ...

    def mark_login_success(self, user_id: str) -> None:
        ...
