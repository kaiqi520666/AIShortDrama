"""Verify the deployed database reached this image's migration head."""

import asyncio
import sys
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402


REQUIRED_CONSTRAINTS = {
    ("generation_tasks", "ck_generation_tasks_status"),
    ("generation_tasks", "ck_generation_tasks_credit_status"),
    ("generation_tasks", "ck_generation_tasks_progress"),
    ("users", "ck_users_credit_balance_nonnegative"),
    ("users", "ck_users_credit_frozen_nonnegative"),
}
REQUIRED_INDEXES = {
    "uq_credit_ledger_idempotency_key",
    "uq_recharge_orders_provider_trade_no",
    "uq_generation_tasks_provider_client",
    "uq_generation_tasks_provider_remote",
}


def verify_heads(current_heads: set[str], expected_heads: set[str]) -> None:
    if current_heads != expected_heads:
        raise RuntimeError(
            f"Database revisions {sorted(current_heads)} do not match "
            f"image heads {sorted(expected_heads)}"
        )


async def check_migrations() -> None:
    config = Config(BACKEND_DIR / "alembic.ini")
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())
    engine = create_async_engine(get_settings().active_database_url)
    try:
        async with engine.connect() as connection:
            current_heads = await connection.run_sync(
                lambda sync_connection: set(
                    MigrationContext.configure(sync_connection).get_current_heads()
                )
            )
            verify_heads(current_heads, expected_heads)
            constraints = {
                tuple(row)
                for row in (
                    await connection.execute(
                        text(
                            "SELECT relation.relname, constraint_row.conname "
                            "FROM pg_constraint AS constraint_row "
                            "JOIN pg_class AS relation ON relation.oid = constraint_row.conrelid "
                            "JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace "
                            "WHERE namespace.nspname = current_schema()"
                        )
                    )
                ).all()
            }
            indexes = set(
                (
                    await connection.execute(
                        text(
                            "SELECT indexname FROM pg_indexes "
                            "WHERE schemaname = current_schema()"
                        )
                    )
                ).scalars()
            )
            missing_constraints = REQUIRED_CONSTRAINTS - constraints
            missing_indexes = REQUIRED_INDEXES - indexes
            if missing_constraints or missing_indexes:
                raise RuntimeError(
                    f"Missing database constraints: {sorted(missing_constraints)}; "
                    f"missing indexes: {sorted(missing_indexes)}"
                )
        print(f"Migration verification passed: {', '.join(sorted(current_heads))}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_migrations())
