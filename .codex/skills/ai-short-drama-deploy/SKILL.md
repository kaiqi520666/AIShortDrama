---
name: ai-short-drama-deploy
description: Check or update the AIShortDrama production deployment on its fixed Tencent Cloud server. For other explicitly named projects on the same server, perform read-only status, payment, log, or configuration inspection without applying the AIShortDrama deployment routine.
---

# AIShortDrama Production Deploy

Use `scripts/update.ps1` for the routine workflow. It contains the fixed project path,
SSH target, key path, production directory, Compose project, and public health URL.

## Authorization

- For status, health, logs, or inspection requests, run the script with `-Mode Status` and keep all remote actions read-only.
- Run `-Mode Deploy` only when the current user request explicitly says to deploy or update production. Skill invocation alone without a deployment command is not authorization to mutate production.
- Use `-SkipTests` only when the user explicitly asks to skip tests.
- Infrastructure changes are outside the routine script. If an update requires syncing `deploy/docker-compose.yml`, OpenResty configuration, certificates, production `.env`, cron, or backup scripts, explain the exact changes and get confirmation before modifying them.

## Invariants

- Never read, print, download, replace, or upload the production `.env` as a whole. The script may read or change only its `BACKEND_IMAGE` and `FRONTEND_IMAGE` lines on the server.
- Do not infer mutation permission for other projects; keep cross-project inspections read-only unless the user explicitly requests a change.
- Connect directly to `43.161.251.55` with SSH proxy and jump-host settings disabled. Do not change Windows VPN, TUN, proxy, or routing settings.
- For AIShortDrama deployment operations, operate only in `/opt/ai-short-drama/deploy` with Compose project name `ai-short-drama`. For explicitly authorized inspections of other projects, use their own project paths and containers without applying this deployment workflow.
- Require a clean Git worktree for deployment. Deploy only committed code and tag both images with the current short commit SHA.
- Back up PostgreSQL before changing image tags. Keep old Docker images for rollback.
- A code-image rollback does not reverse an Alembic migration. If migration compatibility is uncertain, stop before deployment and report it.
- Stop on failed tests, image builds, backup, upload, migration, container health, or public health. Do not continue through a failed stage.

## Commands

Run from PowerShell; the script works independently of the current directory.

```powershell
& '.codex\skills\ai-short-drama-deploy\scripts\update.ps1' -Mode Status
```

```powershell
& '.codex\skills\ai-short-drama-deploy\scripts\update.ps1' -Mode Deploy
```

After deployment, report the deployed commit, container state, public health result, and whether rollback was needed. Do not include credentials or environment values.
