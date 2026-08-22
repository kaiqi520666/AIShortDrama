"""split video pricing by resolution

Revision ID: u2w4y6a8c0e1
Revises: t1v3x5z7b9c0
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "u2w4y6a8c0e1"
down_revision: Union[str, Sequence[str], None] = "t1v3x5z7b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM model_price_rules "
            "WHERE media_type = 'video' AND specification = ''"
        )
    )
    rows = [
        ("seedance-2-mini", "480p", "0.100"),
        ("seedance-2-mini", "720p", "0.200"),
        ("seedance-2-fast", "480p", "0.280"),
        ("seedance-2-fast", "720p", "0.560"),
        ("seedance-2", "480p", "0.450"),
        ("seedance-2", "720p", "0.900"),
        ("seedance-2", "1080p", "2.250"),
        ("seedance-2", "4k", "5.000"),
    ]
    connection.execute(
        sa.text(
            "INSERT INTO model_price_rules "
            "(id, provider, media_type, model, specification, billing_unit, cost_per_unit, "
            "input_cost_per_million, output_cost_per_million, base_credits, freeze_credits, multiplier, enabled) "
            "VALUES (:id, 'toapis', 'video', :model, :specification, 'second', :cost, "
            "NULL, NULL, NULL, NULL, 1.000, true)"
        ),
        [
            {"id": uuid.uuid4(), "model": model, "specification": specification, "cost": cost}
            for model, specification, cost in rows
        ],
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM model_price_rules "
            "WHERE media_type = 'video' AND specification IN "
            "('480p', '720p', '1080p', '4k')"
        )
    )
    connection.execute(
        sa.text(
            "INSERT INTO model_price_rules "
            "(id, provider, media_type, model, specification, billing_unit, cost_per_unit, "
            "input_cost_per_million, output_cost_per_million, base_credits, freeze_credits, multiplier, enabled) "
            "VALUES "
            "(:mini_id, 'toapis', 'video', 'seedance-2-mini', '', 'second', 0.5002, NULL, NULL, NULL, NULL, 1.000, true), "
            "(:fast_id, 'toapis', 'video', 'seedance-2-fast', '', 'second', 0.720, NULL, NULL, NULL, NULL, 1.000, true), "
            "(:full_id, 'toapis', 'video', 'seedance-2', '', 'second', 0.900, NULL, NULL, NULL, NULL, 1.000, true)"
        ),
        {"mini_id": uuid.uuid4(), "fast_id": uuid.uuid4(), "full_id": uuid.uuid4()},
    )
