from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.auth.authentication.infrastructure.adapters.auth_user_orm_model import AuthUser
from src.auth.authorization.infrastructure.adapters.rbac_orm_models import (
    AuthPermission,
    AuthRole,
    AuthRolePermission,
    AuthUserRole,
)
from src.auth.authorization.infrastructure.adapters.role_permission_mapper import ROLE_PERMISSION_MAP

PASSWORD = "P@ssw0rd123"

ROLE_IDS = {
    "customer": uuid.UUID("11111111-1111-1111-1111-111111111111"),
    "operation": uuid.UUID("22222222-2222-2222-2222-222222222222"),
    "admin": uuid.UUID("33333333-3333-3333-3333-333333333333"),
}

PERMISSION_IDS = {
    "applications:create": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001"),
    "applications:list_own": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002"),
    "applications:list_all": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0003"),
    "applications:update_customer": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0004"),
    "users:manage_operations": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0005"),
    "workflows:manage": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0006"),
}

TEST_USERS = {
    "customer": {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444441"),
        "email": "customer@example.com",
        "role": "customer",
    },
    "operation": {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444442"),
        "email": "operation@example.com",
        "role": "operation",
    },
    "admin": {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444443"),
        "email": "admin@example.com",
        "role": "admin",
    },
    "inactive_customer": {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "email": "inactive@example.com",
        "role": "customer",
    },
}


def seed_auth_data(session: Session, *, password_hasher: Any) -> None:
    now = datetime.now(timezone.utc)

    for role_code, role_id in ROLE_IDS.items():
        session.add(AuthRole(id=role_id, code=role_code, description=f"{role_code} role"))

    for permission_code, permission_id in PERMISSION_IDS.items():
        session.add(
            AuthPermission(
                id=permission_id,
                code=permission_code,
                description=f"{permission_code} permission",
            )
        )

    for role_code, permission_codes in ROLE_PERMISSION_MAP.items():
        for permission_code in permission_codes:
            session.add(
                AuthRolePermission(
                    role_id=ROLE_IDS[role_code],
                    permission_id=PERMISSION_IDS[permission_code],
                )
            )

    password_hash = password_hasher.hash_password(PASSWORD)
    for user_key, user in TEST_USERS.items():
        is_active = user_key != "inactive_customer"
        session.add(
            AuthUser(
                id=user["id"],
                email=user["email"],
                password_hash=password_hash,
                is_active=is_active,
                created_at=now,
                updated_at=now,
                last_login_at=None,
            )
        )
        session.add(
            AuthUserRole(
                user_id=user["id"],
                role_id=ROLE_IDS[user["role"]],
            )
        )

    session.commit()
