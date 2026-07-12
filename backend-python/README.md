# backend-python

OpenRouter backend service. FastAPI + SQLAlchemy 2.0 (async) + Celery + gRPC. Owns the database, billing, ML, MCP, and the warm path that the Go gateway delegates to (key validation, "openrouter/auto" routing, semantic cache, video/image/audio jobs).

See the monorepo [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) for the cross-stack picture and DRD requirement traceability.

## Layout

```
app/
  api/                       — FastAPI driving adapter
    routes/                  —   one router per bounded context
    middleware.py            —   request_id, structured logs, OTel
    errors.py                —   DomainError → OpenAI envelope
    dependencies.py          —   FastAPI Depends() factories
    decorators.py            —   @audit_log, @require_permission
  application/               — use cases (services), guardrails, routing, MCP
    services/                —   AuthService, BillingService
    guardrails/              —   pipeline + guards (DRD §14.3)
    routing/strategies.py    —   cost / latency / quality
    mcp/                     —   server + client + tool registry (Phase 4)
  domain/                    — entities, value objects, errors, repository ports
  infrastructure/            — driven adapters
    repositories/            —   SQLAlchemy implementations
    providers/               —   provider adapters (openai, anthropic, ...)
    billing/                 —   Stripe, cached pricing repo
    storage/                 —   S3 / MinIO (aioboto3)
    tasks/                   —   Celery tasks (video, webhooks, billing)
    grpc/                    —   gRPC server (PY-019)
    events/                  —   NATS JetStream pub/sub
    database.py              —   async engine + session factory
    uow.py                   —   SqlUnitOfWork
    redis_client.py          —   shared Redis client
    celery_app.py            —   Celery wiring
  core/                      — config, logging, security, tracing
alembic/                     — migrations (forward-only in prod)
tests/
  unit/                      —   in-memory fakes, fast
  integration/               —   testcontainers Postgres + Redis, respx for HTTP
```

## Design patterns in use

| Pattern | Where | Reason |
|---|---|---|
| Domain-Driven Design | `app/domain/` + `app/application/` | Map to business capabilities |
| Repository | `app/infrastructure/repositories/` | Hide SQLAlchemy from use cases |
| Unit of Work | `app/infrastructure/uow.py` | One transaction per use case |
| Service Layer | `app/application/services/` | Thin orchestration over the domain |
| Adapter | `app/infrastructure/providers/`, `storage/`, `billing/` | Translate to/from external APIs |
| Factory + Registry | `app/infrastructure/providers/registry.py` | Plugin architecture for new providers |
| Strategy | `app/application/routing/strategies.py` | Cost/latency/quality interchangeable |
| Pipeline / Chain of Responsibility | `app/application/guardrails/pipeline.py` | DRD §14.3 |
| Decorator | `app/api/decorators.py` (`@audit_log`, `@require_permission`) | Cross-cutting concerns |
| Dependency Injection | FastAPI `Depends()` (`app/api/dependencies.py`) | Built-in, no extra DI lib |
| Pub/Sub | `app/infrastructure/events/bus.py` | Decouple metering from request path |

## Running locally

Bring up Postgres, Redis, NATS, MinIO via the root `docker-compose.yml`:

```bash
cd ..
docker-compose up -d
```

Install deps and apply migrations:

```bash
make install
make migrate
```

Run the FastAPI app with auto-reload:

```bash
make dev          # uvicorn on :8000
```

In another terminal, run the Celery worker for async jobs:

```bash
make worker
```

The gRPC server boots inside the FastAPI process when `app.infrastructure.grpc.gen.*` stubs are present (run `make proto` from the monorepo root once codegen is wired).

## Tests

```bash
make test            # unit + integration (testcontainers)
make test-unit       # fast — pure Python, in-memory fakes
make test-integration  # spins up Postgres + Redis containers
make lint            # ruff + mypy
```

Unit tests do not need Docker. Integration tests skip themselves if `testcontainers` isn't installed.

## Configuration

All config is environment-driven, validated at startup by `app/core/config.py` (`pydantic-settings`). See `../.env.example` for every variable and its default. Secrets are never read from files at request time — they're loaded once into a frozen `Settings` singleton.

## Phase status

This repo implements Phase 1 in full and Phase 2-4 as interface-stable scaffolding. Check `DEVELOPMENT_PLAN.md` §4 for the per-phase deliverables and the per-file `# Phase-N` comments for what needs filling in next.
