# Engineering Onboarding — Week 1

Goal: by Friday you can run the full stack locally, ship a small change end to
end (PR → CI green → merged), and know where to ask for help.

## Day 1 — Read & set up

- Read in this order:
  1. [README.md](../README.md) — what we're building
  2. [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) — phased delivery + what is real vs stubbed
  3. [ARCHITECTURE.md](../ARCHITECTURE.md) — runtime topology, conventions
  4. [openrouter-drd-go-python-typescript.md](../openrouter-drd-go-python-typescript.md) — full DRD (skim, don't read top to bottom)
  5. [docs/local-dev.md](local-dev.md) — get the stack up
- Get the stack running: `bash scripts/dev-all.sh` then `bash scripts/verify-stack.sh` should be all green.
- Slack: introduce yourself in `#eng`, ask to be added to `#oncall` and `#alerts`.

## Day 2 — Trace a request end to end

Start with a working request and follow it through every layer:

1. `curl -H "Authorization: Bearer $KEY" -X POST http://localhost:8080/api/v1/chat/completions ...`
2. Read the gateway middleware chain order in [docs/middleware-order.md](middleware-order.md). Open each middleware file in `gateway-go/internal/middleware/`.
3. Follow the proxy hop into `gateway-go/internal/proxy/` and the corresponding adapter in `backend-python/app/infrastructure/providers/`.
4. Find where the usage event is emitted (NATS) and where the metering worker consumes it (`backend-python/app/application/services/`).
5. Sketch the trace on paper. Ping your buddy if any layer surprised you.

## Day 3 — Pick up your first ticket

- Look for issues labeled `good-first-issue` or `phase-1`.
- A frequent starter ticket is "add model X to the catalog" — follow
  [ADDING_NEW_MODELS_GUIDE.md](ADDING_NEW_MODELS_GUIDE.md), which walks through
  the Gemma 4 + Qwen 3.6 integration end-to-end and ends with an 11-step
  cheat sheet you can reuse for the next model.
- Open a draft PR within the day. Even a 10-line change exercises the full CI loop.
- Coding conventions:
  - Go: `gofmt`, `golangci-lint`, `slog` for logs, no panics outside `main`.
  - Python: `ruff check && ruff format`, `structlog`, type hints required, no bare `except`.
  - TS: `eslint`, `prettier`, RSC by default — `'use client'` only when needed.

## Day 4 — Tests + observability

- Run the test pyramid:
  - Go: `cd gateway-go && make test`
  - Python: `cd backend-python && make test`
  - Mocks: `cd tools/mock-providers && make test`
  - Load smoke: `cd tools/load-tests && make smoke`
- Pull up Grafana (`http://localhost:3001` if running observability stack) and find:
  - Your test traffic in `gateway_requests_total`
  - The matching trace in Tempo (search by request ID)
  - The structured log line in Loki

## Day 5 — Ship it

- Resolve PR review comments, get one approval, merge.
- Watch the deploy pipeline (GitHub Actions). When green, your change is on staging.
- Read [docs/release-process.md](release-process.md) to understand how staging becomes prod.
- End of week 1:1 with your manager — surface any blockers we should remove for the next person.

## Where to ask

| Topic | Channel / person |
|---|---|
| Local setup broken | `#eng-help` |
| Architecture / design | `#eng-architecture`, your tech lead |
| Incident / oncall | `#oncall`, current oncall |
| Vault / secrets | `#sec-eng` |
| Anything else | your buddy first, then `#eng` |
