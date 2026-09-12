# Architecture Overview

For the requirement-by-requirement plan, see [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md). This document describes the runtime topology, data flow, and the conventions every service follows.

---

## 1. Runtime Topology

```
                    ┌─────────────────────┐
   client ──TLS────▶│  Cloudflare (WAF)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Ingress (Nginx)    │   k8s ingress
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
       ┌────────▼─────────┐         ┌─────────▼─────────┐
       │  gateway-go      │         │  frontend-web     │
       │  (Deployment)    │         │  (Deployment)     │
       │  HPA: 5-200 pods │         │  HPA: 2-20 pods   │
       └────┬─────────┬───┘         └─────────┬─────────┘
            │         │                       │ /api/* (BFF)
            │ gRPC    │ HTTP→Provider          │
            │         │                       │
            │         └──── (egress) ─── LLM Providers
            │                                 │
       ┌────▼──────────────────────────┐      │
       │  backend-python (Deployment)  │◀─────┘
       │  FastAPI + uvicorn            │
       │  HPA: 3-50 pods               │
       └────┬─────────────────┬────────┘
            │                 │
            │                 └──── Celery worker (StatefulSet)
            │                       (video, webhook, billing)
            ▼
   ┌────────┴────────┬────────────┬─────────────┐
   │ PostgreSQL 16   │ Redis 7    │ NATS        │ S3 (Minio in dev)
   │ + pgvector      │ Cluster    │ JetStream   │
   │ Patroni HA      │            │             │
   └─────────────────┴────────────┴─────────────┘
```

---

## 2. Cross-cutting Conventions

Every service follows these. They are enforced by linters, CI, and code review.

### 2.1 Configuration

