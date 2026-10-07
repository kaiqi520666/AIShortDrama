import importlib.util
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import engine
from scripts.check_migrations import verify_heads


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def load_migration(filename):
    spec = importlib.util.spec_from_file_location("migration_under_test", MIGRATIONS_DIR / filename)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


async def apply_migration(connection, filename):
    def run(sync_connection):
        migration = load_migration(filename)
        with Operations.context(MigrationContext.configure(sync_connection)):
            migration.upgrade()

    await connection.run_sync(run)


@asynccontextmanager
async def migration_schema():
    # Every migration runs in its own transactional schema; public stays untouched.
    schema = f"test_migration_{uuid.uuid4().hex}"
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            yield connection
        finally:
            await transaction.rollback()


async def create_legacy_tasks(connection, *, status="queued", credit_status="none", progress=0):
    await connection.execute(
        text(
            "CREATE TABLE generation_tasks ("
            "workspace_id uuid, user_id uuid, created_at timestamptz, "
            "status varchar(20), credit_status varchar(20), progress smallint)"
        )
    )
    await connection.execute(
        text(
            "INSERT INTO generation_tasks (status, credit_status, progress) "
            "VALUES (:status, :credit_status, :progress)"
        ),
        {"status": status, "credit_status": credit_status, "progress": progress},
    )


@pytest.mark.asyncio
async def test_constraint_migration_normalizes_legacy_quoted_states():
    async with migration_schema() as connection:
        await create_legacy_tasks(
            connection, status=" 'running' ", credit_status=" 'none' ", progress=None
        )
        await apply_migration(connection, "z1a2b3c4d5e6f_add_generation_task_constraints.py")
        row = (
            await connection.execute(
                text("SELECT status, credit_status, progress FROM generation_tasks")
            )
        ).one()
        assert tuple(row) == ("running", "none", 0)
        with pytest.raises(IntegrityError):
            async with connection.begin_nested():
                await connection.execute(text("UPDATE generation_tasks SET status = 'unknown'"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "credit_status", "progress"),
    [("unknown", "none", 0), ("queued", "invalid", 0), ("running", "frozen", 101)],
)
async def test_constraint_migration_rejects_unknown_history_without_partial_changes(
    status, credit_status, progress
):
    async with migration_schema() as connection:
        await create_legacy_tasks(
            connection, status=status, credit_status=credit_status, progress=progress
        )
        with pytest.raises(IntegrityError):
            async with connection.begin_nested():
                await apply_migration(
                    connection, "z1a2b3c4d5e6f_add_generation_task_constraints.py"
                )
        row = (
            await connection.execute(
                text("SELECT status, credit_status, progress FROM generation_tasks")
            )
        ).one()
        assert tuple(row) == (status, credit_status, progress)
        assert await connection.scalar(
            text(
                "SELECT count(*) FROM pg_constraint "
                "WHERE conrelid = 'generation_tasks'::regclass"
            )
        ) == 0


@pytest.mark.asyncio
async def test_recharge_trade_migration_refuses_duplicate_provider_transactions():
    async with migration_schema() as connection:
        await connection.execute(
            text("CREATE TABLE recharge_orders (provider text, provider_trade_no text)")
        )
        await connection.execute(
            text(
                "INSERT INTO recharge_orders VALUES "
                "('cahaya', 'same-trade'), ('cahaya', 'same-trade')"
            )
        )
        with pytest.raises(IntegrityError):
            async with connection.begin_nested():
                await apply_migration(connection, "z2b3c4d5e6f7a_add_recharge_trade_constraints.py")
        assert await connection.scalar(text("SELECT count(*) FROM recharge_orders")) == 2


