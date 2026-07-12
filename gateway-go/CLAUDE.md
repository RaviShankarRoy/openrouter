# gateway-go — Hot-Path Reverse Proxy

Go 1.24 reverse proxy implementing the OpenAI-compatible API surface. Hexagonal architecture, Chain-of-Responsibility middleware, circuit breaker per provider. Owns the latency budget (target P99 < 15µs gateway overhead per [NFR-002](../DEVELOPMENT_PLAN.md#6-non-functional-requirements--how-each-is-met)).

## Commands

```bash
go test ./...                          # all unit tests (30 currently pass)
go test -race -coverprofile=coverage.out ./...   # CI-equivalent run
golangci-lint run                      # lint
go build ./cmd/gateway                 # build binary
make test                              # delegates to the above
make dev                               # air hot-reload (if installed)
```

## Layout (Hexagonal / Ports & Adapters)

```
cmd/gateway/                # entry point: main.go
internal/
├── auth/                   # LRU + Redis + gRPC fallback for key validation
├── cache/                  # L1 exact-match Redis cache
├── circuitbreaker/         # sony/gobreaker wrapper, per-provider
├── middleware/             # chain.go: id → log → auth → ratelimit → cache → route → proxy
├── pool/                   # sync.Pool for hot-path []byte buffers
├── proxy/                  # HTTP/2 connection pooling + provider adapters
│   └── adapters/           # openai.go, anthropic.go, google.go — UnifiedRequest/Response
├── router/                 # provider selection + fallback chain
│   └── strategies/         # cost / latency / quality (Strategy pattern)
├── server/                 # http.Server with functional options
└── transport/http/handlers/    # /v1/chat/completions, /health
```

## Middleware Chain Order

Middleware order matters — defined in `internal/middleware/chain.go`. Don't reorder without checking circuit-breaker semantics:

```
RequestID → Recoverer → Logger → Auth → RateLimit → Cache(L1) → Router → Proxy(+CircuitBreaker) → Telemetry
```

## Adding a New Provider Adapter

1. Implement `proxy.Adapter` interface in `internal/proxy/adapters/<name>.go`:
   - `NormalizeRequest(UnifiedRequest) (httpRequest, error)`
   - `NormalizeResponse(httpResponse) (UnifiedResponse, error)`
   - `StreamTranslator() proxy.StreamTranslator`
2. Register in `internal/proxy/factory.go`
3. Add config schema entry for `providers.yaml`
4. Add table-driven unit tests in `<name>_test.go` (see `anthropic_test.go`)

For streaming adapters, **buffer to `\n\n` SSE boundaries before flushing** — the current `PassthroughTranslator` in `proxy.go` writes raw 32 KB read chunks, which can split SSE events mid-JSON.

## Hot-Path Rules

- **No logging on the request path.** Emit to NATS asynchronously via `internal/telemetry`.
- **No DB connections.** Auth metadata comes from LRU → Redis → gRPC to backend.
- **Use `sync.Pool`** for buffers > 4 KB. See `internal/pool/`.
- **Context propagation:** every outbound call must use `ctx` from `r.Context()`.
- **No panics in middleware** — `Recoverer` wraps the chain but a panic mid-stream after `w.WriteHeader` produces "superfluous response.WriteHeader" log spam.

## Notable Dependencies

- `github.com/go-chi/chi/v5` — HTTP router
- `github.com/sony/gobreaker` — circuit breaker (wrapped, not used directly)
- `github.com/redis/go-redis/v9` — Redis client
- `google.golang.org/grpc` — backend communication
- `prometheus/client_golang` — `/metrics` endpoint
- `slog` (stdlib) — structured JSON logging

## Known Issues (from audit)

- `internal/auth/cache.go` uses random map eviction instead of LRU — replace with `hashicorp/golang-lru/v2`.
- `internal/middleware/ratelimit.go:29` fails open on Redis error — consider in-process token bucket fallback.
- `internal/proxy/pool.go` honors `HTTP_PROXY`/`HTTPS_PROXY` env vars — SSRF risk if env injected; pin `Transport.Proxy = nil` in prod.
- gRPC client uses `insecure.NewCredentials()` ([internal/auth/grpc_client.go:39](internal/auth/grpc_client.go#L39)). mTLS expected via service mesh in prod but no mesh manifest exists yet.
- `chatRequest` handler decodes 10MB JSON with no depth limit — bound via `json.Decoder` if Go version doesn't already.

## Tests

5 packages with tests: `auth` (9), `cache` (6), `circuitbreaker` (5), `proxy/adapters` (5), `ratelimit` (5). 13 packages have no tests yet. CI gate: `go test -race` with coverage upload.
