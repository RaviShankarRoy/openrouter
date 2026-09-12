# gateway-go

The hot-path reverse proxy. Stateless, layered n-tier architecture, sub-15µs target overhead.

## Layout

```
cmd/gateway/                 main — composition root only
internal/
  config/                    koanf-based config with env override + validation
  server/                    HTTP + metrics server wiring
  middleware/                Chain-of-responsibility: requestid, log, trace, auth, ratelimit
  auth/                      Layered cache: in-process LRU → Redis → backend gRPC
  ratelimit/                 Strategy: Redis sliding window (Lua atomic)
  cache/                     L1 exact-match cache (Redis)
  router/                    Resolves model → target; supports SIGHUP hot-reload
    strategies/              Strategy pattern: cost, latency, quality, geo
  proxy/                     Outbound: provider selection, adapter, breaker, streaming
    adapters/                Provider Adapter pattern: openai, anthropic, google
  circuitbreaker/            sony/gobreaker registry, one breaker per (provider,model)
  observability/             slog, OTel, prometheus
  transport/http/handlers/   Thin HTTP handlers — no business logic
configs/providers.yaml       Hot-reloadable provider + model routing
```

## Design Patterns

- **Layered N-Tier**: `internal/api/` (presentation) → `internal/service/` (business) → `internal/repository/` (data), plus `internal/shared/` for config, models, and observability. Imports point downward only.
- **Chain of Responsibility**: middleware pipeline in `internal/api/middleware/`.
- **Strategy**: routing strategies in `internal/service/strategies/`.
- **Adapter**: provider request/response normalization in `internal/repository/adapters/`.
- **Circuit Breaker**: per-(provider,model) breaker in `internal/service/circuitbreaker/`.
- **Object Pool**: `sync.Pool` for streaming buffers in `internal/service/proxy/pool.go`.
- **Factory**: HTTP client per provider lazily built in `internal/service/proxy/pool.go`.
- **Observer**: health checks notify routing engine (Phase 2 — see `internal/health/`).

## Quick start

```bash
make dev       # hot-reload via air
make test      # unit tests
make build     # static binary
make docker    # scratch image, ~15MB
```

## Requirement coverage (see ../DEVELOPMENT_PLAN.md)

| DRD ID | File |
|---|---|
| GW-001 OpenAI-compat endpoint | `internal/api/handlers/handlers.go` ChatHandler |
| GW-002 SSE streaming | `internal/service/proxy/proxy.go` send() stream branch |
| GW-005 Connection pooling | `internal/service/proxy/pool.go` clientPool |
| GW-006 Async logging | `internal/api/middleware/chain.go` Logger (NATS publish in Phase 1) |
| GW-008 Health endpoint | `internal/api/handlers/handlers.go` Ready |
| GW-013 Auth via Redis | `internal/repository/auth/cache.go` |
| GW-014 Rate limit | `internal/service/ratelimit/limiter.go` |
| GW-015 Hot-reload routing | `internal/service/router/router.go` Swap() + SIGHUP in main |
