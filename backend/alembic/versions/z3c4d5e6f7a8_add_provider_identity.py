"""Persist provider submission identity and recovery results.

Revision ID: z3c4d5e6f7a8
Revises: z2b3c4d5e6f7a
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "z3c4d5e6f7a8"
down_revision = "z2b3c4d5e6f7a"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    duplicates = connection.execute(sa.text("""
        SELECT provider, task_type, provider_task_id, array_agg(id::text) AS task_ids
        FROM generation_tasks WHERE provider_task_id IS NOT NULL
        GROUP BY provider, task_type, provider_task_id HAVING count(*) > 1
    """)).all()
    if duplicates:
        raise RuntimeError(f"重复 Provider 任务 ID，需要人工核查：{duplicates}")
    op.add_column("generation_tasks", sa.Column("client_request_id", sa.String(128)))
    op.add_column("generation_tasks", sa.Column("provider_request_id", sa.String(128)))
    op.add_column("generation_tasks", sa.Column("submission_started_at", sa.DateTime(timezone=True)))
    op.add_column("generation_tasks", sa.Column("provider_response", postgresql.JSONB()))
    op.add_column("generation_tasks", sa.Column("worker_lease_token", sa.String(36)))
    op.add_column("generation_tasks", sa.Column("worker_lease_until", sa.DateTime(timezone=True)))
    op.add_column(
        "generation_tasks", sa.Column("recovery_attempts", sa.SmallInteger(), server_default="0")
    )
    connection.execute(sa.text("""
        UPDATE generation_tasks SET client_request_id = id::text,
            submission_started_at = CASE
                WHEN started_at IS NOT NULL OR status <> 'queued'
                THEN COALESCE(started_at, updated_at) ELSE NULL END
    """))
    op.create_index(
        "uq_generation_tasks_provider_client", "generation_tasks",
        ["provider", "client_request_id"], unique=True,
        postgresql_where=sa.text("client_request_id IS NOT NULL"),
    )
    op.create_index(
        "uq_generation_tasks_provider_remote", "generation_tasks",
        ["provider", "task_type", "provider_task_id"], unique=True,
        postgresql_where=sa.text("provider_task_id IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_generation_tasks_provider_remote", table_name="generation_tasks")
    op.drop_index("uq_generation_tasks_provider_client", table_name="generation_tasks")
    for column in (
        "recovery_attempts", "worker_lease_until", "worker_lease_token", "provider_response",
        "submission_started_at", "provider_request_id", "client_request_id",
    ):
        op.drop_column("generation_tasks", column)
