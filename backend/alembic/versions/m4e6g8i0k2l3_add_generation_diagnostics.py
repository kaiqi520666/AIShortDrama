"""add generation diagnostics

Revision ID: m4e6g8i0k2l3
Revises: k3d5f7a9b1c2
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "m4e6g8i0k2l3"
down_revision: Union[str, Sequence[str], None] = "k3d5f7a9b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_tasks",
        sa.Column("diagnostic_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_tasks", "diagnostic_snapshot")
