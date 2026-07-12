# OpenRouter-Equivalent AI Gateway

Production-grade unified AI API gateway. Polyglot architecture: Go (hot path) + Python (warm path) + TypeScript (DX).

> **Source DRD:** [openrouter-drd-go-python-typescript.md](openrouter-drd-go-python-typescript.md)
> **Plan & traceability:** [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)
> **Runtime architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Quick Start

```bash
# 1. Prerequisites: docker, go 1.24+, python 3.12+, node 20+, make
make check-tools

# 2. Bootstrap dev dependencies (postgres, redis, nats, minio)
docker-compose up -d
make migrate

# 3. Run all services in dev mode
make dev-all

# 4. Verify
curl http://localhost:8080/health
```

## Repository Layout

| Path | Purpose | Stack |
|---|---|---|
| [`gateway-go/`](gateway-go/) | Hot-path reverse proxy, routing, streaming | Go 1.24 |
| [`backend-python/`](backend-python/) | Business logic, providers, ML, billing | Python 3.12 + FastAPI |
| [`frontend-web/`](frontend-web/) | Dashboard, playground, docs, marketplace | Next.js 15 + React 19 |
| [`cli/`](cli/) | `@openrouter/cli` developer tool | Node.js 20 + TypeScript |
| [`shared/`](shared/) | gRPC `.proto` + canonical OpenAPI spec | — |
| [`infrastructure/`](infrastructure/) | k8s, Helm, Terraform | YAML / HCL |
| [`tools/`](tools/) | Mock providers, load tests | Python / JS |
| [`docs/`](docs/) | ADRs, runbooks, requirements traceability | Markdown |

## Common Commands

```bash
make help              # all targets
make build             # build all stacks
make test              # run all tests
make lint              # lint all stacks
make docker            # build all docker images
make k8s-apply ENV=dev # apply k8s manifests
make load-test         # run k6 load tests against local
```

## Status

This is a scaffold — see [DEVELOPMENT_PLAN.md §1](DEVELOPMENT_PLAN.md) for what is implemented vs stubbed. Phase 1 foundations work end-to-end; Phases 2-4 are scaffolded with interfaces and TODOs mapped to DRD requirement IDs.
