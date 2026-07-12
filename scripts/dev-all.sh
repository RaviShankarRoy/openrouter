#!/usr/bin/env bash
# dev-all.sh — start every service in a tmux session.
# Layout:
#   window 0: gateway (Go)         window 1: backend (FastAPI)
#   window 2: frontend (Next.js)   window 3: mock providers
#   window 4: celery worker        window 5: grpc server
# Detach with Ctrl-b d; reattach with `tmux attach -t openrouter`.

set -euo pipefail

SESSION="${TMUX_SESSION:-openrouter}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v tmux >/dev/null 2>&1; then
  cat >&2 <<EOF
[dev-all] tmux is not installed.

Install it:
  Debian/Ubuntu : sudo apt-get install tmux
  macOS         : brew install tmux

Or run each service manually in its own terminal:
  cd $ROOT_DIR/gateway-go        && make dev
  cd $ROOT_DIR/backend-python    && make dev
  cd $ROOT_DIR/frontend-web      && npm run dev
  cd $ROOT_DIR/tools/mock-providers && make dev
  cd $ROOT_DIR/backend-python    && make worker
EOF
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[dev-all] session '$SESSION' already exists — attaching."
  exec tmux attach -t "$SESSION"
fi

echo "[dev-all] starting tmux session '$SESSION' from $ROOT_DIR"

tmux new-session -d -s "$SESSION" -n gateway -c "$ROOT_DIR/gateway-go" \
  "make dev || (echo 'gateway exited; press enter to close' && read -r)"

tmux new-window -t "$SESSION:" -n backend -c "$ROOT_DIR/backend-python" \
  "make dev || (echo 'backend exited; press enter to close' && read -r)"

tmux new-window -t "$SESSION:" -n frontend -c "$ROOT_DIR/frontend-web" \
  "(npm run dev || echo 'frontend not yet implemented'); read -r"

tmux new-window -t "$SESSION:" -n mock-providers -c "$ROOT_DIR/tools/mock-providers" \
  "make dev || (echo 'mock providers exited; press enter to close' && read -r)"

tmux new-window -t "$SESSION:" -n celery -c "$ROOT_DIR/backend-python" \
  "(make worker || echo 'celery worker target missing'); read -r"

tmux new-window -t "$SESSION:" -n grpc -c "$ROOT_DIR/backend-python" \
  "make grpc-serve || (echo 'grpc-serve exited; press enter to close' && read -r)"

tmux select-window -t "$SESSION:gateway"
exec tmux attach -t "$SESSION"
