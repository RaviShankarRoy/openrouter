# Development Plan — OpenRouter-Equivalent AI Gateway

**Source DRD:** [openrouter-drd-go-python-typescript.md](openrouter-drd-go-python-typescript.md)
**Plan version:** 1.0 — 2026-04-26
**Architecture:** Polyglot microservices — Go (hot path) + Python (warm path) + TypeScript (DX)

---

## 1. Scope Reality Check

The DRD specifies 21 modules requiring 6–14 engineers across 12 months. This plan delivers:

| Tier | What it contains | Status |
|---|---|---|
| **Tier A — Production scaffolding** | Monorepo layout, Dockerfiles, k8s manifests, Helm charts, CI/CD, IaC stubs, observability bootstrapping | Delivered in this scaffold |
| **Tier B — Foundational code with patterns** | Hexagonal Go gateway with middleware chain, circuit breaker, provider adapter interface; Python FastAPI app with DDD layout, repository pattern, guardrail pipeline; Next.js 15 App Router with feature-sliced design | Delivered in this scaffold |
| **Tier C — Phase 1 wired endpoints** | OpenAI-compatible `/v1/chat/completions` proxy, OpenAI + Anthropic adapters, API key auth via Redis, rate limiting, exact-match cache | Delivered in this scaffold |
| **Tier D — Full business logic** | Stripe billing, Celery video pipeline, MCP gateway, semantic cache, full guardrails ML inference, all 60 provider adapters | **NOT delivered** — clearly stubbed with interfaces and TODOs mapped to DRD requirement IDs |

Anything claiming "production ready" for Tier D in a single delivery would be dishonest. The scaffold is structured so Tier D can be filled in incrementally without re-architecting.

---

## 2. Architectural Decisions

### 2.1 Service Boundaries

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENTS (SDKs, browsers, CLIs)                               │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTPS
┌─────────────────────────────▼────────────────────────────────┐
│  EDGE: Cloudflare (CDN + WAF + DDoS)                          │
└─────────────────────────────┬────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────┐
│  GO GATEWAY (gateway-go) — Hot path, < 15µs overhead          │
│  Hexagonal architecture — Ports & Adapters                    │
│  Patterns: Strategy, Chain of Responsibility, Circuit Breaker,│
│            Object Pool, Adapter, Factory                      │
└──┬──────────────────────────────┬──────────────────────────┬─┘
   │ HTTP→Provider                │ gRPC internal             │ pub/sub
   ▼                              ▼                           ▼
┌──────────┐  ┌─────────────────────────────────────┐  ┌─────────────┐
│LLM       │  │ PYTHON BACKEND (backend-python)     │  │ NATS /      │
│Providers │  │ FastAPI + SQLAlchemy 2.0 + Celery   │  │ Redis       │
│(60+)     │  │ DDD + Clean Architecture            │  │ Streams     │
└──────────┘  │ Patterns: Repository, UoW, Service, │  └─────────────┘
              │           Adapter, Strategy,         │         │
              │           Pipeline, Pub/Sub,         │         │
              │           Decorator, Factory         │         ▼
              └─────┬───────────────────────────────┬┘  ┌─────────────┐
                    │ DB                            │   │ Celery      │
                    ▼                               ▼   │ workers     │
              ┌─────────────┐            ┌──────────────┴──────────────┐
              │ PostgreSQL  │            │ Redis 7 / Valkey            │
              │ 16 + pgvector│           │ rate limits, cache, sessions│
              └─────────────┘            └─────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  TYPESCRIPT FRONTEND (frontend-web)                           │
│  Next.js 15 App Router + RSC + Vercel AI SDK                  │
│  Feature-Sliced Design                                        │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Why this layout

