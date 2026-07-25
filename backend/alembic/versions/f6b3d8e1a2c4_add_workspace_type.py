"""add workspace type

Revision ID: f6b3d8e1a2c4
Revises: d4f7a9c2e1b3
Create Date: 2026-07-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6b3d8e1a2c4"
down_revision: Union[str, Sequence[str], None] = "d4f7a9c2e1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "workspace_type",
            sa.String(length=16),
            server_default="general",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_workspaces_workspace_type",
        "workspaces",
        "workspace_type IN ('general', 'ecommerce', 'drama')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_workspaces_workspace_type", "workspaces", type_="check")
    op.drop_column("workspaces", "workspace_type")
