# gateway-go

The hot-path reverse proxy. Stateless, hexagonal architecture, sub-15µs target overhead.

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

- **Hexagonal Architecture** (Ports & Adapters): domain in `internal/`, driven adapters in `internal/adapters/proxy/`, driving adapter in `internal/transport/http/`.
- **Chain of Responsibility**: middleware pipeline in `internal/middleware/`.
- **Strategy**: routing strategies in `internal/router/strategies/`.
- **Adapter**: provider request/response normalization in `internal/proxy/adapters/`.
- **Circuit Breaker**: per-(provider,model) breaker in `internal/circuitbreaker/`.
- **Object Pool**: `sync.Pool` for streaming buffers in `internal/proxy/pool.go`.
- **Factory**: HTTP client per provider lazily built in `internal/proxy/pool.go`.
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
| GW-001 OpenAI-compat endpoint | `internal/transport/http/handlers/handlers.go` ChatHandler |
| GW-002 SSE streaming | `internal/proxy/proxy.go` send() stream branch |
| GW-005 Connection pooling | `internal/proxy/pool.go` clientPool |
| GW-006 Async logging | `internal/middleware/chain.go` Logger (NATS publish in Phase 1) |
| GW-008 Health endpoint | `internal/transport/http/handlers/handlers.go` Ready |
| GW-013 Auth via Redis | `internal/auth/cache.go` |
| GW-014 Rate limit | `internal/ratelimit/limiter.go` |
| GW-015 Hot-reload routing | `internal/router/router.go` Swap() + SIGHUP in main |
