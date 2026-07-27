"""seed system garments

Revision ID: e1a5c7d9b2f4
Revises: c6d8e2f4a1b7
Create Date: 2026-07-27
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e1a5c7d9b2f4"
down_revision: Union[str, Sequence[str], None] = "c6d8e2f4a1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FILENAMES = [
    "6b6cd3d5-544e-4144-9f13-4b02de114f08-1.png",
    "63d7c2a2-8ef5-4bd9-9771-a1d5d7988768-1.png",
    "bae6f90a-39ec-4527-afd5-b681f62cdbb8-1.png",
    "814d83b6-25b7-45af-ab91-2093600a70d0-1.png",
    "9fbc620f-b494-45fd-b11e-dbf23a7dccbe-1.png",
    "71cc06d4-e502-4cc0-9a21-685a1f488a6d-1.png",
    "95d8cf50-96d1-459a-9622-9da404d80180-1.png",
    "55dd3c40-0c66-4c24-b60c-6681b7e1eeb8-1.png",
    "7d69715b-f450-4672-95e5-fe1a36b66fe8-1.png",
]


def garment_id(filename: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"mooncut:garment:{filename}")


def upgrade() -> None:
    garments = sa.table(
        "garments",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("image_url", sa.String()),
        sa.column("object_key", sa.String()),
        sa.column("width", sa.Integer()),
        sa.column("height", sa.Integer()),
        sa.column("garment_metadata", postgresql.JSONB()),
        sa.column("active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(
        garments,
        [
            {
                "id": garment_id(filename),
                "user_id": None,
                "name": f"服饰 {index:02d}",
                "image_url": f"https://image.nodepass.net/system/garments/{filename}",
                "object_key": f"system/garments/{filename}",
                "width": 1024,
                "height": 1024,
                "garment_metadata": {
                    "source_url": f"https://image.nodepass.net/generations/images/{filename}"
                },
                "active": True,
                "sort_order": index,
            }
            for index, filename in enumerate(FILENAMES, 1)
        ],
    )


def downgrade() -> None:
    garments = sa.table("garments", sa.column("id", sa.Uuid()))
    op.execute(garments.delete().where(garments.c.id.in_([*map(garment_id, FILENAMES)])))