| Decision | Rationale |
|---|---|
| **Monorepo, not polyrepo** | Shared protobuf contracts, atomic cross-stack changes, single CI pipeline. Trade-off: tooling complexity (we use `make` + per-stack tools, not Bazel — overkill for a 4-service setup) |
| **Go is stateless** | Auth metadata cached in Redis with TTL. Source of truth is PostgreSQL (Python-owned). This means a cold Redis is slow but never wrong |
| **Python never sees the hot path** | Go does its own routing for explicit `model:` requests (P0). Python only runs for `model: openrouter/auto` (P1) or for cache-miss embedding generation (P1) |
| **Async-by-default in Python** | FastAPI + SQLAlchemy 2.0 async + httpx async. Sync code is a deliberate exception (e.g. token counting with tiktoken) |
| **Next.js App Router (not Pages Router)** | RSC reduces client JS by 30-60% for the dashboard. Streaming UI for the playground via Vercel AI SDK |
| **NATS for events, Celery for jobs** | Two queues do two different things. NATS = fire-and-forget logging/metering events (lossy is acceptable). Celery = durable jobs (video gen, webhooks, billing aggregation) |
| **gRPC for Go↔Python** | Type-safe via shared `.proto` files. Falls back to HTTP/JSON for any service not yet on gRPC |

### 2.3 Design Patterns by Layer

#### Go Gateway (`gateway-go/`)

| Pattern | Where | Why |
|---|---|---|
| **Hexagonal Architecture** | `internal/` (domain) + `internal/adapters/` (driven) + `internal/transport/` (driving) | Test domain logic without HTTP/Redis/Postgres |
| **Chain of Responsibility** | `internal/middleware/chain.go` | Composable: logging → auth → ratelimit → cache → route → proxy |
| **Strategy** | `internal/router/strategies/` | Cost / latency / quality / geo are interchangeable algorithms |
| **Circuit Breaker** | `internal/circuitbreaker/` (wraps `sony/gobreaker`) | Stop hammering a dead provider |
| **Object Pool** | `internal/pool/` (`sync.Pool` for `[]byte` buffers) | Zero-alloc on hot path |
| **Adapter** | `internal/proxy/adapters/` | Each provider has its own request/response shape |
| **Factory** | `internal/proxy/factory.go` | Lazy provider client construction with config |
| **Observer** | `internal/health/watcher.go` | Health probes notify routing engine |
| **Functional Options** | `internal/server/options.go` | Idiomatic Go config pattern |

#### Python Backend (`backend-python/`)

| Pattern | Where | Why |
|---|---|---|
| **Domain-Driven Design** | `app/domain/` (entities, value objects), `app/application/` (use cases), `app/infrastructure/` (DB, Redis, HTTP) | Map to business capabilities, not CRUD |
| **Repository** | `app/infrastructure/repositories/` | Hide SQLAlchemy from use cases |
| **Unit of Work** | `app/infrastructure/uow.py` | Transactional boundaries explicit |
| **Service Layer** | `app/application/services/` | Use cases orchestrate repositories |
| **Adapter (Provider SDK)** | `app/infrastructure/providers/` | DRD §7.2 — already mandated |
| **Factory + Registry** | `app/infrastructure/providers/registry.py` | Plugin architecture for new providers |
| **Strategy** | `app/application/routing/strategies/` | Pluggable routing algorithms |
| **Pipeline / Chain of Responsibility** | `app/application/guardrails/pipeline.py` | DRD §14.3 — already shown |
| **Decorator** | `app/api/decorators.py` (`@audit_log`, `@require_permission`) | Cross-cutting concerns |
| **Dependency Injection** | FastAPI `Depends()` | Built-in, no third-party DI lib needed |
| **Pub/Sub** | `app/infrastructure/events/bus.py` | Decouple metering from request path |
| **Specification** | `app/domain/specifications.py` | Composable query predicates |

#### TypeScript Frontend (`frontend-web/`)

| Pattern | Where | Why |
|---|---|---|
| **Feature-Sliced Design** | `src/features/`, `src/entities/`, `src/widgets/`, `src/shared/` | Scales better than `components/` flat structure |
| **React Server Components** | `src/app/**/page.tsx` (default) | Less client JS, better SEO |
| **Client Components** | `'use client'` only where interactivity needed | Default to server |
| **Custom Hooks** | `src/shared/hooks/` | Encapsulate stateful logic |
| **Repository (API client)** | `src/shared/api/` | Generated from OpenAPI spec |
| **Provider/Context** | `src/shared/providers/` | Auth, theme, query client |
| **Compound Components** | `src/shared/ui/` (built on shadcn/ui) | Composable primitives |

