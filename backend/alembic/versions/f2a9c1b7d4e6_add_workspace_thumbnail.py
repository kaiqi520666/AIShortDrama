"""add workspace thumbnail

Revision ID: f2a9c1b7d4e6
Revises: e8c41d7a2b90
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f2a9c1b7d4e6"
down_revision: Union[str, Sequence[str], None] = "e8c41d7a2b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("thumbnail_url", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE workspaces
        SET thumbnail_url = (
            SELECT node -> 'data' ->> 'asset'
            FROM jsonb_array_elements(COALESCE(canvas -> 'nodes', '[]'::jsonb))
                WITH ORDINALITY AS items(node, position)
            WHERE node ->> 'type' = 'image'
              AND NULLIF(node -> 'data' ->> 'asset', '') IS NOT NULL
            ORDER BY position DESC
            LIMIT 1
        )
        """
    )


def downgrade() -> None:
    op.drop_column("workspaces", "thumbnail_url")
