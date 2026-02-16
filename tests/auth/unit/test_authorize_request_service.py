from __future__ import annotations

import pytest

from src.auth.authorization.application.services.authorize_request_service import (
    AuthorizeRequestService,
)
from src.auth.shared.domain.errors import PermissionDeniedError, TokenInvalidError


@pytest.fixture
def service() -> AuthorizeRequestService:
    return AuthorizeRequestService()


def test_principal_from_claims_maps_claims(service: AuthorizeRequestService) -> None:
    principal = service.principal_from_claims(
        {
            "sub": "user-1",
            "roles": ["customer"],
            "permissions": ["applications:list_own"],
            "iat": 1,
            "exp": 2,
            "iss": "issuer",
            "aud": "audience",
        }
    )

    assert principal.user_id == "user-1"
    assert principal.roles == ("customer",)
    assert principal.permissions == {"applications:list_own"}


def test_principal_from_claims_rejects_missing_claims(service: AuthorizeRequestService) -> None:
    with pytest.raises(TokenInvalidError):
        service.principal_from_claims({"sub": "user-1"})


def test_require_permissions_denies_without_permission(service: AuthorizeRequestService) -> None:
    principal = service.principal_from_claims(
        {
            "sub": "user-1",
            "roles": ["customer"],
            "permissions": ["applications:list_own"],
            "iat": 1,
            "exp": 2,
            "iss": "issuer",
            "aud": "audience",
        }
    )

    with pytest.raises(PermissionDeniedError):
        service.require_permissions(principal, ["applications:list_all"])

