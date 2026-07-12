#!/usr/bin/env bash
# reset-db.sh — drop and recreate the dev database, then run migrations.
# Destructive on purpose. Refuses to run if POSTGRES_DSN points anywhere
# other than localhost.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DSN="${POSTGRES_DSN:-postgresql+asyncpg://openrouter:dev_only_password@localhost:5432/openrouter}"
DB_NAME="${POSTGRES_DB:-openrouter}"
DB_USER="${POSTGRES_USER:-openrouter}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
PSQL_DSN_ADMIN="${PSQL_DSN_ADMIN:-postgresql://$DB_USER:dev_only_password@$DB_HOST:$DB_PORT/postgres}"

# Refuse to wipe anything that is not local.
if [[ "$DSN" != *"@localhost"* && "$DSN" != *"@127.0.0.1"* && "$DSN" != *"@postgres"* ]]; then
  echo "[reset-db] refusing: POSTGRES_DSN does not look local: $DSN" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "[reset-db] psql is required" >&2
  exit 1
fi

echo "[reset-db] dropping database '$DB_NAME'..."
PGPASSWORD=dev_only_password psql "$PSQL_DSN_ADMIN" -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$DB_NAME";
CREATE DATABASE "$DB_NAME" OWNER "$DB_USER";
SQL

echo "[reset-db] running Alembic migrations..."
cd "$ROOT_DIR/backend-python"
if command -v alembic >/dev/null 2>&1; then
  alembic upgrade head
else
  echo "[reset-db] alembic not on PATH — falling back to 'make migrate'"
  make migrate
fi

echo "[reset-db] done. Database '$DB_NAME' is at the head migration."