@pytest.mark.asyncio
async def test_recharge_trade_migration_scopes_uniqueness_by_provider_and_allows_null():
    async with migration_schema() as connection:
        await connection.execute(
            text("CREATE TABLE recharge_orders (provider text, provider_trade_no text)")
        )
        await connection.execute(
            text(
                "INSERT INTO recharge_orders VALUES "
                "('cahaya', 'same-trade'), ('zpay', 'same-trade'), "
                "('cahaya', NULL), ('cahaya', NULL)"
            )
        )
        await apply_migration(connection, "z2b3c4d5e6f7a_add_recharge_trade_constraints.py")
        with pytest.raises(IntegrityError):
            async with connection.begin_nested():
                await connection.execute(
                    text("INSERT INTO recharge_orders VALUES ('cahaya', 'same-trade')")
                )
        assert await connection.scalar(text("SELECT count(*) FROM recharge_orders")) == 4


async def create_legacy_provider_tasks(connection):
    await connection.execute(
        text(
            "CREATE TABLE generation_tasks ("
            "id uuid PRIMARY KEY, provider text, task_type text, provider_task_id text, "
            "status text, started_at timestamptz, updated_at timestamptz)"
        )
    )


@pytest.mark.asyncio
async def test_provider_identity_migration_prechecks_duplicate_remote_ids():
    async with migration_schema() as connection:
        await create_legacy_provider_tasks(connection)
        await connection.execute(
            text(
                "INSERT INTO generation_tasks "
                "(id, provider, task_type, provider_task_id, status, updated_at) "
                "VALUES (:first, 'toapis', 'image', 'duplicate', 'running', now()), "
                "(:second, 'toapis', 'image', 'duplicate', 'running', now())"
            ),
            {"first": uuid.uuid4(), "second": uuid.uuid4()},
        )
        with pytest.raises(RuntimeError, match="Provider"):
            async with connection.begin_nested():
                await apply_migration(connection, "z3c4d5e6f7a8_add_provider_identity.py")
        assert await connection.scalar(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema = current_schema() "
                "AND table_name = 'generation_tasks' AND column_name = 'client_request_id'"
            )
        ) == 0
        assert await connection.scalar(text("SELECT count(*) FROM generation_tasks")) == 2


@pytest.mark.asyncio
async def test_provider_identity_migration_backfills_identity_and_submission_boundary():
    queued_id, running_id = uuid.uuid4(), uuid.uuid4()
    async with migration_schema() as connection:
        await create_legacy_provider_tasks(connection)
        await connection.execute(
            text(
                "INSERT INTO generation_tasks "
                "(id, provider, task_type, provider_task_id, status, started_at, updated_at) "
                "VALUES (:queued, 'toapis', 'image', NULL, 'queued', NULL, now()), "
                "(:running, 'toapis', 'video', 'remote-video', 'running', now(), now())"
            ),
            {"queued": queued_id, "running": running_id},
        )
        await apply_migration(connection, "z3c4d5e6f7a8_add_provider_identity.py")
        rows = {
            row.id: row
            for row in (
                await connection.execute(
                    text(
                        "SELECT id, client_request_id, submission_started_at "
                        "FROM generation_tasks"
                    )
                )
            ).all()
        }
        assert rows[queued_id].client_request_id == str(queued_id)
        assert rows[queued_id].submission_started_at is None
        assert rows[running_id].client_request_id == str(running_id)
        assert rows[running_id].submission_started_at is not None
        with pytest.raises(IntegrityError):
            async with connection.begin_nested():
                await connection.execute(
                    text(
                        "INSERT INTO generation_tasks "
                        "(id, provider, task_type, provider_task_id, client_request_id) "
                        "VALUES (:id, 'toapis', 'video', 'remote-video', 'another-client')"
                    ),
                    {"id": uuid.uuid4()},
                )


def test_migration_check_rejects_database_behind_or_ahead_of_image():
    verify_heads({"revision-2"}, {"revision-2"})
    with pytest.raises(RuntimeError, match="do not match"):
        verify_heads({"revision-1"}, {"revision-2"})
    with pytest.raises(RuntimeError, match="do not match"):
        verify_heads({"revision-3"}, {"revision-2"})