---

## 3. Requirement Traceability

Each module's requirements map to a code path. Full mapping in [docs/requirements-traceability.md](docs/requirements-traceability.md). Highlights:

| DRD Req ID | Stack | Implementation path | Phase |
|---|---|---|---|
| GW-001 (OpenAI-compat) | Go | `gateway-go/internal/transport/http/handlers/chat.go` | 1 |
| GW-002 (SSE streaming) | Go | `gateway-go/internal/transport/http/streaming.go` | 1 |
| GW-005 (connection pooling) | Go | `gateway-go/internal/proxy/pool.go` | 1 |
| GW-013 (auth via Redis) | Go | `gateway-go/internal/middleware/auth.go` | 1 |
| GW-014 (rate limit) | Go | `gateway-go/internal/middleware/ratelimit.go` | 1 |
| PY-005 (provider adapter base) | Python | `backend-python/app/infrastructure/providers/base.py` | 1 |
| PY-007 (argon2id keys) | Python | `backend-python/app/application/services/auth_service.py` | 1 |
| PY-009 (RBAC) | Python | `backend-python/app/api/decorators.py` | 2 |
| PY-011 (Stripe) | Python | `backend-python/app/infrastructure/billing/stripe_client.py` | 2 |
| PY-014 (guardrails) | Python | `backend-python/app/application/guardrails/` | 3 |
| MCP-001..010 | Python | `backend-python/app/application/mcp/` | 4 |
| FE-003 (streaming chat) | TypeScript | `frontend-web/src/features/playground/` | 2 |
| FE-007 (request builder) | TypeScript | `frontend-web/src/features/code-snippets/` | 2 |
| CLI-001..005 | TypeScript | `cli/src/commands/` | 4 |

---

## 4. Phased Delivery (matches DRD §26)

### Phase 1 — Foundation (Months 1-3)
**Deliverables in this scaffold:** Go gateway skeleton with chain middleware, Python adapter base + 2 reference adapters (OpenAI, Anthropic), FastAPI app with auth + key issuance, Redis-backed rate limiter and exact cache, Postgres schema via Alembic, mock provider server, k8s manifests, GitHub Actions CI.

### Phase 2 — Billing & Dashboard (Months 3-5)
**To implement:** Stripe SDK wiring (interface stub provided), credit accounting service (domain models stubbed), OAuth2 via authlib (route stubs provided), audit log decorator (provided), Next.js dashboard pages (route skeletons provided).

### Phase 3 — Multimodal & Intelligence (Months 5-8)
**To implement:** Image/video/audio routes (URL contracts in OpenAPI spec), Celery worker for video jobs (Celery app initialized, task signatures stubbed), semantic cache (pgvector migration provided, embedder interface stubbed), guardrail pipeline (pipeline class provided, classifiers stubbed).

### Phase 4 — Agentic & Enterprise (Months 8-12)
**To implement:** MCP server/client (module skeleton provided), agent session tracking (domain entity provided), prompt versioning (entity + repo stubs), CLI tool (commander.js skeleton provided), Helm chart for self-hosted (provided).

---

## 5. Repository Layout

