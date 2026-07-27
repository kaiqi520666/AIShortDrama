"""seed more system garments

Revision ID: f3b7d9e1a5c2
Revises: e1a5c7d9b2f4
Create Date: 2026-07-27
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f3b7d9e1a5c2"
down_revision: Union[str, Sequence[str], None] = "e1a5c7d9b2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FILENAMES = [
    "5a5e188e-d360-4a36-a3da-519e8e600c61-1.png",
    "5eb6a515-3e67-4269-9aa2-3c9ca0e24719-1.png",
    "2206a3d8-7ce0-4933-832d-db61949bc590-1.png",
    "52eadd3a-451a-4dc8-9fe0-508697397b6e-1.png",
    "6b1f93ff-d72d-45e8-83fb-8586ef80a390-1.png",
    "a6e069e9-ca21-4e5c-9466-bd5b5de750cb-1.png",
    "ea58ecd5-2ff6-4b9c-b672-29705903a735-1.png",
    "fa00a35b-412d-4336-9edd-bc04557ed243-1.png",
    "0daaf549-3634-4918-bbae-7180bf6017c8-1.png",
    "d86b3704-44e4-4d97-bd36-70f8b222f8e2-1.png",
    "74d21229-32f3-4a6e-833f-4b49e9341655-1.png",
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
            for index, filename in enumerate(FILENAMES, 10)
        ],
    )


def downgrade() -> None:
    garments = sa.table("garments", sa.column("id", sa.Uuid()))
    op.execute(garments.delete().where(garments.c.id.in_([*map(garment_id, FILENAMES)])))
