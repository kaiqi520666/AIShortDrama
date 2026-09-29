"""add Cahaya recharge fields"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "x7c9e1a2b3d4"
down_revision = "v3x5z7b9d1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_policies", sa.Column("idr_recharge_min", sa.Integer(), server_default="150000", nullable=False))
    op.add_column("billing_policies", sa.Column("idr_recharge_max", sa.Integer(), server_default="15000000", nullable=False))
    op.add_column("billing_policies", sa.Column("idr_unit_amount", sa.Integer(), server_default="150000", nullable=False))
    op.add_column("billing_policies", sa.Column("idr_unit_credits", sa.Integer(), server_default="1000", nullable=False))
    op.add_column("recharge_orders", sa.Column("currency", sa.String(length=3), server_default="CNY", nullable=False))
    op.add_column("recharge_orders", sa.Column("amount_minor", sa.Integer(), server_default="0", nullable=False))
    op.add_column("recharge_orders", sa.Column("provider_payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("recharge_orders", sa.Column("callback_payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("recharge_orders", sa.Column("callback_received_at", sa.DateTime(timezone=True)))
    op.add_column("recharge_tiers", sa.Column("currency", sa.String(length=3), server_default="CNY", nullable=False))
    connection = op.get_bind()
    policy = connection.execute(
        sa.text("SELECT unit_amount_cents FROM billing_policies WHERE key = 'default'")
    ).scalar_one()
    cny_tiers = connection.execute(
        sa.text(
            "SELECT min_amount_cents, bonus_rate_bps, enabled "
            "FROM recharge_tiers WHERE currency = 'CNY'"
        )
    ).mappings().all()
    if cny_tiers:
        tier_table = sa.table(
            "recharge_tiers",
            sa.column("id", sa.Uuid()),
            sa.column("currency", sa.String(length=3)),
            sa.column("min_amount_cents", sa.Integer()),
            sa.column("bonus_rate_bps", sa.Integer()),
            sa.column("enabled", sa.Boolean()),
        )
        op.bulk_insert(
            tier_table,
            [
                {
                    "id": __import__("uuid").uuid4(),
                    "currency": "IDR",
                    "min_amount_cents": int(round(row["min_amount_cents"] * 150000 / policy)),
                    "bonus_rate_bps": row["bonus_rate_bps"],
                    "enabled": row["enabled"],
                }
                for row in cny_tiers
            ],
        )
    op.drop_constraint("recharge_tiers_min_amount_cents_key", "recharge_tiers", type_="unique")
    op.create_unique_constraint("uq_recharge_tiers_currency_amount", "recharge_tiers", ["currency", "min_amount_cents"])
    op.execute("UPDATE recharge_orders SET amount_minor = amount_cents WHERE amount_minor = 0")


def downgrade() -> None:
    op.drop_constraint("uq_recharge_tiers_currency_amount", "recharge_tiers", type_="unique")
    op.drop_column("recharge_tiers", "currency")
    for column in ("callback_received_at", "callback_payload", "provider_payload", "amount_minor", "currency"):
        op.drop_column("recharge_orders", column)
    for column in ("idr_unit_credits", "idr_unit_amount", "idr_recharge_max", "idr_recharge_min"):
        op.drop_column("billing_policies", column)
