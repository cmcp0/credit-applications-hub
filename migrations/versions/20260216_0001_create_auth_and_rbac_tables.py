"""create auth and rbac tables

Revision ID: 20260216_0001
Revises:
Create Date: 2026-02-16 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260216_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_users (
          id UUID PRIMARY KEY,
          email CITEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL,
          last_login_at TIMESTAMPTZ NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_roles (
          id UUID PRIMARY KEY,
          code TEXT UNIQUE NOT NULL,
          description TEXT NOT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_permissions (
          id UUID PRIMARY KEY,
          code TEXT UNIQUE NOT NULL,
          description TEXT NOT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_user_roles (
          user_id UUID NOT NULL REFERENCES auth_users(id),
          role_id UUID NOT NULL REFERENCES auth_roles(id),
          PRIMARY KEY (user_id, role_id)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_role_permissions (
          role_id UUID NOT NULL REFERENCES auth_roles(id),
          permission_id UUID NOT NULL REFERENCES auth_permissions(id),
          PRIMARY KEY (role_id, permission_id)
        );
        """
    )

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_auth_users_email ON auth_users(email);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_auth_roles_code ON auth_roles(code);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_auth_permissions_code ON auth_permissions(code);")

    op.execute(
        """
        INSERT INTO auth_roles (id, code, description)
        VALUES
          ('11111111-1111-1111-1111-111111111111', 'customer', 'Customer user role'),
          ('22222222-2222-2222-2222-222222222222', 'operation', 'Operation user role'),
          ('33333333-3333-3333-3333-333333333333', 'admin', 'Admin role')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO auth_permissions (id, code, description)
        VALUES
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001', 'applications:create', 'Create applications'),
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002', 'applications:list_own', 'List own applications'),
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0003', 'applications:list_all', 'List all applications'),
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0004', 'applications:update_customer', 'Update customer application status'),
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0005', 'users:manage_operations', 'Manage operation users'),
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0006', 'workflows:manage', 'Manage workflows')
        ON CONFLICT (code) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO auth_role_permissions (role_id, permission_id)
        VALUES
          ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001'),
          ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002'),
          ('22222222-2222-2222-2222-222222222222', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0003'),
          ('22222222-2222-2222-2222-222222222222', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0004'),
          ('33333333-3333-3333-3333-333333333333', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0003'),
          ('33333333-3333-3333-3333-333333333333', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0005'),
          ('33333333-3333-3333-3333-333333333333', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0006')
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_role_permissions;")
    op.execute("DROP TABLE IF EXISTS auth_user_roles;")
    op.execute("DROP TABLE IF EXISTS auth_permissions;")
    op.execute("DROP TABLE IF EXISTS auth_roles;")
    op.execute("DROP TABLE IF EXISTS auth_users;")
