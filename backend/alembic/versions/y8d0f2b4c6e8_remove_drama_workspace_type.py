"""Remove the retired drama workspace type after explicit data cleanup."""

from alembic import op
import sqlalchemy as sa

revision = "y8d0f2b4c6e8"
down_revision = "x7c9e1a2b3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM workspaces WHERE workspace_type = 'drama'")):
        raise RuntimeError(
            "Purge retired drama projects and their exclusive media with "
            "python -m scripts.purge_drama_workspaces --apply before this migration."
        )
    op.drop_constraint("ck_workspaces_workspace_type", "workspaces", type_="check")
    op.create_check_constraint(
        "ck_workspaces_workspace_type", "workspaces",
        "workspace_type IN ('general', 'ecommerce')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_workspaces_workspace_type", "workspaces", type_="check")
    op.create_check_constraint(
        "ck_workspaces_workspace_type", "workspaces",
        "workspace_type IN ('general', 'ecommerce', 'drama')",
    )
