"""remove retired video model

Revision ID: d2c4f6a8b1e3
Revises: f3b7d9e1a5c2
Create Date: 2026-07-30
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2c4f6a8b1e3"
down_revision: Union[str, Sequence[str], None] = "f3b7d9e1a5c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RETIRED_MODEL = "happy" + "horse-1.1"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM model_price_rules WHERE model = :model"),
        {"model": RETIRED_MODEL},
    )
    workspaces = connection.execute(
        sa.text("SELECT id, canvas FROM workspaces WHERE canvas::text LIKE :model"),
        {"model": f'%"model": "{RETIRED_MODEL}"%'},
    ).all()
    for workspace_id, canvas in workspaces:
        changed = False
        for node in canvas.get("nodes", []):
            data = node.get("data") or {}
            if data.get("model") != RETIRED_MODEL:
                continue
            data.update({"model": "seedance-2", "resolution": "720p"})
            changed = True
        if changed:
            connection.execute(
                sa.text(
                    "UPDATE workspaces SET canvas = CAST(:canvas AS jsonb), "
                    "version = version + 1 WHERE id = :workspace_id"
                ),
                {"canvas": json.dumps(canvas), "workspace_id": workspace_id},
            )


def downgrade() -> None:
    pass
