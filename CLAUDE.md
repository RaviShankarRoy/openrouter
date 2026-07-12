# Claude Code Context — OpenRouter-Equivalent AI Gateway

Polyglot scaffold of an OpenRouter-style AI Gateway. 4 services + shared contracts + infra.

> **This is a scaffold, not a finished product.** See [DEVELOPMENT_PLAN.md §1](DEVELOPMENT_PLAN.md) — Tier A/B/C delivered, Tier D (full Stripe, MCP server, ML guardrails, semantic cache, 60 provider adapters) is intentionally stubbed with interfaces + TODOs mapped to DRD requirement IDs. Empty function bodies in Phase 2-4 modules are by design.

## Repo Layout

| Path | Stack | Status |
|---|---|---|
| [gateway-go/](gateway-go/) | Go 1.24 reverse proxy (hot path) | Phase 1 implemented |
| [backend-python/](backend-python/) | FastAPI + SQLAlchemy 2.0 async + Celery | Phase 1 implemented; Stripe/Celery/guardrails stubbed |
| [frontend-web/](frontend-web/) | Next.js 15 App Router + React 19 | Phase 1 implemented; playground partial |
| [cli/](cli/) | Node 20 + TypeScript + commander | Phase 4 stubs |
| [shared/](shared/) | gRPC `.proto` + OpenAPI canonical spec | — |
| [infrastructure/](infrastructure/) | k8s base + overlays, Helm chart, Terraform | — |
| [tools/](tools/) | Mock provider server, k6 load tests | — |
| [docs/](docs/) | ADRs, runbooks, requirements traceability | — |

## Commands (root)

```bash
make help               # list all targets
make check-tools        # verify go/python/node/docker installed
make build              # build all 4 stacks
make test               # test-go + test-py + test-web (no test-cli wired)
make lint               # lint all stacks
make docker             # build all images
make dev-all            # all services via tmux
make migrate            # alembic upgrade head (backend-python)
make load-test          # k6 against local gateway
```

Per-service Make targets live in each service's `Makefile`; root just dispatches.

## Local Dev Bring-up

```bash
docker-compose up -d                # postgres+pgvector, redis, nats, minio
make migrate                        # apply alembic migrations
make dev-all                        # OR run each service separately
curl http://localhost:8080/health   # gateway health check
```

`docker-compose.observability.yml` is a separate file for Prometheus + Grafana + Loki + Tempo + Promtail — don't conflate with the deps compose.

## Cross-Cutting Conventions

Every service follows [ARCHITECTURE.md §2](ARCHITECTURE.md#2-cross-cutting-conventions):

- **Config:** env vars validated at startup. Go = `koanf`, Python = `pydantic-settings`, TS = `zod`.
- **Logging:** structured JSON to stdout. Go = `slog`, Python = `structlog`, TS = `pino`. Required fields: `timestamp,level,service,version,trace_id,span_id,request_id`. **Never log raw API keys, prompts, or PII.**
- **Metrics:** Prometheus `/metrics` on each service. Naming: `{service}_{subsystem}_{metric}_{unit}`. Never label by `user_id` or `request_id`.
- **Tracing:** OpenTelemetry OTLP/gRPC to Tempo. Sampling: 100% errors, 1% success. W3C `traceparent` propagation.
- **Errors:** OpenAI-compatible envelope: `{"error":{"message","type","code","param"}}`.

## Architectural Non-Negotiables

1. **Go gateway does NOT open SQL connections.** Python backend owns the DB exclusively ([ARCHITECTURE.md §2.6](ARCHITECTURE.md#26-database)). If you reach for `database/sql` in `gateway-go/`, stop.
2. **Gateway ↔ backend is gRPC.** Proto definitions in `shared/proto/`. HTTP/JSON only for admin tooling ([DEVELOPMENT_PLAN.md §7](DEVELOPMENT_PLAN.md) decision #2).
3. **Python uses `asyncpg`, NOT psycopg3** (LGPL avoidance — [DEVELOPMENT_PLAN.md §7](DEVELOPMENT_PLAN.md) risk #4).
4. **No logging on the gateway hot path.** Usage events emit to NATS subject `gateway.usage` for async metering.
5. **Frontend default = React Server Components.** `'use client'` only where interactivity needed.

## Known Landmines

- **Celery module path:** k8s manifests must reference `app.infrastructure.celery_app` (NOT `app.infrastructure.celery.app`). The worker manifest at [infrastructure/kubernetes/base/backend-celery-worker/deployment.yaml](infrastructure/kubernetes/base/backend-celery-worker/deployment.yaml) currently has this bug and crash-loops.
- **`.env` contains a real Google OAuth client secret** (`GOCSPX-...`). Treat as a leaked credential — rotate before any push. Use `.env.example` for new clones.
- **CORS in `backend-python/app/main.py`** uses `allow_credentials=True` + `allow_methods=["*"]` + `allow_headers=["*"]`. Don't add `"*"` to `CORS_ORIGINS` in prod — FastAPI permits it but the combo is XSRF-shaped.
- **Rate limiter fails open** on Redis errors ([gateway-go/internal/middleware/ratelimit.go:29](gateway-go/internal/middleware/ratelimit.go#L29)). When working on auth/limit paths, prefer fail-closed.
- **JWT uses HS256 with a default `SECRET_KEY="dev_only_change_in_prod_min_32_chars_long"`** ([backend-python/app/core/config.py](backend-python/app/core/config.py)). Don't ship without an env override.
- **Routes match the OpenAPI spec under `/api/v1/...`**, but some frontend calls hit `/v1/...` directly — verify prefix when wiring new endpoints.

## Where to Find Things

- **DRD (source of truth for requirements):** [openrouter-drd-go-python-typescript.md](openrouter-drd-go-python-typescript.md) — 77k file
- **Requirement → code mapping:** [DEVELOPMENT_PLAN.md §3](DEVELOPMENT_PLAN.md#3-requirement-traceability)
- **Runtime topology + request flow:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **ADRs:** [docs/adr/](docs/adr/)
- **Runbooks:** [docs/runbooks/](docs/runbooks/)
- **Local dev:** [docs/local-dev.md](docs/local-dev.md)
- **Onboarding:** [docs/onboarding.md](docs/onboarding.md)

## Definition of Done (per service)

See [DEVELOPMENT_PLAN.md §8](DEVELOPMENT_PLAN.md#8-definition-of-done-per-service). Highlights: >80% unit coverage, integration tests against testcontainers, k6 load test in CI gate, runbook in `docs/runbooks/`, Helm values documented, Trivy CRITICAL=0.
