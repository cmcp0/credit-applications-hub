from __future__ import annotations

from src.auth.authentication.application.dto import LoginCommand, LoginResult
from src.auth.authentication.domain.ports.password_hasher import PasswordHasher
from src.auth.authentication.domain.ports.token_issuer import TokenIssuer
from src.auth.authentication.domain.ports.user_credentials_reader import UserCredentialsReader
from src.auth.authentication.domain.value_objects import EmailAddress
from src.auth.shared.domain.errors import InvalidCredentialsError, UserInactiveError


class LoginService:
    def __init__(
        self,
        credentials_reader: UserCredentialsReader,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
    ) -> None:
        self._credentials_reader = credentials_reader
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer

    def login(self, command: LoginCommand) -> LoginResult:
        normalized_email = EmailAddress.normalize(command.email)
        user_credentials = self._credentials_reader.get_by_normalized_email(normalized_email)

        if user_credentials is None:
            raise InvalidCredentialsError()

        if not self._password_hasher.verify(command.password, user_credentials.password_hash):
            raise InvalidCredentialsError()

        if not user_credentials.is_active:
            raise UserInactiveError()

        issued_token = self._token_issuer.issue_access_token(
            subject=user_credentials.user_id,
            roles=user_credentials.roles,
            permissions=user_credentials.permissions,
        )
        self._credentials_reader.mark_login_success(user_credentials.user_id)

        return LoginResult(
            access_token=issued_token.access_token,
            token_type="bearer",
            expires_in=issued_token.expires_in,
        )

