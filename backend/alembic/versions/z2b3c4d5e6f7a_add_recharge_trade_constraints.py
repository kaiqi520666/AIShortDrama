"""add recharge provider trade constraints

Revision ID: z2b3c4d5e6f7a
Revises: z1a2b3c4d5e6f
"""

from alembic import op
import sqlalchemy as sa


revision = "z2b3c4d5e6f7a"
down_revision = "z1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_recharge_orders_provider_trade_no",
        "recharge_orders",
        ["provider", "provider_trade_no"],
        unique=True,
        postgresql_where=sa.text("provider_trade_no IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_recharge_orders_provider_trade_no", table_name="recharge_orders")
