"""add credit billing

Revision ID: a73d8c41f2e6
Revises: c4a8b7d2e901
Create Date: 2026-07-24
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a73d8c41f2e6"
down_revision: Union[str, Sequence[str], None] = "c4a8b7d2e901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("credit_balance", sa.BigInteger(), server_default="0", nullable=False)
    )
    op.add_column(
        "users", sa.Column("credit_frozen", sa.BigInteger(), server_default="0", nullable=False)
    )
    op.create_check_constraint(
        "ck_users_credit_balance_nonnegative", "users", "credit_balance >= 0"
    )
    op.create_check_constraint(
        "ck_users_credit_frozen_nonnegative", "users", "credit_frozen >= 0"
    )
    op.add_column(
        "generation_tasks",
        sa.Column(
            "pricing_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "generation_tasks",
        sa.Column("frozen_credits", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "generation_tasks",
        sa.Column("charged_credits", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.add_column(
        "generation_tasks",
        sa.Column("credit_status", sa.String(20), server_default="'none'", nullable=False),
    )
    op.create_table(
        "model_price_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("media_type", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("specification", sa.String(32), server_default=sa.text("''"), nullable=False),
        sa.Column("billing_unit", sa.String(24), nullable=False),
        sa.Column("cost_per_unit", sa.Numeric(12, 6), nullable=True),
        sa.Column("input_cost_per_million", sa.Numeric(12, 6), nullable=True),
        sa.Column("output_cost_per_million", sa.Numeric(12, 6), nullable=True),
        sa.Column("base_credits", sa.Integer(), nullable=True),
        sa.Column("freeze_credits", sa.Integer(), nullable=True),
        sa.Column("multiplier", sa.Numeric(8, 3), server_default="1.000", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_model_price_rules_lookup",
        "model_price_rules",
        ["media_type", "model", "specification"],
        unique=True,
    )
    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("frozen_after", sa.BigInteger(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"], ["generation_tasks.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_credit_ledger_user_created_at", "credit_ledger", ["user_id", "created_at"]
    )
    op.create_index(
        "uq_credit_ledger_idempotency_key", "credit_ledger", ["idempotency_key"], unique=True
    )

    rules = sa.table(
        "model_price_rules",
        sa.column("id", sa.Uuid()),
        sa.column("provider", sa.String()),
        sa.column("media_type", sa.String()),
        sa.column("model", sa.String()),
        sa.column("specification", sa.String()),
        sa.column("billing_unit", sa.String()),
        sa.column("cost_per_unit", sa.Numeric()),
        sa.column("input_cost_per_million", sa.Numeric()),
        sa.column("output_cost_per_million", sa.Numeric()),
        sa.column("base_credits", sa.Integer()),
        sa.column("freeze_credits", sa.Integer()),
    )
    rows = []
    image_prices = {
        "gpt-image-2": {"1K": "0.105", "2K": "0.140", "4K": "0.175"},
        "doubao-seedream-5-0-pro": {"1K": "0.300", "2K": "0.300"},
        "doubao-seedream-5-0": {"2K": "0.2205", "3K": "0.2205"},
        "gemini-3-pro-image-preview": {"1K": "0.420", "2K": "0.420", "4K": "0.420"},
        "gemini-3.1-flash-image-preview": {"1K": "0.210", "2K": "0.210", "4K": "0.210"},
    }
    for model, prices in image_prices.items():
        for specification, cost in prices.items():
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "provider": "toapis",
                    "media_type": "image",
                    "model": model,
                    "specification": specification,
                    "billing_unit": "image",
                    "cost_per_unit": cost,
                }
            )
    for model, cost in {
        "seedance-2": "0.900",
        "seedance-2-fast": "0.720",
        "seedance-2-mini": "0.5002",
        "happyhorse-1.1": "0.600",
    }.items():
        rows.append(
            {
                "id": uuid.uuid4(),
                "provider": "toapis",
                "media_type": "video",
                "model": model,
                "specification": "",
                "billing_unit": "second",
                "cost_per_unit": cost,
            }
        )
    rows.extend(
        [
            {
                "id": uuid.uuid4(),
                "provider": "dashscope",
                "media_type": "text",
                "model": "qwen3.7-plus",
                "specification": "",
                "billing_unit": "request",
                "input_cost_per_million": "1.600",
                "output_cost_per_million": "6.400",
                "base_credits": 1,
            },
            {
                "id": uuid.uuid4(),
                "provider": "dashscope",
                "media_type": "text",
                "model": "qwen3.6-flash",
                "specification": "",
                "billing_unit": "request",
                "input_cost_per_million": "1.200",
                "output_cost_per_million": "7.200",
                "base_credits": 1,
            },
            {
                "id": uuid.uuid4(),
                "provider": "volcengine",
                "media_type": "audio",
                "model": "seed-audio-1.0-multilingual",
                "specification": "",
                "billing_unit": "minute",
                "cost_per_unit": "1.000",
                "freeze_credits": 60,
            },
        ]
    )
    for row in rows:
        for field in (
            "cost_per_unit",
            "input_cost_per_million",
            "output_cost_per_million",
            "base_credits",
            "freeze_credits",
        ):
            row.setdefault(field, None)
    op.bulk_insert(rules, rows)


def downgrade() -> None:
    op.drop_table("credit_ledger")
    op.drop_table("model_price_rules")
    op.drop_column("generation_tasks", "credit_status")
    op.drop_column("generation_tasks", "charged_credits")
    op.drop_column("generation_tasks", "frozen_credits")
    op.drop_column("generation_tasks", "pricing_snapshot")
    op.drop_constraint("ck_users_credit_frozen_nonnegative", "users", type_="check")
    op.drop_constraint("ck_users_credit_balance_nonnegative", "users", type_="check")
    op.drop_column("users", "credit_frozen")
    op.drop_column("users", "credit_balance")
