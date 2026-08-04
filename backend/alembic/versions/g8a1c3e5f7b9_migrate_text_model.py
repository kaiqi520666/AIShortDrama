"""migrate text generation to GPT-5.6 Sol via AIJWS

Revision ID: g8a1c3e5f7b9
Revises: d2c4f6a8b1e3
Create Date: 2026-08-04
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g8a1c3e5f7b9"
down_revision: Union[str, Sequence[str], None] = "d2c4f6a8b1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE model_price_rules SET enabled = false "
            "WHERE model IN ('qwen3.7-plus', 'qwen3.6-flash')"
        )
    )
    rules = sa.table(
        "model_price_rules",
        sa.column("id", sa.Uuid()),
        sa.column("provider", sa.String()),
        sa.column("media_type", sa.String()),
        sa.column("model", sa.String()),
        sa.column("specification", sa.String()),
        sa.column("billing_unit", sa.String()),
        sa.column("input_cost_per_million", sa.Numeric()),
        sa.column("output_cost_per_million", sa.Numeric()),
        sa.column("base_credits", sa.Integer()),
    )
    op.bulk_insert(
        rules,
        [
            {
                "id": uuid.uuid4(),
                "provider": "aijws",
                "media_type": "text",
                "model": "gpt-5.6-sol",
                "specification": "",
                "billing_unit": "request",
                "input_cost_per_million": None,
                "output_cost_per_million": None,
                "base_credits": 1,
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM model_price_rules WHERE model = 'gpt-5.6-sol'")
    )
    op.execute(
        sa.text(
            "UPDATE model_price_rules SET enabled = true "
            "WHERE model IN ('qwen3.7-plus', 'qwen3.6-flash')"
        )
    )
