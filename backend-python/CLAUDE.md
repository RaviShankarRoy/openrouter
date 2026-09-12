# backend-python — Warm-Path Business Logic

FastAPI + SQLAlchemy 2.0 async + Celery + Redis + NATS. DDD layout. Owns the Postgres database exclusively (Go gateway never opens SQL connections — [ARCHITECTURE.md §2.6](../ARCHITECTURE.md#26-database)).

## Commands

```bash
uv sync                                # install deps from uv.lock
uv run pytest -q                       # unit tests (46 currently pass in ~8s)
uv run pytest --cov=app                # with coverage
uv run ruff check app/                 # lint
uv run mypy app/                       # type check
uv run alembic upgrade head            # apply migrations
uv run alembic revision -m "<msg>" --autogenerate    # new migration
uv run uvicorn app.main:app --reload --port 8000     # dev server (HTTP)
uv run python -m app.grpc_main                       # dev gRPC server (port 50051)
uv run celery -A app.repository.celery_app worker --loglevel=info     # worker
make test                              # delegates to pytest
make dev                               # delegates to uvicorn --reload
```

**Critical:** the Celery module path is `app.repository.celery_app` (file, not package). The k8s worker manifest currently references `app.repository.celery.app` — that's a bug.

## Layout (Layered N-Tier)

```
app/
├── main.py                 # FastAPI app factory, lifespan, CORS
├── grpc_main.py            # gRPC server entry (for gateway-go auth lookups)
├── api/
│   ├── routes/             # HTTP routes: auth, oauth, billing, models, admin, webhooks
│   └── decorators.py       # @audit_log, @require_permission
├── service/                # ── business tier: use cases (warm path)
│   ├── auth_service.py     # also billing_service.py, oauth_service.py
│   ├── domain/             # entities, value objects, errors (DomainError hierarchy),
│   │                       #   repositories.py = the Port interfaces
│   ├── routing/strategies/ # pluggable routing algorithms
│   ├── guardrails/         # pipeline.py (Phase 3, mostly skeleton)
│   ├── mcp/                # MCP server/client (Phase 4 stubs)
│   └── uow.py              # UnitOfWork port
├── repository/             # ── data tier: implements the domain Ports
│   ├── api_keys.py         # the aggregate repositories sit at the top level:
│   ├── credits.py          #   credits, organizations, usage, users, video_jobs
│   ├── database.py         # asyncpg pool init
│   ├── redis_client.py     # redis-py async
│   ├── celery_app.py       # Celery app — note path
│   ├── uow.py              # SqlUnitOfWork (async with uow:)
│   ├── orm_models.py       # SQLAlchemy 2.0 declarative
│   ├── providers/          # base.py + openai.py + anthropic.py + google.py
│   ├── billing/            # stripe_client.py (Phase 2, interface complete)
│   ├── grpc/               # server.py for AuthServicer + gen/ (gitignored)
│   ├── events/bus.py       # NATS publisher
│   └── tasks/              # Celery: video.py, webhooks.py, billing.py
├── shared/                 # ── cross-cutting, imported by any tier
│   ├── config.py           # pydantic-settings
│   ├── logging.py          # structlog JSON formatter
│   ├── tracing.py          # OpenTelemetry setup
│   └── security.py         # argon2id (m=64MB,t=3,p=4), JWT, password hashing
└── tests/                  # pytest + pytest-asyncio + testcontainers

**Dependency rule: imports point downward only.** `api → service → repository`, and any
tier may import `shared`. The service tier reaches the repository tier through the Port
interfaces in `service/domain/repositories.py`, never by importing `app.repository`.
alembic/
├── env.py
└── versions/               # forward-only migrations
```

## Key Patterns

- **Async-by-default.** FastAPI + asyncpg + httpx. Sync exceptions: tiktoken token counting, Celery task bodies.
- **Repository + Unit of Work.** `async with uow:` opens a session AND a transaction. Don't call `with_for_update()` outside `async with uow.begin()` — it silently becomes a plain SELECT.
- **Dependency Injection** via FastAPI `Depends()`. No third-party DI lib.
- **Pub/Sub** via NATS for fire-and-forget metering events. Celery for durable jobs.
- **Provider adapters** subclass `app/repository/providers/base.py:ProviderAdapter` — implement `chat_completion`, `embed`, `stream_chat`.
- **Audit logging** via `@audit_log(action="...", target_id_arg="...")` decorator on admin routes.

## Database

- Postgres 16 + pgvector extension.
- Alembic forward-only — **no down migrations in prod** ([ARCHITECTURE.md §2.6](../ARCHITECTURE.md#26-database)).
- Connection pool size: `cpu_count * 2 + reserve`.
- Lookup hashes for API keys: HMAC-SHA-256 with SECRET_KEY (consider — currently plain SHA-256 in `core/security.py`).

## Logging

`structlog` JSON output. The `_SENSITIVE_KEYS` redactor in `core/logging.py` only matches top-level keys — nested dicts and free-text fields containing `sk-...` are NOT scrubbed. When logging request payloads, scrub manually or extend the processor.

## Testing

- Unit tests: `pytest -q` runs in ~8s.
- Integration: `pytest tests/integration/` uses `testcontainers` for Postgres + Redis (slower).
- Fixtures live in `tests/conftest.py`.
- 3 DeprecationWarnings from `testcontainers` package — not project code; ignore.

## Known Issues (from audit)

- `auth_service.revoke_key` doesn't check `key.org_id == requesting_org_id` — BOLA across tenants.
- `stripe_client._credit_org` is not idempotent on Stripe webhook redeliveries — needs `processed_stripe_events` dedupe table.
- `oauth_service.exchange` doesn't verify Google `email_verified` or token audience — account takeover risk.
- `core/config.py` has a default `SECRET_KEY` for HS256 JWT — add startup assertion: never the default in `environment=="prod"`.
- `_install_sighup_handler` uses deprecated `asyncio.get_event_loop()` — switch to `get_running_loop()`.
- `tasks/video.py` returns fake provider job IDs — Phase 3 stub.
- `tasks/webhooks.py` reuses `SECRET_KEY` as HMAC key — split into `WEBHOOK_SIGNING_KEY`.

## Dependencies

Managed by `uv` (uv.lock locked). Key: `fastapi`, `sqlalchemy>=2.0`, `asyncpg`, `celery`, `redis[hiredis]`, `httpx`, `stripe`, `openai`, `anthropic`, `google-genai`, `tiktoken`, `prometheus-client`, `opentelemetry-api`, `structlog`, `pydantic-settings`, `passlib[argon2]`.
