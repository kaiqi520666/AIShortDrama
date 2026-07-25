"""add credit recharge

Revision ID: d4f7a9c2e1b3
Revises: c9d2e4f6a7b8
Create Date: 2026-07-25
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4f7a9c2e1b3"
down_revision: Union[str, Sequence[str], None] = "c9d2e4f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recharge_tiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("min_amount_cents", sa.Integer(), nullable=False),
        sa.Column("bonus_rate_bps", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("min_amount_cents >= 3500", name="ck_recharge_tiers_min_amount"),
        sa.CheckConstraint("bonus_rate_bps BETWEEN 0 AND 3000", name="ck_recharge_tiers_bonus_rate"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("min_amount_cents"),
    )
    op.bulk_insert(
        sa.table(
            "recharge_tiers",
            sa.column("id", sa.Uuid()),
            sa.column("min_amount_cents", sa.Integer()),
            sa.column("bonus_rate_bps", sa.Integer()),
            sa.column("enabled", sa.Boolean()),
        ),
        [
            {"id": uuid.uuid4(), "min_amount_cents": amount, "bonus_rate_bps": rate, "enabled": True}
            for amount, rate in ((3500, 0), (10500, 300), (17500, 600), (35000, 800), (70000, 1000))
        ],
    )
    op.create_table(
        "recharge_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tier_id", sa.Uuid(), nullable=True),
        sa.Column("out_trade_no", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), server_default="zpay", nullable=False),
        sa.Column("provider_trade_no", sa.String(length=64), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("base_credits", sa.BigInteger(), nullable=False),
        sa.Column("bonus_credits", sa.BigInteger(), nullable=False),
        sa.Column("total_credits", sa.BigInteger(), nullable=False),
        sa.Column("tier_snapshot", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("pay_type", sa.String(length=20), server_default="wxpay", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("pay_url", sa.String(length=500), nullable=True),
        sa.Column("qr_code", sa.String(length=500), nullable=True),
        sa.Column("qr_img", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'paid', 'failed')", name="ck_recharge_orders_status"),
        sa.ForeignKeyConstraint(["tier_id"], ["recharge_tiers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("out_trade_no"),
    )
    op.create_index("ix_recharge_orders_user_created_at", "recharge_orders", ["user_id", "created_at"])
    op.create_index("ix_recharge_orders_status_created_at", "recharge_orders", ["status", "created_at"])
    op.add_column("credit_ledger", sa.Column("recharge_order_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_credit_ledger_recharge_order", "credit_ledger", "recharge_orders", ["recharge_order_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_credit_ledger_recharge_order_id", "credit_ledger", ["recharge_order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_credit_ledger_recharge_order_id", "credit_ledger", type_="unique")
    op.drop_constraint("fk_credit_ledger_recharge_order", "credit_ledger", type_="foreignkey")
    op.drop_column("credit_ledger", "recharge_order_id")
    op.drop_index("ix_recharge_orders_status_created_at", table_name="recharge_orders")
    op.drop_index("ix_recharge_orders_user_created_at", table_name="recharge_orders")
    op.drop_table("recharge_orders")
    op.drop_table("recharge_tiers")
