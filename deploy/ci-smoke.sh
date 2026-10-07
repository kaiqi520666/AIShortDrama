#!/usr/bin/env bash
set -euo pipefail

: "${BACKEND_IMAGE:?Set the backend image built for this commit}"
: "${FRONTEND_IMAGE:?Set the frontend image built for this commit}"

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
smoke_dir="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/aisd-ci-smoke.XXXXXX")"
project="aisd-ci-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}-$$"
frontend_port="$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
compose=(docker compose --project-name "$project" --project-directory "$smoke_dir"
    --env-file "$smoke_dir/.env" --file "$smoke_dir/docker-compose.yml"
    --file "$smoke_dir/ci-volumes.yml")

cleanup() {
    result=$?
    trap - EXIT
    if (( result != 0 )); then
        "${compose[@]}" ps --all || true
        "${compose[@]}" logs --no-color --tail 100 || true
    fi
    "${compose[@]}" down --volumes --remove-orphans || true
    rm -rf -- "$smoke_dir"
    exit "$result"
}
trap cleanup EXIT

# Isolated Compose directory keeps both generated settings and DB files out of deploy/.
cp "$repo_root/deploy/docker-compose.yml" "$smoke_dir/docker-compose.yml"
cat > "$smoke_dir/ci-volumes.yml" <<'EOF'
services:
  db:
    volumes:
      - ci_postgres:/var/lib/postgresql/data
  redis:
    volumes:
      - ci_redis:/data
volumes:
  ci_postgres:
  ci_redis:
EOF
cat > "$smoke_dir/.env" <<EOF
BACKEND_IMAGE=$BACKEND_IMAGE
FRONTEND_IMAGE=$FRONTEND_IMAGE
FRONTEND_PORT=$frontend_port
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://aisd_ci:ci-only-password@db:5432/aisd_ci
REDIS_URL=redis://redis:6379/0
REDIS_PREFIX=$project
SECRET_KEY=ci-only-secret-not-for-production
POSTGRES_USER=aisd_ci
POSTGRES_PASSWORD=ci-only-password
POSTGRES_DB=aisd_ci
EOF

"${compose[@]}" config --quiet
"${compose[@]}" up --detach --wait --wait-timeout 90 db redis
"${compose[@]}" run --rm --no-deps migrate
"${compose[@]}" run --rm --no-deps migrate python scripts/check_migrations.py
"${compose[@]}" up --detach --no-deps --wait --wait-timeout 90 backend worker
"${compose[@]}" up --detach --no-deps --wait --wait-timeout 90 frontend

for attempt in {1..20}; do
    if "${compose[@]}" exec --no-TTY worker arq --check app.workers.settings.WorkerSettings; then
        break
    fi
    if (( attempt == 20 )); then
        echo "Worker did not produce a healthy ARQ heartbeat" >&2
        exit 1
    fi
    sleep 2
done

frontend_address="$("${compose[@]}" port frontend 80)"
curl --fail --silent --show-error --retry 5 --retry-connrefused --max-time 10 \
    "http://$frontend_address/" > /dev/null
response="$(curl --fail --silent --show-error --max-time 10 "http://$frontend_address/api/health")"
if ! grep -q '"status":"ok"' <<< "$response"; then
    echo "Frontend-to-backend health response was not healthy" >&2
    exit 1
fi

"${compose[@]}" ps
echo "Compose smoke passed: migrations, backend, worker heartbeat, frontend and proxy health"
