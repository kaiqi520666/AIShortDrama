"""add credit policy

Revision ID: v3x5z7b9d1f2
Revises: u2w4y6a8c0e1
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "v3x5z7b9d1f2"
down_revision: Union[str, Sequence[str], None] = "u2w4y6a8c0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_policies",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "registration_bonus_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "registration_bonus_credits",
            sa.Integer(),
            server_default=sa.text("10"),
            nullable=False,
        ),
        sa.Column(
            "daily_refill_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "daily_minimum_credits",
            sa.Integer(),
            server_default=sa.text("10"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("key = 'default'", name="ck_credit_policies_singleton"),
        sa.CheckConstraint(
            "registration_bonus_credits > 0",
            name="ck_credit_policies_registration_bonus_positive",
        ),
        sa.CheckConstraint(
            "daily_minimum_credits > 0",
            name="ck_credit_policies_daily_minimum_positive",
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.execute("INSERT INTO credit_policies (key) VALUES ('default')")


def downgrade() -> None:
    op.drop_table("credit_policies")
