"""add workflow versioning columns

Revision ID: 20260217_0003
Revises: 20260216_0002
Create Date: 2026-02-17 13:00:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260217_0003"
down_revision = "20260216_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE workflows
          ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;
        """
    )
    op.execute(
        """
        ALTER TABLE workflows
          ADD COLUMN IF NOT EXISTS version_status TEXT NOT NULL DEFAULT 'PUBLISHED';
        """
    )
    op.execute(
        """
        ALTER TABLE workflows
          ADD COLUMN IF NOT EXISTS published_by UUID NULL REFERENCES auth_users(id);
        """
    )
    op.execute(
        """
        ALTER TABLE workflows
          ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ NULL;
        """
    )
    op.execute("DROP INDEX IF EXISTS ux_workflows_country;")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_workflows_country_version
        ON workflows(country, version);
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_workflows_country_active_published
        ON workflows(country)
        WHERE active = TRUE AND version_status = 'PUBLISHED';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_workflows_country_active_published;")
    op.execute("DROP INDEX IF EXISTS ux_workflows_country_version;")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_workflows_country ON workflows(country);")
    op.execute("ALTER TABLE workflows DROP COLUMN IF EXISTS published_at;")
    op.execute("ALTER TABLE workflows DROP COLUMN IF EXISTS published_by;")
    op.execute("ALTER TABLE workflows DROP COLUMN IF EXISTS version_status;")
    op.execute("ALTER TABLE workflows DROP COLUMN IF EXISTS version;")

