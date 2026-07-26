"""store original workspace thumbnail

Revision ID: a1c7e4d9b2f6
Revises: f6b3d8e1a2c4
Create Date: 2026-07-26
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a1c7e4d9b2f6"
down_revision: Union[str, Sequence[str], None] = "f6b3d8e1a2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE workspaces
        SET thumbnail_url = regexp_replace(
            thumbnail_url,
            '([?&])x-oss-process=image/resize,w_480/quality,q_80/format,webp$',
            ''
        )
        WHERE thumbnail_url LIKE '%x-oss-process=image/resize,w_480/quality,q_80/format,webp'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE workspaces
        SET thumbnail_url = thumbnail_url
            || CASE WHEN position('?' IN thumbnail_url) > 0 THEN '&' ELSE '?' END
            || 'x-oss-process=image/resize,w_480/quality,q_80/format,webp'
        WHERE thumbnail_url IS NOT NULL
          AND thumbnail_url NOT LIKE '%x-oss-process=%'
        """
    )
