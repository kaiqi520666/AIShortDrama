"""backfill latest generated thumbnail

Revision ID: b7e3d9a1c5f8
Revises: f2a9c1b7d4e6
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b7e3d9a1c5f8"
down_revision: Union[str, Sequence[str], None] = "f2a9c1b7d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE workspaces AS workspace
        SET thumbnail_url = latest.url
        FROM (
            SELECT DISTINCT ON (workspace_id)
                workspace_id,
                result -> 'data' -> 0 ->> 'url' AS url
            FROM generation_tasks
            WHERE task_type = 'image'
              AND status = 'succeeded'
              AND NULLIF(result -> 'data' -> 0 ->> 'url', '') IS NOT NULL
            ORDER BY workspace_id, finished_at DESC NULLS LAST, created_at DESC
        ) AS latest
        WHERE workspace.id = latest.workspace_id
        """
    )
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


def downgrade() -> None:
    pass
