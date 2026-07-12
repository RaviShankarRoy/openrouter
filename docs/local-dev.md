# Local Development

The full setup for running the gateway, backend, frontend, and supporting
infra on a laptop. Referenced from [ARCHITECTURE.md §6](../ARCHITECTURE.md#6-local-development).

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Go | 1.24+ | `go version` |
| Python | 3.12+ | The mock providers and backend both pin 3.12 |
| Node.js | 20+ | Next.js 15 + the CLI |
| Docker + Compose | v2 | Postgres, Redis, NATS, MinIO |
| `make` | any | Cross-stack orchestration |
| `tmux` | any | Optional but `scripts/dev-all.sh` uses it |
| `mkcert` | any | Optional — `scripts/generate-keys.sh` falls back to openssl |
| `k6` | 0.55+ | Load tests |
| `psql` | 14+ | `scripts/reset-db.sh` |
| `jq` | any | `scripts/seed-dev.sh` |

## First-time setup

```bash
git clone ... && cd normal
cp .env.example .env                      # adjust values; defaults work for local
docker compose up -d                      # postgres, redis, nats, minio
bash scripts/reset-db.sh                  # create DB and run migrations
bash scripts/generate-keys.sh             # local TLS for *.openrouter.local
make install                              # delegates to per-stack install targets
```

## Day-to-day

There are **three supported paths** for starting the full stack. Pick one — they share env vars and ports so you can switch without confusion.

### Path A — Native, single command (recommended for fast iteration)

Reads [Procfile.dev](../Procfile.dev). Each line is one process; Ctrl+C stops them all.

```bash
make up-native            # delegates to overmind / honcho / foreman, whichever is on PATH
```

Install one of these once:

```bash
brew install overmind     # macOS, recommended (tmux-backed, attach to any process)
pip install honcho        # cross-platform, pure Python
gem install foreman       # Ruby, original Heroku tool
```

Pros: millisecond hot reload, normal terminal, easy debugger attach.
Cons: you need Go 1.24, Python 3.12, Node 20 on your machine.

### Path B — Containers, single command (zero toolchain install)

Reads [docker-compose.dev.yml](../docker-compose.dev.yml) on top of [docker-compose.yml](../docker-compose.yml). Bind-mounts source for hot reload; caches deps in named volumes.

```bash
make up-docker            # docker compose -f docker-compose.yml -f docker-compose.dev.yml up
make down-docker          # stop everything, keep volume caches
make down-docker-clean    # stop and wipe caches (forces full reinstall)
```

Pros: only requires Docker, identical on every machine, near-prod parity.
Cons: first boot is slow (~3-5 min to install deps), mac filesystem perf via bind-mount can be sluggish.

### Path C — tmux multi-pane (original)

```bash
bash scripts/dev-all.sh   # one tmux session, one window per service
```

Pros: each service in its own pane, survive terminal close (`tmux detach`).
Cons: requires tmux, not portable to Windows.

### Or run services individually

```bash
make dev-gateway                          # gateway-go + air hot reload
make dev-backend                          # uvicorn --reload
make dev-frontend                         # next dev
cd tools/mock-providers && make dev       # uvicorn on :9100
```

Verify everything is healthy:

```bash
bash scripts/verify-stack.sh
```

Seed a test org + key + credits:

```bash
bash scripts/seed-dev.sh
# Prints an API key — use it as Authorization: Bearer ...
```

## Service ports

| Service | Port | URL |
|---|---|---|
| Go gateway | 8080 | http://localhost:8080 |
| Go gateway metrics | 9091 | http://localhost:9091/metrics |
| Python backend | 8000 | http://localhost:8000 |
| Python backend gRPC | 50051 | (used by gateway) |
| Python backend metrics | 9092 | http://localhost:9092/metrics |
| Frontend | 3000 | http://localhost:3000 |
| Mock providers | 9100 | http://localhost:9100 |
| Postgres | 5432 | `psql -h localhost -U openrouter` |
| Redis | 6379 | `redis-cli` |
| NATS | 4222 | |
| MinIO | 9000 | http://localhost:9000 (console: 9001) |
| Prometheus (optional) | 9090 | |
| Grafana (optional) | 3001 | |

## Adding an open-weight model (Gemma 4, Qwen, etc.)

The gateway already ships with Gemma 4 and Qwen 3.x catalog entries pointing
at Together and Fireworks. To exercise them locally:

```bash
# Add provider keys to .env (sign up at api.together.xyz or fireworks.ai)
echo "TOGETHER_API_KEY=tok-..." >> .env
echo "FIREWORKS_API_KEY=fw-..." >> .env

# Try a request
curl -N http://localhost:8080/api/v1/chat/completions \
  -H "Authorization: Bearer $DEV_KEY" \
  -d '{"model":"qwen/qwen3.6-27b","stream":true,
       "messages":[{"role":"user","content":"hi"}]}'
```

For a no-cost path, use the bundled Ollama service:

```bash
docker compose up -d ollama
docker exec or-ollama ollama pull gemma4:e4b
# Then call model: "google/gemma-4-e4b"
```

Full walkthrough + cheat sheet for adding a *new* model:
[ADDING_NEW_MODELS_GUIDE.md](ADDING_NEW_MODELS_GUIDE.md).

## Pointing the gateway at the mocks

In a test profile, swap the upstream URLs in `gateway-go/configs/providers.yaml`:

```yaml
providers:
  openai:
    base_url: http://localhost:9100/v1
  anthropic:
    base_url: http://localhost:9100
  google:
    base_url: http://localhost:9100/v1beta
```

`SIGHUP` the gateway to pick up the change (GW-015).

## Common troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `connection refused` on :8080 | Gateway isn't running | `make dev-gateway` |
| 401 on /chat/completions | Key not in Redis cache | `bash scripts/seed-dev.sh` |
| Stuck migrations | Local DB drifted | `bash scripts/reset-db.sh` |
| Mock providers return 429 | Stale scenario override | `curl -X POST :9100/control/reset` |
| Slow gateway in load tests | Postgres in the request path | Check Redis cache hit rate |

## Running the test suites

```bash
make test                                 # all stacks
cd tools/mock-providers && make test      # mock provider unit tests
cd tools/load-tests && make smoke         # k6 sanity check
```
