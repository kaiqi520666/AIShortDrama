"""Preview or explicitly purge retired drama projects and exclusive OSS media.

Run from backend: uv run python -m scripts.purge_drama_workspaces [--apply]
Production requires --production; shared storage needs cross-environment review first.
Historical credit ledger entries remain.
"""

import argparse
import asyncio
import json
from urllib.parse import unquote, urlsplit

from sqlalchemy import delete, select, text, update
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models import Asset, GenerationTask, Workspace
from app.models.base import Base
from app.services.storage import OssStorage


def object_keys(value, base_url: str) -> set[str]:
    if isinstance(value, dict):
        return set().union(*(object_keys(item, base_url) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(object_keys(item, base_url) for item in value))
    prefix = base_url.rstrip("/") + "/"
    if isinstance(value, str) and base_url and value.startswith(prefix):
        key = unquote(urlsplit(value[len(prefix):]).path)
        if key and ".." not in key.split("/"):
            return {key}
    return set()


def exclusive_keys(candidates: set[str], retained_rows: list, base_url: str) -> set[str]:
    protected = object_keys(retained_rows, base_url)
    # Metadata can hold raw keys or URLs embedded in serialized prompts.
    retained_text = json.dumps(retained_rows, default=str, ensure_ascii=False)
    return {key for key in candidates - protected if key not in retained_text}


async def purge(apply: bool = False, keep_objects: set[str] | None = None, *, production: bool = False) -> dict:
    settings = get_settings()
    if production:
        if settings.app_env != "production":
            raise RuntimeError("--production requires APP_ENV=production.")
    elif settings.app_env == "production" or make_url(settings.active_database_url).host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Use --production explicitly for a production database.")
    async with SessionLocal() as db:
        # Prevent new references or tasks appearing between planning and deletion.
        if apply:
            names = ", ".join('"' + table.name + '"' for table in Base.metadata.sorted_tables)
            await db.execute(text(f"LOCK TABLE {names} IN SHARE ROW EXCLUSIVE MODE"))
        workspaces = list(await db.scalars(select(Workspace).where(Workspace.workspace_type == "drama")))
        workspace_ids = [row.id for row in workspaces]
        tasks = list(await db.scalars(select(GenerationTask).where(GenerationTask.workspace_id.in_(workspace_ids))))
        if any(task.status in {"queued", "running"} or task.credit_status == "frozen" for task in tasks):
            raise RuntimeError("Wait for drama tasks and frozen credits to settle before purging.")
        task_ids = [row.id for row in tasks]
        assets = list(await db.scalars(select(Asset).where(
            Asset.workspace_id.in_(workspace_ids) | Asset.generation_task_id.in_(task_ids)
        )))
        asset_ids = [row.id for row in assets]
        excluded = {"workspaces": workspace_ids, "generation_tasks": task_ids, "assets": asset_ids}
        retained = []
        for table in Base.metadata.sorted_tables:
            query = select(table)
            if table.name in excluded:
                query = query.where(table.c.id.not_in(excluded[table.name]))
            retained.extend(dict(row) for row in (await db.execute(query)).mappings())
        retained_text = json.dumps(retained, default=str, ensure_ascii=False)
        shared_assets = [asset for asset in assets if str(asset.id) in retained_text]
        retained.extend({
            "url": asset.url, "object_key": asset.object_key, "metadata": asset.asset_metadata,
        } for asset in shared_assets)
        shared_ids = {asset.id for asset in shared_assets}
        deleted_assets = [asset for asset in assets if asset.id not in shared_ids]
        candidates = object_keys(
            [workspace.canvas for workspace in workspaces]
            + [workspace.thumbnail_url for workspace in workspaces]
            + [task.result for task in tasks]
            + [{"url": asset.url, "metadata": asset.asset_metadata} for asset in assets],
            settings.oss_public_base_url,
        )
        candidates.update(asset.object_key for asset in assets if asset.object_key)
        keys = exclusive_keys(candidates, retained, settings.oss_public_base_url) - (keep_objects or set())
        report = {
            "apply": apply, "workspaces": len(workspaces), "tasks": len(tasks),
            "assets": len(deleted_assets), "shared_assets_preserved": len(shared_assets),
            "exclusive_objects": sorted(keys), "shared_objects_preserved": sorted(candidates - keys),
        }
        print(json.dumps(report, ensure_ascii=False))
        if apply:
            if keys:
                storage = OssStorage()
                # On any OSS failure the DB transaction rolls back, so the command can be retried.
                for key in sorted(keys):
                    await storage.delete_object(key)
            if shared_ids:
                await db.execute(update(Asset).where(Asset.id.in_(shared_ids)).values(
                    workspace_id=None, generation_task_id=None,
                ))
            await db.execute(delete(Asset).where(Asset.id.in_([asset.id for asset in deleted_assets])))
            await db.execute(delete(GenerationTask).where(GenerationTask.id.in_(task_ids)))
            await db.execute(delete(Workspace).where(Workspace.id.in_(workspace_ids)))
            await db.commit()
        return report


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--production", action="store_true", help="Explicitly target the production database")
    parser.add_argument("--keep-object", action="append", default=[], help="Object still referenced by another environment")
    args = parser.parse_args()
    try:
        await purge(args.apply, set(args.keep_object), production=args.production)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
