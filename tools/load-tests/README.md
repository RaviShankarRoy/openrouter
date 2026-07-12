# Load Tests (k6)

Validates the gateway's NFR targets:

- **NFR-005** — 10K+ RPS sustained
- **NFR-002** — < 15 µs P99 gateway overhead at 5K RPS
- **NFR-003** — < 200 ms TTFT for streaming

These scripts hit the local stack — they are **not** load tests against real
provider APIs. The provider mocks (`tools/mock-providers/`) sit behind the
gateway so we measure gateway overhead, not OpenAI's response time.

## Prerequisites

```bash
# k6 v0.55+
brew install k6                                    # macOS
sudo apt-get install k6                            # Debian/Ubuntu (xK6 repo)

# Local stack must be up:
make dev-all                                       # tmux: gateway + backend + mock providers

# Optional: InfluxDB + Grafana for the dashboard
docker run -d -p 8086:8086 influxdb:1.8
# Import dashboards/grafana-k6.json into Grafana.
```

## Targets

| Target | Profile | Duration | What it proves |
|---|---|---|---|
| `make smoke` | 1 VU | 30 s | API works at all |
| `make run` (load) | 5 K RPS | 5 min | Sustains the steady state from NFR-005 |
| `make stress` | ramp 0 → 15 K RPS | 10 min | Find breaking point |
| `make spike` | 0 → 10 K → 0 | 60 s | Survives traffic spikes |
| `make soak` | 2 K RPS | 1 h | No memory leaks / connection leaks |
| `make streaming` | 200 VUs | 5 min | SSE chunk timing (NFR-003) |

## Running

```bash
make smoke                                         # quick sanity check
make run                                           # full 5K RPS load test
make BASE_URL=https://staging.example.com run      # against another env
```

Pipe metrics to InfluxDB:

```bash
make K6_OUT='--out influxdb=http://localhost:8086/k6' run
```

## Interpreting results

The thresholds in `k6/thresholds.js` correspond directly to NFR IDs. A failing
threshold prints in red and the run exits non-zero — wired into CI as a quality
gate. Keep an eye on:

- `http_req_duration{kind:gateway}` P99 — should be sub-millisecond at the
  gateway because the mock returns in microseconds. Anything else is the
  gateway adding overhead.
- `http_req_failed` — must stay at 0 for the load test (any 5xx is a real bug).
- `iteration_duration` — total round-trip including provider mock latency.

When a threshold fails, drill into the per-tag breakdown the summary prints.
The `dashboards/grafana-k6.json` dashboard is the friendlier view for sustained
runs.
