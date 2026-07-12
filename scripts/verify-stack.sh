#!/usr/bin/env bash
# verify-stack.sh — health-check every service. Returns non-zero if anything
# is unreachable so it can be wired into CI smoke jobs.

set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
MOCK_URL="${MOCK_URL:-http://localhost:9100}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[0;33m'
RESET=$'\033[0m'

failures=0

check_http() {
  local name="$1" url="$2"
  if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
    printf "  %s%-22s%s OK    %s\n" "$GREEN" "$name" "$RESET" "$url"
  else
    printf "  %s%-22s%s DOWN  %s\n" "$RED" "$name" "$RESET" "$url"
    failures=$((failures + 1))
  fi
}

check_tcp() {
  local name="$1" host="$2" port="$3"
  if (echo > "/dev/tcp/$host/$port") >/dev/null 2>&1; then
    printf "  %s%-22s%s OK    %s:%s\n" "$GREEN" "$name" "$RESET" "$host" "$port"
  else
    printf "  %s%-22s%s DOWN  %s:%s\n" "$RED" "$name" "$RESET" "$host" "$port"
    failures=$((failures + 1))
  fi
}

echo "Stack health check"
echo "------------------"
check_http "gateway-go"     "$GATEWAY_URL/health"
check_http "backend-python" "$BACKEND_URL/health"
check_http "frontend-web"   "$FRONTEND_URL"
check_http "mock-providers" "$MOCK_URL/health"
check_tcp  "postgres"       "$POSTGRES_HOST" "$POSTGRES_PORT"
check_tcp  "redis"          "$REDIS_HOST"    "$REDIS_PORT"

echo
if [[ $failures -gt 0 ]]; then
  printf "%s%d service(s) DOWN%s\n" "$RED" "$failures" "$RESET"
  exit 1
fi
printf "%sAll services OK%s\n" "$GREEN" "$RESET"

# Hint about optional infra so a missing observability stack is informational,
# not noise.
if ! curl -fsS --max-time 1 "http://localhost:9090" >/dev/null 2>&1; then
  printf "  %sinfo%s prometheus not running on :9090 (optional)\n" "$YELLOW" "$RESET"
fi
