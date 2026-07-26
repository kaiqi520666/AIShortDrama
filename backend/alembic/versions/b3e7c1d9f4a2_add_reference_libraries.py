"""add reference libraries

Revision ID: b3e7c1d9f4a2
Revises: a1c7e4d9b2f6
Create Date: 2026-07-26
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b3e7c1d9f4a2"
down_revision: Union[str, Sequence[str], None] = "a1c7e4d9b2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MODEL_FILENAMES = [
    "10ceb15ec0ad430b9ef9ac0eb92d9c5e.png",
    "14b359841edb4d50028a3244e134d0af.png",
    "18e9d453d226966892123157eb43caa6.png",
    "296d71c0fe0910e63bf3cd10cafe2114.png",
    "2dc021c209110df11f4c689473b72294.png",
    "2e17466edd26f4978075214894e42640.png",
    "33ec87f1da0b60b18ad6e93a0698061f.png",
    "39f1306b5af144696b21c8ad191970b0.png",
    "625f66cb1f35c116e5ee352227631ed8.png",
    "652401272e8274e381b2a01f92e6d1d2.png",
    "6af4f1a648faa00cfdd80a6112b0c99e.png",
    "7f1bbce8d4e7c6eab4c4ce520fbc4359.png",
    "84fc2055d7e95d1932ca4c6330e57ef1.png",
    "93bb1bb35715e703e45ecf475e928960.png",
    "97ed9e1e562c697e9e693c9765e39ed7.png",
    "9a20be85d4cc9df5393d0a2bf56ae393.png",
    "a382dab2122d923cdf8577f900a26ed1.png",
    "a9ff82de3ba38df9ae382a277757a8b3.png",
    "abf657269fea635934364a4f33f3ee74.png",
    "aeddca98b3d35b633566ffb3789c9706.png",
    "af0365ac163f4ce851af248e7290d368.png",
    "c2168ccb6a4b4829ae6476f54502b7f2.png",
    "c5d4cc970d81154c33c931dcbf529c94.png",
    "d0409c74d78262c25e4b3964c229708b.png",
    "e23dc2083b24e38f876940da012848da.png",
]


def _create_reference_table(name: str, metadata_column: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            metadata_column,
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(f"ix_{name}_user_active_sort", name, ["user_id", "active", "sort_order"])


def _move_legacy_reference_assets(table: str, category: str, metadata_column: str) -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO {table}
                (id, user_id, name, image_url, object_key, width, height,
                 {metadata_column}, created_at, updated_at)
            SELECT id, user_id, name, url, object_key, width, height,
                   asset_metadata - 'category', created_at, updated_at
            FROM assets
            WHERE deleted_at IS NULL AND asset_metadata ->> 'category' = :category
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(category=category)
    )
    op.execute(
        sa.text(
            """
            UPDATE assets
            SET deleted_at = now()
            WHERE deleted_at IS NULL AND asset_metadata ->> 'category' = :category
            """
        ).bindparams(category=category)
    )


def upgrade() -> None:
    _create_reference_table("outfit_models", "model_metadata")
    _create_reference_table("characters", "character_metadata")
    op.bulk_insert(
        sa.table(
            "outfit_models",
            sa.column("id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("image_url", sa.String()),
            sa.column("object_key", sa.String()),
            sa.column("active", sa.Boolean()),
            sa.column("sort_order", sa.Integer()),
        ),
        [
            {
                "id": uuid.uuid5(uuid.NAMESPACE_URL, f"mooncut:outfit-model:{filename}"),
                "name": f"模特 {index:02d}",
                "image_url": f"https://image.nodepass.net/system/outfit-models/{filename}",
                "object_key": f"system/outfit-models/{filename}",
                "active": True,
                "sort_order": index,
            }
            for index, filename in enumerate(MODEL_FILENAMES, 1)
        ],
    )
    _move_legacy_reference_assets("outfit_models", "model", "model_metadata")
    _move_legacy_reference_assets("characters", "character", "character_metadata")


def downgrade() -> None:
    op.execute(
        """
        UPDATE assets
        SET deleted_at = NULL
        WHERE id IN (
            SELECT id FROM outfit_models WHERE user_id IS NOT NULL
            UNION
            SELECT id FROM characters WHERE user_id IS NOT NULL
        )
        """
    )
    op.drop_index("ix_characters_user_active_sort", table_name="characters")
    op.drop_table("characters")
    op.drop_index("ix_outfit_models_user_active_sort", table_name="outfit_models")
    op.drop_table("outfit_models")
