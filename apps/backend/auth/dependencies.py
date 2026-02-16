from __future__ import annotations

from collections.abc import Sequence
from typing import Optional
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.auth.jwt_codec import JwtCodec, JwtCodecConfig, JwtTokenIssuer
from apps.backend.database import create_session_factory
from apps.backend.security.password_hasher import Argon2PasswordHasher
from apps.backend.settings import Settings
from src.auth.authentication.application.services.login_service import LoginService
from src.auth.authentication.domain.ports.token_issuer import TokenIssuer
from src.auth.authentication.infrastructure.adapters.auth_user_credentials_repository import (
    AuthUserCredentialsRepository,
)
from src.auth.authorization.application.services.authorize_request_service import (
    AuthorizeRequestService,
)
from src.auth.authorization.domain.entities import AuthenticatedPrincipal
from src.auth.authorization.domain.ports.permission_policy_reader import PermissionPolicyReader
from src.auth.authorization.infrastructure.adapters.permission_policy_repository import (
    PermissionPolicyRepository,
)
from src.auth.authorization.infrastructure.services.permission_resolution_service import (
    PermissionResolutionService,
)
from src.auth.shared.domain.errors import AuthHeaderMissingError, PermissionDeniedError, TokenInvalidError


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session_factory(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> sessionmaker[Session]:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.session_factory = create_session_factory(settings.database_url)
    return request.app.state.session_factory


def get_db_session(
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_password_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


def get_jwt_codec(settings: Annotated[Settings, Depends(get_settings)]) -> JwtCodec:
    config = JwtCodecConfig(
        secret=settings.auth_jwt_secret,
        issuer=settings.auth_jwt_issuer,
        audience=settings.auth_jwt_audience,
        ttl_seconds=settings.auth_jwt_ttl_seconds,
    )
    return JwtCodec(config)


def get_token_issuer(codec: Annotated[JwtCodec, Depends(get_jwt_codec)]) -> TokenIssuer:
    return JwtTokenIssuer(codec)


def get_user_credentials_reader(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthUserCredentialsRepository:
    return AuthUserCredentialsRepository(db_session)


def get_permission_policy_reader(
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PermissionPolicyReader:
    return PermissionPolicyRepository(db_session)


def get_permission_resolution_service(
    policy_reader: Annotated[PermissionPolicyReader, Depends(get_permission_policy_reader)],
) -> PermissionResolutionService:
    return PermissionResolutionService(policy_reader)


def get_login_service(
    credentials_reader: Annotated[AuthUserCredentialsRepository, Depends(get_user_credentials_reader)],
    password_hasher: Annotated[Argon2PasswordHasher, Depends(get_password_hasher)],
    token_issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
) -> LoginService:
    return LoginService(
        credentials_reader=credentials_reader,
        password_hasher=password_hasher,
        token_issuer=token_issuer,
    )


def get_authorize_request_service() -> AuthorizeRequestService:
    return AuthorizeRequestService()


def get_current_principal(
    jwt_codec: Annotated[JwtCodec, Depends(get_jwt_codec)],
    authorize_request_service: Annotated[
        AuthorizeRequestService,
        Depends(get_authorize_request_service),
    ],
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
) -> AuthenticatedPrincipal:
    token = _extract_bearer_token(authorization)
    claims = jwt_codec.decode_token(token)
    return authorize_request_service.principal_from_claims(claims)


def require_permissions(*required_permissions: str):
    def _require(
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
        authorize_service: Annotated[
            AuthorizeRequestService,
            Depends(get_authorize_request_service),
        ],
    ) -> AuthenticatedPrincipal:
        authorize_service.require_permissions(principal, required_permissions)
        return principal

    return _require


def require_any_permissions(*required_permissions: str):
    def _require(
        principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    ) -> AuthenticatedPrincipal:
        if not any(permission in principal.permissions for permission in required_permissions):
            raise PermissionDeniedError()
        return principal

    return _require


def owner_scope_for_customer(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    authorize_service: Annotated[AuthorizeRequestService, Depends(get_authorize_request_service)],
) -> Optional[str]:
    return authorize_service.owner_scope(principal)


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise AuthHeaderMissingError()

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise TokenInvalidError("Authorization header must use Bearer token")

    return parts[1].strip()
