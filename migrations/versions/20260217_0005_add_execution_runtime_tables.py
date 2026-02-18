"""add execution runtime tables

Revision ID: 20260217_0005
Revises: 20260217_0004
Create Date: 2026-02-17 19:45:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260217_0005"
down_revision = "20260217_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_jobs (
          id UUID PRIMARY KEY,
          workflow_id UUID NOT NULL REFERENCES workflows(id),
          workflow_revision INT NOT NULL,
          application_id UUID NULL REFERENCES applications(id),
          operation_id UUID NULL REFERENCES operations(id),
          sub_operation_id UUID NULL REFERENCES sub_operations(id),
          status TEXT NOT NULL,
          idempotency_key TEXT NOT NULL,
          payload_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
          attempts INT NOT NULL DEFAULT 0,
          max_attempts INT NOT NULL DEFAULT 5,
          available_at TIMESTAMPTZ NOT NULL,
          locked_at TIMESTAMPTZ NULL,
          completed_at TIMESTAMPTZ NULL,
          last_error_code TEXT NULL,
          last_error_message TEXT NULL,
          correlation_id UUID NOT NULL,
          created_at TIMESTAMPTZ NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_worker_jobs_idempotency_key ON worker_jobs(idempotency_key);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_jobs_workflow_id ON worker_jobs(workflow_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_jobs_status ON worker_jobs(status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_jobs_available_at ON worker_jobs(available_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_jobs_correlation_id ON worker_jobs(correlation_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_jobs_application_id ON worker_jobs(application_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_worker_jobs_operation_id ON worker_jobs(operation_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_worker_jobs_sub_operation_id ON worker_jobs(sub_operation_id);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS event_consumptions (
          id UUID PRIMARY KEY,
          consumer_name TEXT NOT NULL,
          queue_name TEXT NOT NULL,
          message_id TEXT NOT NULL,
          correlation_id UUID NULL,
          payload_hash TEXT NULL,
          consumed_at TIMESTAMPTZ NOT NULL
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_event_consumptions_consumer_queue_message ON event_consumptions(consumer_name, queue_name, message_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_event_consumptions_consumer_name ON event_consumptions(consumer_name);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_event_consumptions_queue_name ON event_consumptions(queue_name);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_event_consumptions_correlation_id ON event_consumptions(correlation_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS event_consumptions;")
    op.execute("DROP TABLE IF EXISTS worker_jobs;")

