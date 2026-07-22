"""add user authentication

Revision ID: c4a8b7d2e901
Revises: 9f1d62a4c8b3
Create Date: 2026-07-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4a8b7d2e901"
down_revision: Union[str, Sequence[str], None] = "9f1d62a4c8b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LOCAL_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.alter_column("users", "display_name", new_column_name="username")
    op.alter_column("users", "username", type_=sa.String(32), existing_type=sa.String(100))
    op.add_column("users", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "users", sa.Column("auth_version", sa.Integer(), server_default=sa.text("0"), nullable=False)
    )
    op.add_column(
        "users",
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute(
        sa.text(
            "UPDATE users SET email = 'local@system.invalid', password_hash = '!', "
            "is_system = true WHERE id = CAST(:id AS uuid)"
        ).bindparams(id=LOCAL_USER_ID)
    )
    op.alter_column("users", "email", nullable=False)
    op.alter_column("users", "password_hash", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "is_system")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
    op.alter_column("users", "username", type_=sa.String(100), existing_type=sa.String(32))
    op.alter_column("users", "username", new_column_name="display_name")
