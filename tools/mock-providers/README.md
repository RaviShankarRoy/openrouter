# Mock Providers

A FastAPI app that emulates OpenAI, Anthropic, and Google AI APIs with realistic
shapes (tool calls, structured outputs, streaming, embeddings, images). Used by
CI integration tests so we never hit a real provider — see DRD §23.2.

## What it does

- Implements the routes the Go gateway adapters speak to:
  - OpenAI:    `/v1/chat/completions`, `/v1/embeddings`, `/v1/images/generations`
  - Anthropic: `/v1/messages` (with content blocks)
  - Google:    `/v1beta/models/{model}:generateContent`
- Responses match the upstream shapes closely enough that a real adapter cannot
  tell the difference. Streaming uses SSE (`sse-starlette`).
- A scenario engine lets a test inject latency, error rates, and rate-limit
  bursts at runtime via the control plane.

## Why it exists

Real provider APIs are slow, flaky, expensive, and unavailable in CI. Without
this server we cannot meaningfully exercise the provider adapters, the circuit
breaker (LB-003), backoff (RL-006), or the SSE proxy (GW-002).

## Quick start

```bash
make install        # editable install + dev deps
make dev            # uvicorn on :9100 (reload)
make test           # pytest
make docker         # multi-stage build, < 200MB
```

## Configuration

All knobs are env vars; defaults are listed in `src/config.py`.

| Var | Default | Purpose |
|---|---|---|
| `MOCK_PORT` | `9100` | HTTP port |
| `MOCK_DEFAULT_LATENCY_MS` | `5` | Baseline injected latency per request |
| `MOCK_DEFAULT_ERROR_RATE` | `0.0` | Probability (0..1) of returning a 5xx |
| `MOCK_DEFAULT_RATE_LIMIT_RATE` | `0.0` | Probability of returning 429 |
| `MOCK_STREAM_CHUNK_DELAY_MS` | `20` | Delay between SSE chunks |
| `MOCK_LOG_LEVEL` | `info` | uvicorn log level |

Override at runtime via the control plane (no restart needed):

```bash
# Make every OpenAI chat call take 2s and fail 10% of the time
curl -X POST http://localhost:9100/control/scenario \
  -H 'Content-Type: application/json' \
  -d '{"provider":"openai","route":"chat","latency_ms":2000,"error_rate":0.1}'

# Inspect what the server is currently doing
curl http://localhost:9100/control/stats
```

Snapshots captured by the gateway test suite can be replayed back via the
control plane to reproduce a flaky failure deterministically — see
`src/control/snapshots.py`.

## Wiring it into the gateway

Point the Go gateway provider config at the mock instead of the real upstream:

```yaml
# gateway-go/configs/providers.yaml (test profile)
providers:
  openai:
    base_url: http://localhost:9100/v1
  anthropic:
    base_url: http://localhost:9100
  google:
    base_url: http://localhost:9100/v1beta
```

## Scenario reference (DRD requirement IDs)

The scenario engine names map directly to DRD requirement IDs so test failures
are easy to attribute:

| Scenario | DRD ID | What it does |
|---|---|---|
| `latency_spike` | NFR-002 | Sleep N ms before responding |
| `provider_429` | RL-006 | Return 429 with `Retry-After` |
| `provider_5xx` | LB-003 | Return 503 to trip the circuit breaker |
| `slow_stream` | NFR-003 | Add per-chunk delay to SSE responses |
| `tool_call` | PI-004 | Reply with a `tool_calls` array |
| `structured_output` | PI-005 | Reply with `response_format: json_schema` shaped content |
