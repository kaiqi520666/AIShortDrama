"""add users workspaces assets

Revision ID: 9f1d62a4c8b3
Revises: 6503ea6036f8
Create Date: 2026-07-22
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9f1d62a4c8b3"
down_revision: Union[str, Sequence[str], None] = "6503ea6036f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LOCAL_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
EMPTY_CANVAS = """{
  "schema_version": 1,
  "nodes": [],
  "edges": [],
  "groups": [],
  "sequence": 1,
  "group_sequence": 1,
  "viewport": {"x": 0, "y": 0, "zoom": 1}
}"""


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("canvas", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_user_updated_at", "workspaces", ["user_id", "updated_at"])
    op.execute(
        sa.text("INSERT INTO users (id, display_name) VALUES (:id, :name)").bindparams(
            id=LOCAL_USER_ID, name="本地用户"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO workspaces (id, user_id, name, canvas) "
            "VALUES (:id, :user_id, :name, CAST(:canvas AS jsonb))"
        ).bindparams(
            id=DEFAULT_WORKSPACE_ID,
            user_id=LOCAL_USER_ID,
            name="默认工作台",
            canvas=EMPTY_CANVAS,
        )
    )
    op.add_column("generation_tasks", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("generation_tasks", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE generation_tasks SET user_id = :user_id, workspace_id = :workspace_id"
        ).bindparams(user_id=LOCAL_USER_ID, workspace_id=DEFAULT_WORKSPACE_ID)
    )
    op.alter_column("generation_tasks", "user_id", nullable=False)
    op.alter_column("generation_tasks", "workspace_id", nullable=False)
    op.create_foreign_key(
        "fk_generation_tasks_user_id_users", "generation_tasks", "users", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_generation_tasks_workspace_id_workspaces",
        "generation_tasks",
        "workspaces",
        ["workspace_id"],
        ["id"],
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("generation_task_id", sa.Uuid(), nullable=True),
        sa.Column("node_id", sa.String(64), nullable=True),
        sa.Column("media_type", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("asset_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generation_task_id"], ["generation_tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_user_media_created_at", "assets", ["user_id", "media_type", "created_at"])
    op.create_index("ix_assets_workspace_id", "assets", ["workspace_id"])
    op.create_index("ix_assets_generation_task_id", "assets", ["generation_task_id"])


def downgrade() -> None:
    op.drop_index("ix_assets_generation_task_id", table_name="assets")
    op.drop_index("ix_assets_workspace_id", table_name="assets")
    op.drop_index("ix_assets_user_media_created_at", table_name="assets")
    op.drop_table("assets")
    op.drop_constraint("fk_generation_tasks_workspace_id_workspaces", "generation_tasks", type_="foreignkey")
    op.drop_constraint("fk_generation_tasks_user_id_users", "generation_tasks", type_="foreignkey")
    op.drop_column("generation_tasks", "workspace_id")
    op.drop_column("generation_tasks", "user_id")
    op.drop_index("ix_workspaces_user_updated_at", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_table("users")