- **Source of truth:** environment variables, validated at startup.
- **Local dev:** `.env` files (gitignored), template in `.env.example`.
- **Production:** k8s `Secret` + `ConfigMap`, mounted as env.
- **Hot-reload:** Go gateway routing config via SIGHUP; everything else requires pod restart.
- **Schema validation:** Go uses [`koanf`](https://github.com/knadh/koanf) with struct tags; Python uses `pydantic-settings`; TypeScript uses `zod`.

### 2.2 Logging

- **Format:** JSON, one event per line, UTC timestamps.
- **Required fields:** `timestamp`, `level`, `service`, `version`, `trace_id`, `span_id`, `request_id`.
- **Optional fields:** `org_id`, `user_id`, `key_id`, `model`, `provider` — never log raw API keys, prompts, or PII.
- **Sink:** stdout. Promtail ships to Loki. Local dev tails to terminal.
- **Implementation:** Go = `slog` with custom handler; Python = `structlog` with JSON renderer; TS = `pino`.

### 2.3 Metrics

- **Format:** Prometheus exposition.
- **Endpoint:** `/metrics` on every service (separate from main port for scraping policy).
- **Naming:** `{service}_{subsystem}_{metric}_{unit}`. e.g., `gateway_proxy_request_duration_seconds`.
- **Cardinality discipline:** never label by `user_id` or `request_id`. `key_id` only if cardinality is bounded.

### 2.4 Tracing

- **Standard:** OpenTelemetry SDK in every service.
- **Exporter:** OTLP/gRPC to Grafana Tempo (or Jaeger in dev).
- **Sampling:** head-based, 100% errors, 1% success.
- **Propagation:** W3C Trace Context (`traceparent` header).
- **Span boundaries:** every HTTP/gRPC ingress, every outbound provider call, every DB query > 10ms.

### 2.5 Errors

- **Wire format:** OpenAI-compatible error envelope:
  ```json
  {"error": {"message": "...", "type": "...", "code": "...", "param": "..."}}
  ```
- **Internal:** Go uses wrapped `error` with `errors.Is/As`; Python defines a small `DomainError` hierarchy in `app/service/domain/errors.py`; never raise raw `Exception`.
- **HTTP mapping:** see `shared/openapi/errors.yaml`.

### 2.6 Database

- **Owner:** Python backend exclusively. Go never opens a SQL connection.
- **Migrations:** Alembic in `backend-python/alembic/`. Forward-only — no down migrations in prod.
- **Connection pooling:** `asyncpg` pool, sized `cpu_count * 2 + reserve`.
- **Transactions:** Unit of Work pattern, `async with uow:` blocks.

### 2.7 Auth between services

- **Internal:** mTLS via service mesh (Linkerd or Istio in production; bypassed in dev).
- **Service identity:** SPIFFE IDs, e.g. `spiffe://openrouter/ns/prod/sa/gateway-go`.
- **API key validation:** Go does Redis lookup; on cache miss, gRPCs to backend `AuthService.ValidateKey`.

---

## 3. Data Flow: A Single `chat/completions` Request

```
1. Client → Cloudflare → Nginx → gateway-go pod
2. gateway-go middleware chain executes in order:
   a. RequestID middleware: assign UUID, set trace span
   b. Logger middleware: log request meta (no body)
   c. Auth middleware:
      - Extract Bearer token, hash it
      - LRU cache lookup (in-process, 60s TTL)
      - Miss → Redis GET auth:{hash}
      - Miss → gRPC to backend.AuthService.ValidateKey
      - Cache result both layers
   d. RateLimit middleware:
      - Redis sliding window check (Lua script, atomic)
      - 429 with Retry-After if exceeded
   e. Cache middleware (L1):
      - SHA-256(model + messages + params)
      - Redis GET — hit returns cached response, exit chain
   f. Router middleware:
      - Read provider scores from Redis
      - Apply routing strategy (cost/latency/quality from key policy)
      - Choose primary + fallback chain
   g. Proxy middleware:
      - Acquire HTTP/2 connection from pool to chosen provider
      - Adapter normalizes request → provider native format
      - For SSE: stream chunks back to client, never buffer
      - For non-streaming: read full response, normalize, return
   h. CircuitBreaker wrap:
      - On 5xx/timeout/429: increment failures, possibly open
      - If open or all providers fail: try next in fallback chain
   i. Telemetry middleware (deferred):
      - Emit usage event to NATS subject `gateway.usage`
      - Emit metric to local Prometheus
3. Async (out of request path):
   a. Python metering worker consumes `gateway.usage`
   b. Token count via tiktoken (or provider-reported)
   c. Cost = tokens × model_price
   d. UPDATE credit_balance, INSERT usage_record
   e. Check budget thresholds → optional alert
4. Response delivered to client.
```

---

## 4. Failure Modes

| Failure | Detection | Mitigation |
|---|---|---|
| Provider 5xx | HTTP status from upstream | Circuit breaker opens after 5 failures in 30s; route to fallback |
| Provider timeout | `context.DeadlineExceeded` | Same as 5xx |
| All providers down for model | Fallback chain exhausted | Return cached response if available; else 503 + Retry-After |
| Redis down | Connection error | Auth degrades to backend gRPC (slow but works); rate limit fails open with metric alert |
| Postgres down | Connection error | Backend returns 503 for write paths; reads from Redis cache where possible |
| Backend down | gRPC error | Gateway uses last-known auth cache (extended TTL during incident); new key creation fails |
| NATS down | Publish error | Usage events queue locally on disk (bounded), drained when NATS recovers |
| OOM in Go gateway | k8s OOMKilled | HPA + memory limit tuned via load test; pod replaced |

---

## 5. Security Boundaries

- **Public surface:** `gateway-go:443` (TLS), `frontend-web:443` (TLS).
- **Internal surface:** mTLS only. No service exposes plaintext outside its pod.
- **Secrets:** HashiCorp Vault in prod, k8s `Secret` for bootstrap. Never in env files committed to git.
- **API keys:** hashed with argon2id (memory=64MB, iters=3, parallelism=4) before storage.
- **PII:** scrubbed from logs by default. Opt-in raw prompt logging requires org admin signoff and shorter retention.

---

## 6. Local Development

```bash
# 1. Bring up dependencies
docker-compose up -d  # postgres, redis, nats, minio

# 2. Run each stack (separate terminals)
make dev-gateway       # go run with hot reload via air
make dev-backend       # uvicorn --reload
make dev-frontend      # next dev
make dev-mock          # tools/mock-providers

# 3. Or run everything via tmux
make dev-all
```

See [docs/local-dev.md](docs/local-dev.md) for full setup.
