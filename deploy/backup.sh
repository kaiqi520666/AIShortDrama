#!/bin/sh
set -eu

deploy_dir=/opt/ai-short-drama/deploy
backup_dir=/opt/ai-short-drama/backups
timestamp=$(date -u +%Y%m%dT%H%M%SZ)

mkdir -p "$backup_dir"
cd "$deploy_dir"
docker compose -p ai-short-drama exec -T db \
  pg_dump -U mooncut -d mooncut -Fc > "$backup_dir/database-$timestamp.dump"
find "$backup_dir" -type f -name 'database-*.dump' -mtime +6 -delete
