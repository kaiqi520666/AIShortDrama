"""add generation task constraints and indexes

Revision ID: z1a2b3c4d5e6f
Revises: y8d0f2b4c6e8
"""

from alembic import op
from sqlalchemy import text


revision = "z1a2b3c4d5e6f"
down_revision = "y8d0f2b4c6e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(text("UPDATE generation_tasks SET credit_status = 'none' WHERE credit_status IS NULL OR credit_status = ''"))
    op.execute(text("UPDATE generation_tasks SET status = 'queued' WHERE status IS NULL OR status = ''"))
    op.execute(text("UPDATE generation_tasks SET progress = 0 WHERE progress IS NULL"))
    op.create_check_constraint(
        "ck_generation_tasks_status",
        "generation_tasks",
        "status IN ('queued', 'running', 'succeeded', 'failed', 'timeout', 'cancelled', 'needs_review')",
    )
    op.create_check_constraint(
        "ck_generation_tasks_credit_status",
        "generation_tasks",
        "credit_status IN ('none', 'frozen', 'consumed', 'refunded')",
    )
    op.create_check_constraint(
        "ck_generation_tasks_progress",
        "generation_tasks",
        "progress BETWEEN 0 AND 100",
    )
    op.create_index(
        "ix_generation_tasks_workspace_status_created_at",
        "generation_tasks",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_generation_tasks_user_status_created_at",
        "generation_tasks",
        ["user_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_generation_tasks_user_status_created_at", table_name="generation_tasks")
    op.drop_index("ix_generation_tasks_workspace_status_created_at", table_name="generation_tasks")
    op.drop_constraint("ck_generation_tasks_progress", "generation_tasks", type_="check")
    op.drop_constraint("ck_generation_tasks_credit_status", "generation_tasks", type_="check")
    op.drop_constraint("ck_generation_tasks_status", "generation_tasks", type_="check")
