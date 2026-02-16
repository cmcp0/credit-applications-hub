from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Optional

from src.auth.authorization.domain.entities import AuthenticatedPrincipal
from src.auth.shared.domain.errors import PermissionDeniedError, TokenInvalidError


class AuthorizeRequestService:
    _REQUIRED_CLAIMS = {"sub", "roles", "permissions", "iat", "exp", "iss", "aud"}

    def principal_from_claims(self, claims: Mapping[str, object]) -> AuthenticatedPrincipal:
        if not self._REQUIRED_CLAIMS.issubset(set(claims.keys())):
            raise TokenInvalidError("Missing required token claims")

        subject = claims.get("sub")
        roles = claims.get("roles")
        permissions = claims.get("permissions")

        if not isinstance(subject, str) or not subject:
            raise TokenInvalidError("Invalid subject claim")

        if not isinstance(roles, Sequence) or isinstance(roles, (str, bytes)):
            raise TokenInvalidError("Invalid roles claim")

        if not isinstance(permissions, Sequence) or isinstance(permissions, (str, bytes)):
            raise TokenInvalidError("Invalid permissions claim")

        normalized_roles = tuple(str(role) for role in roles)
        normalized_permissions = frozenset(str(permission) for permission in permissions)

        if not normalized_roles:
            raise TokenInvalidError("No roles in token")

        return AuthenticatedPrincipal(
            user_id=subject,
            roles=normalized_roles,
            permissions=normalized_permissions,
        )

    def require_permissions(
        self,
        principal: AuthenticatedPrincipal,
        required_permissions: Sequence[str],
    ) -> None:
        if not principal.has_all_permissions(required_permissions):
            raise PermissionDeniedError()

    def owner_scope(self, principal: AuthenticatedPrincipal) -> Optional[str]:
        if principal.is_customer():
            return principal.user_id
        return None
