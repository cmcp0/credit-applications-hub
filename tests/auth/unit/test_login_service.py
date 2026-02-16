from __future__ import annotations

from typing import Optional

import pytest

from src.auth.authentication.application.dto import LoginCommand
from src.auth.authentication.application.services.login_service import LoginService
from src.auth.authentication.domain.entities import StoredUserCredentials
from src.auth.authentication.domain.ports.token_issuer import IssuedToken
from src.auth.shared.domain.errors import InvalidCredentialsError, UserInactiveError


class StubCredentialsReader:
    def __init__(self, user: Optional[StoredUserCredentials]) -> None:
        self._user = user
        self.marked_user_id: Optional[str] = None

    def get_by_normalized_email(self, normalized_email: str) -> Optional[StoredUserCredentials]:
        return self._user

    def mark_login_success(self, user_id: str) -> None:
        self.marked_user_id = user_id


class StubPasswordHasher:
    def __init__(self, valid: bool = True) -> None:
        self._valid = valid

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return self._valid


class StubTokenIssuer:
    def issue_access_token(self, *, subject: str, roles: tuple[str, ...], permissions: tuple[str, ...]) -> IssuedToken:
        return IssuedToken(access_token=f"token-for-{subject}", expires_in=3600)


@pytest.fixture
def active_user() -> StoredUserCredentials:
    return StoredUserCredentials(
        user_id="user-1",
        email="user@example.com",
        password_hash="hash",
        is_active=True,
        roles=("customer",),
        permissions=("applications:list_own",),
    )


def test_login_service_returns_token_for_valid_credentials(active_user: StoredUserCredentials) -> None:
    reader = StubCredentialsReader(active_user)
    service = LoginService(reader, StubPasswordHasher(valid=True), StubTokenIssuer())

    result = service.login(LoginCommand(email=" User@Example.com ", password="secret"))

    assert result.token_type == "bearer"
    assert result.access_token == "token-for-user-1"
    assert result.expires_in == 3600
    assert reader.marked_user_id == "user-1"


def test_login_service_rejects_invalid_credentials(active_user: StoredUserCredentials) -> None:
    service = LoginService(StubCredentialsReader(active_user), StubPasswordHasher(valid=False), StubTokenIssuer())

    with pytest.raises(InvalidCredentialsError):
        service.login(LoginCommand(email="user@example.com", password="bad"))


def test_login_service_rejects_inactive_user(active_user: StoredUserCredentials) -> None:
    inactive = StoredUserCredentials(
        user_id=active_user.user_id,
        email=active_user.email,
        password_hash=active_user.password_hash,
        is_active=False,
        roles=active_user.roles,
        permissions=active_user.permissions,
    )
    service = LoginService(StubCredentialsReader(inactive), StubPasswordHasher(valid=True), StubTokenIssuer())

    with pytest.raises(UserInactiveError):
        service.login(LoginCommand(email="user@example.com", password="secret"))
