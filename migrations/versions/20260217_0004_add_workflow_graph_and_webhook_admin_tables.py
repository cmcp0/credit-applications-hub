"""add workflow graph and webhook admin tables

Revision ID: 20260217_0004
Revises: 20260217_0003
Create Date: 2026-02-17 16:10:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260217_0004"
down_revision = "20260217_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE workflows
          ADD COLUMN IF NOT EXISTS graph_revision INT NOT NULL DEFAULT 0;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS operations (
          id UUID PRIMARY KEY,
          workflow_id UUID NOT NULL REFERENCES workflows(id),
          name TEXT NOT NULL,
          sort_order INT NOT NULL,
          active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_operations_workflow_sort_order ON operations(workflow_id, sort_order);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_operations_workflow_id ON operations(workflow_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sub_operations (
          id UUID PRIMARY KEY,
          operation_id UUID NOT NULL REFERENCES operations(id),
          sort_order INT NOT NULL,
          execution_type TEXT NOT NULL,
          target_ref TEXT NOT NULL,
          input_template JSONB NOT NULL DEFAULT '{}'::jsonb,
          output_alias TEXT NULL,
          active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_sub_operations_operation_sort_order ON sub_operations(operation_id, sort_order);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sub_operations_operation_id ON sub_operations(operation_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sub_operation_triggers (
          id UUID PRIMARY KEY,
          sub_operation_id UUID NOT NULL REFERENCES sub_operations(id),
          trigger_type TEXT NOT NULL,
          trigger_name TEXT NOT NULL,
          payload_template JSONB NOT NULL DEFAULT '{}'::jsonb,
          condition_expr TEXT NULL,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sub_operation_triggers_sub_operation_id ON sub_operation_triggers(sub_operation_id);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_endpoints (
          id UUID PRIMARY KEY,
          workflow_id UUID NOT NULL REFERENCES workflows(id),
          country TEXT NOT NULL,
          provider_code TEXT NOT NULL,
          direction TEXT NOT NULL,
          event_type TEXT NOT NULL,
          method TEXT NOT NULL,
          url TEXT NOT NULL,
          secret_ref TEXT NOT NULL,
          timeout_ms INT NOT NULL DEFAULT 5000,
          active BOOLEAN NOT NULL DEFAULT TRUE,
          created_by UUID NOT NULL REFERENCES auth_users(id),
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_webhook_endpoints_workflow_id ON webhook_endpoints(workflow_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_events (
          id UUID PRIMARY KEY,
          endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id),
          workflow_id UUID NOT NULL REFERENCES workflows(id),
          application_id UUID NULL REFERENCES applications(id),
          provider_code TEXT NOT NULL,
          direction TEXT NOT NULL,
          event_type TEXT NOT NULL,
          payload JSONB NOT NULL DEFAULT '{}'::jsonb,
          payload_hash TEXT NOT NULL,
          signature_valid BOOLEAN NULL,
          external_event_id TEXT NULL,
          correlation_id UUID NOT NULL,
          delivery_status TEXT NOT NULL,
          occurred_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_webhook_events_workflow_id ON webhook_events(workflow_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_webhook_events_correlation_id ON webhook_events(correlation_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_delivery_attempts (
          id UUID PRIMARY KEY,
          webhook_event_id UUID NOT NULL REFERENCES webhook_events(id),
          attempt_no INT NOT NULL,
          delivery_status TEXT NOT NULL,
          response_code INT NULL,
          response_body TEXT NULL,
          latency_ms INT NULL,
          error_code TEXT NULL,
          error_message TEXT NULL,
          next_retry_at TIMESTAMPTZ NULL,
          created_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_webhook_delivery_attempts_event_attempt ON webhook_delivery_attempts(webhook_event_id, attempt_no);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_webhook_delivery_attempts_event_id ON webhook_delivery_attempts(webhook_event_id);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_replay_commands (
          command_id UUID PRIMARY KEY,
          workflow_id UUID NOT NULL REFERENCES workflows(id),
          webhook_event_id UUID NOT NULL REFERENCES webhook_events(id),
          requested_by UUID NOT NULL REFERENCES auth_users(id),
          reason TEXT NOT NULL,
          requested_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_webhook_replay_commands_workflow_actor_time ON webhook_replay_commands(workflow_id, requested_by, requested_at DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_webhook_replay_commands_event_time ON webhook_replay_commands(webhook_event_id, requested_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_replay_commands;")
    op.execute("DROP TABLE IF EXISTS webhook_delivery_attempts;")
    op.execute("DROP TABLE IF EXISTS webhook_events;")
    op.execute("DROP TABLE IF EXISTS webhook_endpoints;")
    op.execute("DROP TABLE IF EXISTS sub_operation_triggers;")
    op.execute("DROP TABLE IF EXISTS sub_operations;")
    op.execute("DROP TABLE IF EXISTS operations;")
    op.execute("ALTER TABLE workflows DROP COLUMN IF EXISTS graph_revision;")
