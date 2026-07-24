"""snapshot credit ledger model

Revision ID: e8c41d7a2b90
Revises: a73d8c41f2e6
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8c41d7a2b90"
down_revision: Union[str, Sequence[str], None] = "a73d8c41f2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("credit_ledger", sa.Column("media_type", sa.String(16), nullable=True))
    op.add_column("credit_ledger", sa.Column("model", sa.String(64), nullable=True))
    op.execute(
        """
        UPDATE credit_ledger AS ledger
        SET media_type = COALESCE(task.pricing_snapshot ->> 'media_type', task.task_type),
            model = task.model
        FROM generation_tasks AS task
        WHERE ledger.task_id = task.id
        """
    )
    op.execute(
        """
        UPDATE credit_ledger
        SET model = substring(note FROM '^结算 (.+) 生成积分$')
        WHERE model IS NULL
          AND entry_type = 'consume'
          AND note ~ '^结算 .+ 生成积分$'
        """
    )
    op.execute(
        """
        UPDATE credit_ledger AS ledger
        SET media_type = prices.media_type
        FROM (
            SELECT model, min(media_type) AS media_type
            FROM model_price_rules
            GROUP BY model
        ) AS prices
        WHERE ledger.media_type IS NULL
          AND ledger.model = prices.model
        """
    )


def downgrade() -> None:
    op.drop_column("credit_ledger", "model")
    op.drop_column("credit_ledger", "media_type")
