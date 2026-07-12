#!/usr/bin/env bash
# seed-dev.sh — bootstrap a local dev org, user, API key, and credit balance.
# Idempotent: re-running just refreshes the credits and key.
#
# Talks to the Python backend's admin API. Requires the backend to be running
# (BACKEND_HTTP_PORT, default 8000) and an admin token from .env.

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-dev-admin-token}"
ORG_NAME="${SEED_ORG_NAME:-Dev Org}"
USER_EMAIL="${SEED_USER_EMAIL:-dev@openrouter.local}"
INITIAL_CREDITS="${SEED_CREDITS:-1000}"

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "[seed] missing dependency: $1" >&2; exit 1; }
}

require curl
require jq

post() {
  local path="$1" body="$2"
  curl -fsS -X POST "$BACKEND_URL$path" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H 'Content-Type: application/json' \
    -d "$body"
}

echo "[seed] backend URL: $BACKEND_URL"

if ! curl -fsS "$BACKEND_URL/health" >/dev/null; then
  echo "[seed] backend is not reachable. Run 'make dev-backend' first." >&2
  exit 1
fi

echo "[seed] creating org '$ORG_NAME'..."
ORG_RESP=$(post "/admin/orgs" "{\"name\":\"$ORG_NAME\"}")
ORG_ID=$(echo "$ORG_RESP" | jq -r '.id')
echo "[seed]   org_id=$ORG_ID"

echo "[seed] creating user '$USER_EMAIL'..."
USER_RESP=$(post "/admin/users" "{\"email\":\"$USER_EMAIL\",\"org_id\":\"$ORG_ID\"}")
USER_ID=$(echo "$USER_RESP" | jq -r '.id')
echo "[seed]   user_id=$USER_ID"

echo "[seed] minting API key..."
KEY_RESP=$(post "/admin/keys" "{\"org_id\":\"$ORG_ID\",\"name\":\"dev-key\"}")
KEY_PLAINTEXT=$(echo "$KEY_RESP" | jq -r '.plaintext')
echo "[seed]   API key (plaintext, shown ONCE): $KEY_PLAINTEXT"

echo "[seed] topping up $INITIAL_CREDITS credits..."
post "/admin/billing/credits" \
  "{\"org_id\":\"$ORG_ID\",\"amount\":$INITIAL_CREDITS,\"note\":\"seed-dev\"}" >/dev/null

cat <<EOF

[seed] done. Try:
  curl -H "Authorization: Bearer $KEY_PLAINTEXT" \\
       http://localhost:8080/api/v1/models

EOF
