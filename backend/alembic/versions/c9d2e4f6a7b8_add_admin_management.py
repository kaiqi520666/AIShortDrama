"""add admin management

Revision ID: c9d2e4f6a7b8
Revises: b7e3d9a1c5f8
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c9d2e4f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b7e3d9a1c5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=16), server_default="user", nullable=False))
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("before_snapshot", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("after_snapshot", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_admin_created_at", "admin_audit_logs", ["admin_id", "created_at"])
    op.create_index("ix_admin_audit_logs_target_created_at", "admin_audit_logs", ["target_type", "target_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_logs_target_created_at", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_created_at", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
