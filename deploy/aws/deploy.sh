#!/usr/bin/env bash
# deploy/aws/deploy.sh — build and (re)deploy the whole stack on the server.
#
# Run from anywhere inside the repo on the EC2 instance:
#   ./deploy/aws/deploy.sh            # pull latest code, build, migrate, start
#   ./deploy/aws/deploy.sh --no-pull  # deploy the code as-is (no git pull)
#
# Safe to re-run any time: compose only rebuilds what changed and only
# restarts containers whose image or config actually changed.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENVFILE="$ROOT/.env.aws"
COMPOSE=(docker compose -f "$ROOT/deploy/aws/docker-compose.aws.yml" --env-file "$ENVFILE")

# ---------- preflight ----------
if [ ! -f "$ENVFILE" ]; then
  echo "ERROR: $ENVFILE not found."
  echo "  cp deploy/aws/.env.aws.example .env.aws   # then edit it"
  exit 1
fi
if grep -q "CHANGE_ME" "$ENVFILE"; then
  echo "ERROR: .env.aws still contains CHANGE_ME placeholders."
  echo "  Generate real secrets with:  openssl rand -hex 32"
  exit 1
fi

# ---------- update code ----------
if [ "${1:-}" != "--no-pull" ] && git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  echo "==> Pulling latest code"
  git -C "$ROOT" pull --ff-only || echo "    (pull skipped — no upstream or local changes)"
fi

# ---------- build & start ----------
echo "==> Building images (first run takes ~10-15 min; later runs are cached)"
"${COMPOSE[@]}" build

echo "==> Starting the stack (migrations run automatically before the backend)"
"${COMPOSE[@]}" up -d

echo "==> Waiting 15s for services to settle"
sleep 15

# ---------- verify ----------
echo "==> Container status:"
"${COMPOSE[@]}" ps

DOMAIN="$(grep -E '^DOMAIN=' "$ENVFILE" | cut -d= -f2)"
echo
echo "==> Health checks (from inside the network):"
"${COMPOSE[@]}" exec -T gateway sh -c 'exit 0' 2>/dev/null \
  && echo "    gateway container: running" || echo "    gateway container: NOT RUNNING"
"${COMPOSE[@]}" exec -T backend curl -fsS http://localhost:8000/health >/dev/null 2>&1 \
  && echo "    backend /health:   OK" || echo "    backend /health:   FAILED (check: ${COMPOSE[*]} logs backend)"

echo
echo "================================================================"
echo " Once DNS points at this server, verify from your laptop:"
echo "   curl https://api.${DOMAIN}/health"
echo "   open https://app.${DOMAIN}"
echo
echo " Logs:    ${COMPOSE[*]} logs -f [service]"
echo " Stop:    ${COMPOSE[*]} down"
echo "================================================================"
