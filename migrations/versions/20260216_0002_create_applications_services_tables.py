"""create applications services tables

Revision ID: 20260216_0002
Revises: 20260216_0001
Create Date: 2026-02-16 02:30:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260216_0002"
down_revision = "20260216_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workflows (
          id UUID PRIMARY KEY,
          country TEXT NOT NULL,
          active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_workflows_country ON workflows(country);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS statuses (
          id UUID PRIMARY KEY,
          workflow_id UUID NOT NULL REFERENCES workflows(id),
          code TEXT NOT NULL,
          label TEXT NOT NULL,
          is_terminal BOOLEAN NOT NULL DEFAULT FALSE,
          is_initial BOOLEAN NOT NULL DEFAULT FALSE,
          sort_order INT NOT NULL DEFAULT 0
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_statuses_workflow_code ON statuses(workflow_id, code);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS status_transitions (
          id UUID PRIMARY KEY,
          from_status_id UUID NOT NULL REFERENCES statuses(id),
          to_status_id UUID NOT NULL REFERENCES statuses(id)
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_status_transitions_from_to ON status_transitions(from_status_id, to_status_id);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES auth_users(id),
          country TEXT NOT NULL,
          full_name TEXT NOT NULL,
          identity_document TEXT NOT NULL,
          requested_amount NUMERIC(14,2) NOT NULL,
          monthly_income NUMERIC(14,2) NOT NULL,
          application_date DATE NOT NULL,
          status_code TEXT NOT NULL,
          version INT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_user_id ON applications(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_country ON applications(country);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_status_code ON applications(status_code);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS application_status_history (
          id UUID PRIMARY KEY,
          application_id UUID NOT NULL REFERENCES applications(id),
          from_status_code TEXT NOT NULL,
          to_status_code TEXT NOT NULL,
          application_version INT NOT NULL,
          reason_code TEXT NULL,
          actor_user_id UUID NULL,
          actor_role TEXT NULL,
          command_id UUID NULL,
          correlation_id UUID NOT NULL,
          changed_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_application_status_history_application_version ON application_status_history(application_id, application_version);"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_application_status_history_command_id ON application_status_history(command_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_application_status_history_application_changed ON application_status_history(application_id, changed_at DESC);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox_events (
          id UUID PRIMARY KEY,
          aggregate_type TEXT NOT NULL,
          aggregate_id UUID NOT NULL,
          exchange_name TEXT NOT NULL,
          routing_key TEXT NOT NULL,
          event_name TEXT NOT NULL,
          schema_version TEXT NOT NULL,
          correlation_id UUID NOT NULL,
          payload JSONB NOT NULL,
          publish_status TEXT NOT NULL,
          attempts INT NOT NULL DEFAULT 0,
          last_error TEXT NULL,
          next_attempt_at TIMESTAMPTZ NOT NULL,
          locked_at TIMESTAMPTZ NULL,
          locked_by TEXT NULL,
          occurred_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL,
          published_at TIMESTAMPTZ NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_outbox_events_aggregate_id ON outbox_events(aggregate_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_outbox_events_correlation_id ON outbox_events(correlation_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_outbox_events_status_created ON outbox_events(publish_status, created_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_outbox_events_status_next_attempt ON outbox_events(publish_status, next_attempt_at);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_outbox_events_locked_at ON outbox_events(locked_at);")

    op.execute(
        """
        INSERT INTO workflows (id, country, active, created_at, updated_at)
        VALUES
          ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0001', 'MX', TRUE, NOW(), NOW()),
          ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002', 'BR', TRUE, NOW(), NOW()),
          ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003', 'CO', TRUE, NOW(), NOW()),
          ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0004', 'CL', TRUE, NOW(), NOW()),
          ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0005', 'PE', TRUE, NOW(), NOW())
        ON CONFLICT (country) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO statuses (id, workflow_id, code, label, is_terminal, is_initial, sort_order)
        VALUES
          ('cccccccc-cccc-cccc-cccc-cccccccc1001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0001', 'PENDING_REVIEW', 'Pending review', FALSE, TRUE, 1),
          ('cccccccc-cccc-cccc-cccc-cccccccc1002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0001', 'APPROVED', 'Approved', TRUE, FALSE, 2),
          ('cccccccc-cccc-cccc-cccc-cccccccc1003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0001', 'REJECTED', 'Rejected', TRUE, FALSE, 3),

          ('cccccccc-cccc-cccc-cccc-cccccccc2001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002', 'PENDING_REVIEW', 'Pending review', FALSE, TRUE, 1),
          ('cccccccc-cccc-cccc-cccc-cccccccc2002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002', 'APPROVED', 'Approved', TRUE, FALSE, 2),
          ('cccccccc-cccc-cccc-cccc-cccccccc2003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002', 'REJECTED', 'Rejected', TRUE, FALSE, 3),

          ('cccccccc-cccc-cccc-cccc-cccccccc3001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003', 'PENDING_REVIEW', 'Pending review', FALSE, TRUE, 1),
          ('cccccccc-cccc-cccc-cccc-cccccccc3002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003', 'APPROVED', 'Approved', TRUE, FALSE, 2),
          ('cccccccc-cccc-cccc-cccc-cccccccc3003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0003', 'REJECTED', 'Rejected', TRUE, FALSE, 3),

          ('cccccccc-cccc-cccc-cccc-cccccccc4001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0004', 'PENDING_REVIEW', 'Pending review', FALSE, TRUE, 1),
          ('cccccccc-cccc-cccc-cccc-cccccccc4002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0004', 'APPROVED', 'Approved', TRUE, FALSE, 2),
          ('cccccccc-cccc-cccc-cccc-cccccccc4003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0004', 'REJECTED', 'Rejected', TRUE, FALSE, 3),

          ('cccccccc-cccc-cccc-cccc-cccccccc5001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0005', 'PENDING_REVIEW', 'Pending review', FALSE, TRUE, 1),
          ('cccccccc-cccc-cccc-cccc-cccccccc5002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0005', 'APPROVED', 'Approved', TRUE, FALSE, 2),
          ('cccccccc-cccc-cccc-cccc-cccccccc5003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0005', 'REJECTED', 'Rejected', TRUE, FALSE, 3)
        ON CONFLICT (id) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO status_transitions (id, from_status_id, to_status_id)
        VALUES
          ('dddddddd-dddd-dddd-dddd-dddddddd1001', 'cccccccc-cccc-cccc-cccc-cccccccc1001', 'cccccccc-cccc-cccc-cccc-cccccccc1002'),
          ('dddddddd-dddd-dddd-dddd-dddddddd1002', 'cccccccc-cccc-cccc-cccc-cccccccc1001', 'cccccccc-cccc-cccc-cccc-cccccccc1003'),

          ('dddddddd-dddd-dddd-dddd-dddddddd2001', 'cccccccc-cccc-cccc-cccc-cccccccc2001', 'cccccccc-cccc-cccc-cccc-cccccccc2002'),
          ('dddddddd-dddd-dddd-dddd-dddddddd2002', 'cccccccc-cccc-cccc-cccc-cccccccc2001', 'cccccccc-cccc-cccc-cccc-cccccccc2003'),

          ('dddddddd-dddd-dddd-dddd-dddddddd3001', 'cccccccc-cccc-cccc-cccc-cccccccc3001', 'cccccccc-cccc-cccc-cccc-cccccccc3002'),
          ('dddddddd-dddd-dddd-dddd-dddddddd3002', 'cccccccc-cccc-cccc-cccc-cccccccc3001', 'cccccccc-cccc-cccc-cccc-cccccccc3003'),

          ('dddddddd-dddd-dddd-dddd-dddddddd4001', 'cccccccc-cccc-cccc-cccc-cccccccc4001', 'cccccccc-cccc-cccc-cccc-cccccccc4002'),
          ('dddddddd-dddd-dddd-dddd-dddddddd4002', 'cccccccc-cccc-cccc-cccc-cccccccc4001', 'cccccccc-cccc-cccc-cccc-cccccccc4003'),

          ('dddddddd-dddd-dddd-dddd-dddddddd5001', 'cccccccc-cccc-cccc-cccc-cccccccc5001', 'cccccccc-cccc-cccc-cccc-cccccccc5002'),
          ('dddddddd-dddd-dddd-dddd-dddddddd5002', 'cccccccc-cccc-cccc-cccc-cccccccc5001', 'cccccccc-cccc-cccc-cccc-cccccccc5003')
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS outbox_events;")
    op.execute("DROP TABLE IF EXISTS application_status_history;")
    op.execute("DROP TABLE IF EXISTS applications;")
    op.execute("DROP TABLE IF EXISTS status_transitions;")
    op.execute("DROP TABLE IF EXISTS statuses;")
    op.execute("DROP TABLE IF EXISTS workflows;")
