from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from apps.backend.api.applications.command_consumer import AuthorizedStatusActor
from src.applications.shared.domain.errors import (
    ApplicationPermissionDeniedError,
    ValidationError,
)
from src.applications.shared.domain.value_objects import FieldValidationError
from src.auth.authentication.infrastructure.adapters.auth_user_orm_model import AuthUser
from src.auth.authorization.infrastructure.adapters.permission_policy_repository import (
    PermissionPolicyRepository,
)
from src.auth.authorization.infrastructure.services.permission_resolution_service import (
    PermissionResolutionService,
)

REQUIRED_STATUS_UPDATE_PERMISSION = "applications:update_customer"


class StatusUpdateActorAuthorizer:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._permission_resolution_service = PermissionResolutionService(PermissionPolicyRepository(session))

    def authorize(self, *, actor_user_id: str, requested_actor_role: str) -> AuthorizedStatusActor:
        actor_uuid = self._parse_actor_user_id(actor_user_id)
        user = self._session.get(AuthUser, actor_uuid)
        if user is None or not user.is_active:
            raise ApplicationPermissionDeniedError()

        roles = self._permission_resolution_service.roles_for_user(actor_user_id)
        permissions = self._permission_resolution_service.permissions_for_user(actor_user_id)
        if REQUIRED_STATUS_UPDATE_PERMISSION not in permissions:
            raise ApplicationPermissionDeniedError()

        resolved_role = _resolve_actor_role(roles, requested_actor_role)
        return AuthorizedStatusActor(
            actor_user_id=str(user.id),
            actor_role=resolved_role,
        )

    def _parse_actor_user_id(self, actor_user_id: str) -> uuid.UUID:
        try:
            return uuid.UUID(actor_user_id)
        except ValueError as exc:
            raise ValidationError(
                [
                    FieldValidationError(
                        field="actor_user_id",
                        code="INVALID_FORMAT",
                        message="actor_user_id must be a valid UUID",
                    )
                ]
            ) from exc


def _resolve_actor_role(roles: Sequence[str], requested_actor_role: str) -> str:
    normalized_roles = tuple(sorted({role.strip().lower() for role in roles if role and role.strip()}))
    normalized_requested = requested_actor_role.strip().lower()

    if normalized_requested and normalized_requested in normalized_roles:
        return normalized_requested
    if "operation" in normalized_roles:
        return "operation"
    if normalized_roles:
        return normalized_roles[0]

    raise ApplicationPermissionDeniedError()