```
prac1/normal/
├── README.md
├── ARCHITECTURE.md                    # this scaffold's architecture overview
├── DEVELOPMENT_PLAN.md                # this file
├── Makefile                           # cross-stack orchestration
├── docker-compose.yml                 # local dev: postgres, redis, nats, minio
├── docker-compose.observability.yml   # prometheus, grafana, tempo, loki
├── .env.example                       # all env vars documented
├── .editorconfig
├── .gitignore
├── .github/workflows/                 # CI per stack + release
├── docs/                              # ADRs, API contracts, runbooks
├── shared/                            # cross-stack contracts
│   ├── proto/                         #   gRPC definitions
│   └── openapi/                       #   OpenAPI spec (canonical)
├── gateway-go/                        # Go gateway (DRD Module 1)
├── backend-python/                    # Python services (DRD Modules 2, 4-21)
├── frontend-web/                      # Next.js dashboard + portal (DRD Module 3)
├── cli/                               # @openrouter/cli (DRD §6.5)
├── infrastructure/
│   ├── kubernetes/                    # raw manifests + kustomize overlays
│   ├── helm/                          # production helm chart
│   └── terraform/                     # IaC (AWS reference)
└── tools/
    ├── mock-providers/                # DRD §23.2 mock provider server
    └── load-tests/                    # k6 scripts for NFR-005
```

---

## 6. Non-Functional Requirements — How Each Is Met

| NFR | Target | How |
|---|---|---|
| NFR-001 (99.95% uptime) | < 4.38h/yr down | Multi-region k8s, HPA, circuit breaker, graceful degradation to cache |
| NFR-002 (<15µs gateway P99) | 5K RPS | Go + `fasthttp` evaluated, `sync.Pool` buffers, no logging on hot path (async via NATS), Redis pipelined lookups |
| NFR-003 (<200ms TTFT) | streaming | SSE proxy with zero buffering, HTTP/2 keepalive to providers |
| NFR-004 (<50ms backend P95) | excl. provider | async SQLAlchemy + asyncpg + Redis cache for hot reads |
| NFR-005 (10K+ RPS) | sustained | k6 load tests in CI gate, HPA on RPS metric |
| NFR-006 (99.999% durability) | data | Postgres streaming replication + S3 versioning + daily backups to cross-region |
| NFR-007/008 (RTO/RPO) | <5min/<1min | WAL shipping, automated failover via Patroni, runbooks in `docs/runbooks/` |
| NFR-010 (cold start) | Go <200ms, Py <5s | Go: scratch image, no init work. Python: lazy imports, `prefork` worker pool |

---

## 7. Risks & Open Questions

These are the items I'd push back on the DRD for before sprint planning:

1. **15µs P99 vs Redis lookup on hot path.** Redis local-net round-trip is ~100-500µs. Either NFR-002 must exclude mandatory Redis I/O, or auth metadata must live in an in-process LRU (with Redis as fallback). The scaffold uses an LRU-with-Redis-backing pattern (`gateway-go/internal/auth/cache.go`).
2. **Go↔Python protocol.** DRD says "gRPC or HTTP." This scaffold commits to gRPC (`shared/proto/`) with HTTP/JSON only for admin tooling. Pick one, stick to it.
3. **Semantic cache miss cost.** L2 lookup adds latency to every miss. Scaffold makes L2 opt-in via `X-Semantic-Cache: true` header.
4. **License risk.** psycopg3 is LGPL-3.0 — fine for SaaS, problematic if `IN-010` air-gapped distribution ships it. Scaffold uses `asyncpg` (MIT) instead.
5. **MCP "Code Mode" claims.** The "50% fewer tokens, 40% lower latency" needs benchmarking before being a P2 commitment.

---

## 8. Definition of Done (per service)

A service is "production ready" only when ALL of:

- [ ] All P0 requirements from its DRD module implemented and tested
- [ ] Unit test coverage > 80%
- [ ] Integration tests against testcontainers (Postgres, Redis, mock providers) pass
- [ ] Load test meets NFR target (gate in CI)
- [ ] Prometheus metrics emitted, Grafana dashboard committed in `infrastructure/grafana/`
- [ ] OpenTelemetry spans on every request boundary
- [ ] Structured logs emitted (`slog` for Go, `structlog` for Python)
- [ ] Health check endpoint returns dependency status
- [ ] Dockerfile builds reproducibly, image scanned (Trivy CRITICAL = 0)
- [ ] Helm chart values documented
- [ ] Runbook in `docs/runbooks/{service-name}.md`
- [ ] On-call alert rules in `infrastructure/alerts/`

This scaffold provides the structure for every checkbox above. Filling them is the work of Phases 1-4.
