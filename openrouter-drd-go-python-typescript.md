# Project: OpenRouter — Developer Requirements Document (DRD)

**Version:** 2.0
**Date:** April 26, 2026
**Classification:** Internal — Engineering & Product
**Architecture:** Go (Gateway Core) + Python (Backend & ML) + TypeScript (Frontend & DX)

---

## Table of Contents

1. Executive Summary
2. Product Vision & Goals
3. System Architecture Overview
4. Module 1 — Gateway Core (Go)
5. Module 2 — Backend Services (Python)
6. Module 3 — Frontend & Developer Portal (TypeScript)
7. Module 4 — Provider Integration Layer
8. Module 5 — Multimodal API Surface
9. Module 6 — Routing & Load Balancing Engine
10. Module 7 — Caching System
11. Module 8 — Authentication & API Key Management
12. Module 9 — Billing, Metering & Cost Control
13. Module 10 — Rate Limiting & Throttling
14. Module 11 — Guardrails, Safety & Compliance
15. Module 12 — MCP Gateway (Model Context Protocol)
16. Module 13 — Agentic Workflow Support
17. Module 14 — Observability & Monitoring
18. Module 15 — Developer Experience (DX)
19. Module 16 — Marketplace & Model Discovery
20. Module 17 — Admin Dashboard & Analytics
21. Module 18 — Security Infrastructure
22. Module 19 — Infrastructure & Deployment
23. Module 20 — Testing Strategy
24. Module 21 — Competitive Feature Matrix
25. Non-Functional Requirements
26. Development Phases & Milestones
27. Technology Stack Summary
28. Glossary

---

## 1. Executive Summary

This document defines the complete developer requirements for building a production-grade **unified AI API gateway** — a platform equivalent to OpenRouter that provides a single API endpoint for accessing 300+ AI models across 60+ providers, with unified billing, intelligent routing, automatic failover, and enterprise governance.

The platform uses a **polyglot architecture** optimized for the strengths of each language:

- **Go** — Gateway core (hot path): reverse proxy, routing, streaming, failover. Chosen for sub-15µs overhead, goroutine concurrency, and single-binary deployment. Every major open-source AI gateway (Bifrost, Kong, Envoy) uses Go for this layer.
- **Python** — Backend services, provider adapters, and ML features: billing logic, user management, semantic routing, guardrails, embeddings, model evaluation. Chosen for the richest AI/ML ecosystem, native provider SDKs, and fastest iteration speed.
- **TypeScript** — Frontend, developer portal, API documentation, and CLI tooling: dashboard, playground, docs site, SDK generation. Chosen for full-stack web capability, Vercel AI SDK compatibility, and clean developer experience.

**Target scale:** 1 billion+ tokens/day, 10,000+ RPS, 99.95% uptime SLA.

---

## 2. Product Vision & Goals

### Primary Goals

- PG-1: Provide a single, OpenAI-compatible API endpoint that routes to any AI model from any provider
- PG-2: Normalize all provider request/response schemas into one unified format
- PG-3: Automatically handle failover, load balancing, and provider health monitoring
- PG-4: Provide unified billing, usage tracking, and cost controls
- PG-5: Support all modalities — text, image, audio, video, embeddings, and reranking
- PG-6: Enable enterprise governance — RBAC, audit logs, compliance, guardrails
- PG-7: Serve as an MCP gateway for agentic AI workflows

### Secondary Goals

- SG-1: Build a model marketplace with rankings, pricing comparisons, and playground
- SG-2: Provide a prompt management and versioning system
- SG-3: Enable bring-your-own-key (BYOK) for users who prefer direct provider billing
- SG-4: Support self-hosted / on-premise deployment for enterprise customers
- SG-5: Achieve sub-15µs gateway overhead at 5,000 RPS sustained

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Applications                          │
│  (SDKs: OpenAI Python/JS, Anthropic SDK, custom HTTP clients)    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS (OpenAI-compatible)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Edge Layer (CDN + WAF)                         │
│            Cloudflare / AWS CloudFront + Shield                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 GATEWAY CORE (Go — Hot Path)                     │
│                 Language: Go 1.24+                                │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │TLS Term. │ │  Auth    │ │  Router  │ │ Schema Normalizer   │ │
│  │& Parse   │→│ (key     │→│ (model + │→│ (per-provider        │ │
│  │          │ │  lookup) │ │  health) │ │  request/response)  │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │Rate      │ │ Cache    │ │ Stream   │ │ Failover &          │ │
│  │Limiter   │ │ Layer    │ │ Proxy    │ │ Circuit Breaker     │ │
│  │(Redis)   │ │(exact)   │ │ (SSE)    │ │                     │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │ gRPC / HTTP internal
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│           BACKEND SERVICES (Python — Warm Path)                  │
│           Language: Python 3.12+ / FastAPI / SQLAlchemy          │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │User &    │ │ Billing  │ │ Auth &   │ │ Audit Logging       │ │
│  │Org Mgmt  │ │ & Meter  │ │ RBAC     │ │                     │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │Semantic  │ │ MCP      │ │Guardrails│ │ Prompt Mgmt         │ │
│  │Cache/    │ │ Gateway  │ │ Engine   │ │ & Versioning        │ │
│  │Routing   │ │          │ │          │ │                     │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────────────────┐ │
│  │Provider  │ │ Model    │ │ Evaluation & Quality Scoring     │ │
│  │Adapters  │ │ Registry │ │ (promptfoo, deepeval, custom)    │ │
│  └──────────┘ └──────────┘ └──────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│           FRONTEND & DX LAYER (TypeScript)                       │
│           Language: TypeScript / Next.js 15 / React 19           │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │User      │ │ API      │ │ Model    │ │ Interactive         │ │
│  │Dashboard │ │ Playground│ │ Market-  │ │ API Docs            │ │
│  │          │ │          │ │ place    │ │ (OpenAPI)            │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────────────────┐ │
│  │Admin     │ │ Status   │ │ CLI Tool (npx / global install)  │ │
│  │Panel     │ │ Page     │ │                                  │ │
│  └──────────┘ └──────────┘ └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                 │
│                                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────────┐│
│  │ PostgreSQL   │ │    Redis     │ │   Object Storage (S3)      ││
│  │ 16 + pgvector│ │ 7 / Valkey   │ │   Video/Image/Audio files  ││
│  │ Users, keys, │ │ Rate limits, │ │                            ││
│  │ usage, billing│ │ exact cache, │ │                            ││
│  │ vectors      │ │ sessions     │ │                            ││
│  └──────────────┘ └──────────────┘ └────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    LLM PROVIDERS (60+)                             │
│  OpenAI │ Anthropic │ Google │ Mistral │ Bedrock │ Azure          │
│  Groq   │ Together  │ Cohere │ DeepSeek│ xAI     │ Ollama         │
│  Fireworks│ Replicate│ Qwen  │ Cerebras│ ByteDance│ HuggingFace   │
└──────────────────────────────────────────────────────────────────┘
```

### Why This Stack

| Layer | Language | Why This Language |
|---|---|---|
| Gateway core | Go | Every major AI gateway uses Go for proxying. 11µs overhead at 5K RPS, goroutines for concurrency, single binary, no runtime dependencies. Bifrost, Kong, Envoy, Docker, Kubernetes — all Go. |
| Backend | Python | All provider SDKs are Python-first (openai, anthropic, google-genai). Richest AI/ML ecosystem (tiktoken, sentence-transformers, guardrails-ai, promptfoo). FastAPI is production-ready. LiteLLM, the most popular open-source AI proxy, is Python. |
| Frontend & DX | TypeScript | Next.js for SSR dashboard, React for interactive playground, Vercel AI SDK for streaming UI, OpenAPI codegen for SDK generation. The standard for modern developer portals. |

---

## 4. Module 1 — Gateway Core (Go)

### 4.1 Purpose

The stateless, high-performance reverse proxy that sits in the hot path of every API request. Written in Go for maximum throughput and minimal latency. This is a pure network-level component — no business logic, no database queries, no ML inference.

### 4.2 Frameworks & Libraries

| Library | Purpose |
|---|---|
| `net/http` or `fasthttp` | HTTP server (evaluate both; fasthttp for max throughput) |
| `github.com/gin-gonic/gin` or custom router | Request routing (Gin if team prefers frameworks) |
| `github.com/redis/go-redis/v9` | Redis client for rate limiting and cache lookup |
| `github.com/sony/gobreaker` | Circuit breaker pattern |
| `github.com/prometheus/client_golang` | Prometheus metrics |
| `go.opentelemetry.io/otel` | OpenTelemetry tracing |
| `golang.org/x/sync/semaphore` | Concurrency control |
| `slog` (stdlib) | Structured logging |
| `gopkg.in/yaml.v3` | Configuration parsing |

### 4.3 Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| GW-001 | OpenAI-compatible `/api/v1/chat/completions` endpoint | P0 | Drop-in replacement for OpenAI SDK — change only base URL |
| GW-002 | SSE streaming support | P0 | All models stream correctly; `stream: true` works identically to OpenAI |
| GW-003 | Request parsing and validation | P0 | Reject malformed requests with clear error messages in < 1ms |
| GW-004 | Response normalization (Go-side fast path) | P0 | Basic response structure normalization for common providers in Go; complex cases delegated to Python adapters |
| GW-005 | Connection pooling to providers | P0 | Persistent HTTP/2 connections; configurable pool size per provider |
| GW-006 | Request/response logging (async) | P0 | Non-blocking log emission to NATS/Redis Streams; zero impact on latency |
| GW-007 | Graceful degradation | P0 | Gateway returns cached/fallback response if all providers fail |
| GW-008 | Health check endpoint | P0 | `/health` returns 200 with provider status within 50ms |
| GW-009 | Request timeout management | P1 | Configurable per-model timeout; default 120s for text, 300s for video |
| GW-010 | WebSocket support | P1 | For real-time bidirectional streaming (future audio/video) |
| GW-011 | HTTP/3 (QUIC) support | P2 | Reduced connection overhead for mobile clients |
| GW-012 | Gateway overhead < 15µs at 5K RPS | P0 | Verified via sustained benchmarks on c6g.xlarge or equivalent |
| GW-013 | Auth token validation via Redis lookup | P0 | Validate API key hash against Redis cache; fallback to Python auth service if cache miss |
| GW-014 | Rate limit check via Redis | P0 | Sliding window counter check before forwarding request |
| GW-015 | Provider selection via routing rules from config | P0 | Load routing config from YAML + hot-reload on SIGHUP |

### 4.4 Technical Constraints

- Single binary deployment (no external dependencies at runtime)
- Zero heap allocations on hot path where possible — use `sync.Pool` for buffer recycling
- Structured logging via `slog` (Go 1.21+)
- Configuration: YAML file + environment variable overrides + hot-reload
- gRPC or HTTP internal communication to Python backend for complex operations
- The Go gateway does NOT query PostgreSQL directly — all DB access goes through Python backend services

### 4.5 What the Go Gateway Does NOT Do

To keep the hot path fast, these are explicitly delegated to the Python backend:

- User registration, org management
- Billing calculations and Stripe calls
- Complex provider adapter logic (new/experimental providers)
- Semantic caching (embedding generation + vector search)
- Guardrail inference (PII detection, prompt injection classification)
- MCP tool execution
- Prompt management and versioning
- Model evaluation and quality scoring

---

## 5. Module 2 — Backend Services (Python)

### 5.1 Purpose

All business logic, provider adapters, ML-powered features, and data management. Python is the warm path — latency is measured in milliseconds, not microseconds. This is where the AI-specific intelligence lives.

### 5.2 Frameworks & Libraries

| Library | Purpose | License |
|---|---|---|
| **FastAPI** | HTTP framework (async, OpenAPI auto-gen) | MIT |
| **SQLAlchemy 2.0** | ORM with async support | MIT |
| **Alembic** | Database migrations | MIT |
| **Pydantic v2** | Data validation and serialization | MIT |
| **Celery + Redis** | Async task queue (video jobs, webhooks, aggregation) | BSD |
| **httpx** | Async HTTP client for provider calls | BSD |
| **openai** | OpenAI provider SDK | MIT |
| **anthropic** | Anthropic provider SDK | MIT |
| **google-genai** | Google AI provider SDK | Apache 2.0 |
| **mistralai** | Mistral provider SDK | Apache 2.0 |
| **cohere** | Cohere provider SDK | MIT |
| **boto3** | AWS Bedrock provider SDK | Apache 2.0 |
| **tiktoken** | OpenAI tokenizer | MIT |
| **sentence-transformers** | Embedding generation for semantic cache | Apache 2.0 |
| **guardrails-ai** | Input/output validation framework | Apache 2.0 |
| **nemo-guardrails** | Programmable LLM guardrails (NVIDIA) | Apache 2.0 |
| **llm-guard** | Prompt injection and PII detection | MIT |
| **stripe** | Payment processing SDK | MIT |
| **passlib[argon2]** | API key hashing | BSD |
| **python-jose** | JWT token handling | MIT |
| **authlib** | OAuth2/OIDC client | BSD |
| **prometheus-client** | Prometheus metrics | Apache 2.0 |
| **opentelemetry-api** | Distributed tracing | Apache 2.0 |
| **structlog** | Structured logging | MIT |
| **redis[hiredis]** | Redis client (high-performance) | MIT |
| **psycopg[binary]** | PostgreSQL async driver | LGPL |
| **promptfoo** | Prompt evaluation (via subprocess) | MIT |

### 5.3 Service Decomposition

The Python backend is split into focused microservices (can start as a monolith and split later):

```
python-backend/
├── services/
│   ├── auth/              # Authentication, API key management, RBAC
│   │   ├── models.py      # User, Org, Team, APIKey SQLAlchemy models
│   │   ├── service.py     # Auth logic, key generation, hashing
│   │   ├── oauth.py       # OAuth2/OIDC integration
│   │   └── routes.py      # FastAPI routes
│   │
│   ├── billing/           # Metering, credits, Stripe integration
│   │   ├── models.py      # BillingAccount, CreditBalance, Invoice, UsageRecord
│   │   ├── metering.py    # Token counting, cost calculation
│   │   ├── stripe_svc.py  # Stripe API integration
│   │   └── routes.py
│   │
│   ├── providers/         # Provider adapters and normalization
│   │   ├── base.py        # Abstract ProviderAdapter interface
│   │   ├── openai.py      # OpenAI adapter
│   │   ├── anthropic.py   # Anthropic adapter
│   │   ├── google.py      # Google Gemini adapter
│   │   ├── bedrock.py     # AWS Bedrock adapter
│   │   ├── mistral.py     # Mistral adapter
│   │   ├── cohere.py      # Cohere adapter
│   │   ├── groq.py        # Groq adapter
│   │   ├── deepseek.py    # DeepSeek adapter
│   │   ├── together.py    # Together AI adapter
│   │   ├── replicate.py   # Replicate adapter
│   │   └── registry.py    # Dynamic provider registry
│   │
│   ├── routing/           # Intelligent routing engine
│   │   ├── engine.py      # Routing decision logic
│   │   ├── health.py      # Provider health monitoring
│   │   ├── scoring.py     # Provider quality scoring (Auto Exacto)
│   │   ├── semantic.py    # Semantic routing (classify → route)
│   │   └── balancer.py    # Load balancing strategies
│   │
│   ├── cache/             # Semantic caching
│   │   ├── exact.py       # Redis exact-match cache
│   │   ├── semantic.py    # pgvector semantic similarity cache
│   │   └── embeddings.py  # Embedding generation for cache keys
│   │
│   ├── guardrails/        # Safety and compliance
│   │   ├── engine.py      # Guardrail pipeline orchestrator
│   │   ├── pii.py         # PII detection and redaction
│   │   ├── injection.py   # Prompt injection detection
│   │   ├── content.py     # Content safety filters
│   │   └── custom.py      # User-defined custom validators
│   │
│   ├── mcp/               # Model Context Protocol gateway
│   │   ├── server.py      # MCP server implementation
│   │   ├── client.py      # MCP client for connecting to tool servers
│   │   ├── auth.py        # OAuth2 + OBO for MCP
│   │   └── registry.py    # MCP tool registry
│   │
│   ├── prompts/           # Prompt management and versioning
│   │   ├── models.py      # PromptTemplate, PromptVersion
│   │   ├── service.py     # CRUD, versioning, variable substitution
│   │   └── routes.py
│   │
│   ├── models_catalog/    # Model marketplace and discovery
│   │   ├── models.py      # ModelEntry, ProviderEndpoint, Pricing
│   │   ├── rankings.py    # Usage-based rankings
│   │   └── routes.py
│   │
│   ├── video/             # Async video generation job system
│   │   ├── jobs.py        # Job lifecycle (submit, poll, download)
│   │   ├── tasks.py       # Celery tasks for async processing
│   │   └── routes.py
│   │
│   ├── webhooks/          # Outbound webhook delivery
│   │   ├── service.py     # Webhook registration and delivery
│   │   └── tasks.py       # Celery tasks for reliable delivery
│   │
│   └── admin/             # Internal admin operations
│       ├── routes.py      # Admin API endpoints
│       └── service.py     # Model registry mgmt, user mgmt
│
├── core/
│   ├── config.py          # Settings via pydantic-settings
│   ├── database.py        # SQLAlchemy async engine setup
│   ├── redis.py           # Redis connection pool
│   ├── security.py        # Password hashing, JWT signing
│   ├── middleware.py       # CORS, request ID, error handling
│   └── events.py          # Startup/shutdown events
│
├── main.py                # FastAPI application entry point
├── alembic/               # Database migrations
├── tests/                 # pytest test suite
├── pyproject.toml         # Project dependencies (uv/poetry)
└── Dockerfile
```

### 5.4 Domain Model (Core Entities — SQLAlchemy)

```
User ──┬── Organization ──┬── Team ──┬── Project
       │                  │          │
       │                  │          └── APIKey (scoped)
       │                  │
       │                  ├── BillingAccount
       │                  │     ├── CreditBalance
       │                  │     ├── Invoice
       │                  │     ├── UsageRecord
       │                  │     └── PaymentMethod (Stripe)
       │                  │
       │                  ├── Policy
       │                  │     ├── RateLimit
       │                  │     ├── BudgetLimit
       │                  │     ├── ModelAllowlist
       │                  │     └── GuardrailConfig
       │                  │
       │                  └── AuditLog
       │
       └── Preferences
             ├── DefaultModel
             ├── FallbackChain
             └── RoutingPreferences

ModelEntry
  ├── model_id (e.g., "anthropic/claude-sonnet-4-20250514")
  ├── provider
  ├── modalities (text, image, video, audio, embeddings)
  ├── pricing (input_per_token, output_per_token)
  ├── context_window
  ├── supported_features (tools, structured_output, streaming, vision)
  └── ProviderEndpoint[]

PromptTemplate
  ├── name, description
  ├── PromptVersion[]
  │     ├── version_number
  │     ├── content (with {{variable}} placeholders)
  │     ├── environment (dev/staging/prod)
  │     └── metrics (avg_latency, avg_cost, quality_score)
  └── A/B test configuration

VideoJob
  ├── job_id, status (pending/processing/completed/failed)
  ├── model, prompt, parameters
  ├── output_urls[]
  └── cost, duration
```

### 5.5 Key Python Backend Requirements

| ID | Requirement | Priority |
|---|---|---|
| PY-001 | FastAPI application with async endpoints | P0 |
| PY-002 | SQLAlchemy 2.0 async ORM with PostgreSQL | P0 |
| PY-003 | Alembic database migrations | P0 |
| PY-004 | Pydantic v2 request/response models | P0 |
| PY-005 | Provider adapter plugin architecture (base class + registry) | P0 |
| PY-006 | Celery task queue for async jobs (video gen, webhooks, aggregation) | P1 |
| PY-007 | API key hashing with argon2id via passlib | P0 |
| PY-008 | OAuth2/OIDC integration via authlib | P1 |
| PY-009 | RBAC middleware with role/permission checks | P0 |
| PY-010 | Audit logging decorator for all mutation endpoints | P0 |
| PY-011 | Stripe SDK integration for billing | P0 |
| PY-012 | tiktoken for OpenAI token counting | P0 |
| PY-013 | sentence-transformers for semantic cache embeddings | P1 |
| PY-014 | guardrails-ai + llm-guard for input/output safety | P1 |
| PY-015 | Structured logging via structlog | P0 |
| PY-016 | Prometheus metrics via prometheus-client | P0 |
| PY-017 | OpenTelemetry tracing | P0 |
| PY-018 | Health check endpoint with dependency status | P0 |
| PY-019 | gRPC server for Go gateway communication (or HTTP internal API) | P0 |
| PY-020 | Auto-generated OpenAPI spec from FastAPI | P0 |

### 5.6 Python Performance Considerations

The Python backend is NOT in the hot path — the Go gateway handles all latency-critical proxying. Python handles business logic where latency of 10-100ms is acceptable.

- Use `asyncio` everywhere — FastAPI with `uvicorn` workers
- Use `httpx.AsyncClient` with connection pooling for provider calls
- Use Redis for caching frequently accessed data (API key metadata, model registry)
- Deploy with `gunicorn` + `uvicorn` workers (4-8 per CPU core)
- For CPU-bound ML tasks (embedding generation, guardrail inference), use Celery workers with dedicated compute
- GIL mitigation: multiprocessing via gunicorn workers, not threading
- Consider PyPy or Cython for hot loops if profiling shows bottlenecks

---

## 6. Module 3 — Frontend & Developer Portal (TypeScript)

### 6.1 Purpose

All user-facing web interfaces, developer documentation, interactive tools, and CLI. TypeScript/Next.js provides server-side rendering, static generation for docs, and React for interactive components.

### 6.2 Frameworks & Libraries

| Library | Purpose |
|---|---|
| **Next.js 15** | Full-stack React framework (SSR, SSG, API routes) |
| **React 19** | UI components |
| **Tailwind CSS 4** | Utility-first styling |
| **shadcn/ui** | Component library |
| **Recharts / D3.js** | Charts and data visualization |
| **Monaco Editor** | Code editor for playground and prompt editor |
| **Vercel AI SDK** | Streaming chat UI components |
| **next-auth** | Authentication (OAuth2, magic links) |
| **SWR / TanStack Query** | Data fetching and caching |
| **Fumadocs / Nextra** | Documentation site generator |
| **Stripe.js** | Client-side payment integration |
| **Playwright** | E2E testing |

### 6.3 Frontend Applications

| Application | Route | Description | Priority |
|---|---|---|---|
| Landing page | `/` | Product overview, pricing, features | P0 |
| Documentation | `/docs` | API reference, guides, tutorials (MDX) | P0 |
| Dashboard | `/dashboard` | Usage analytics, billing, API keys | P0 |
| Playground | `/playground` | Interactive model testing (text, image, video, audio) | P0 |
| Model marketplace | `/models` | Browse, search, filter, compare models | P0 |
| Admin panel | `/admin` | Internal admin operations (protected) | P1 |
| Status page | `/status` | Provider uptime and incident history | P1 |
| Changelog | `/changelog` | Product updates and announcements | P1 |
| Pricing | `/pricing` | Plans, pricing calculator | P0 |

### 6.4 Frontend Requirements

| ID | Requirement | Priority |
|---|---|---|
| FE-001 | Responsive design (desktop + mobile) | P0 |
| FE-002 | Dark/light mode support | P0 |
| FE-003 | Real-time streaming chat in playground (Vercel AI SDK) | P0 |
| FE-004 | API key management UI (create, revoke, view usage) | P0 |
| FE-005 | Usage charts (tokens, requests, cost by day/week/month) | P0 |
| FE-006 | Model comparison tool (side-by-side pricing, speed, quality) | P1 |
| FE-007 | Request builder with code snippets (Python, JS, cURL, Go) | P0 |
| FE-008 | Video playground: submit prompt, poll status, preview result | P1 |
| FE-009 | Image playground: generate and display images inline | P1 |
| FE-010 | Billing UI: credit balance, purchase credits, invoices | P0 |
| FE-011 | Team management: invite members, assign roles | P1 |
| FE-012 | OAuth2 login (Google, GitHub, email/password) | P0 |
| FE-013 | Internationalization (i18n) support | P2 |
| FE-014 | Keyboard shortcuts for playground | P2 |
| FE-015 | OpenAPI-generated interactive docs | P0 |

### 6.5 CLI Tool (TypeScript / Node.js)

```bash
npx @openrouter/cli
```

| ID | Feature | Priority |
|---|---|---|
| CLI-001 | `login` — authenticate via browser OAuth flow | P2 |
| CLI-002 | `models list` — list available models with pricing | P2 |
| CLI-003 | `chat` — interactive terminal chat with any model | P2 |
| CLI-004 | `usage` — display usage stats for current billing period | P2 |
| CLI-005 | `keys create/list/revoke` — API key management | P2 |

---

## 7. Module 4 — Provider Integration Layer

### 7.1 Supported Providers (Launch Target: 20+, Year 1: 60+)

#### Tier 1 — Day One (Must Have)

| Provider | Models | Auth Type | Modalities | SDK |
|---|---|---|---|---|
| OpenAI | GPT-4o, GPT-5, o-series, DALL-E, Whisper, TTS, Sora | Bearer token | Text, Image, Audio, Video | `openai` |
| Anthropic | Claude Opus, Sonnet, Haiku | x-api-key | Text, Image (input) | `anthropic` |
| Google | Gemini Pro, Flash, Ultra, Veo, Imagen | Bearer/OAuth | Text, Image, Audio, Video | `google-genai` |
| AWS Bedrock | Claude, Llama, Titan, Cohere, Mistral | AWS SigV4 | Text, Image, Embeddings | `boto3` |
| Azure OpenAI | GPT-4o, GPT-5, DALL-E, Whisper | Azure AD / API key | Text, Image, Audio | `openai` (Azure config) |

#### Tier 2 — Month 1-3

| Provider | Models | SDK |
|---|---|---|
| Mistral AI | Mistral Large, Medium, Codestral | `mistralai` |
| Cohere | Command R+, Embed, Rerank | `cohere` |
| Groq | Llama, Mixtral (ultra-fast inference) | `openai` (compatible) |
| Together AI | Open-source model hosting | `together` / `openai` |
| DeepSeek | DeepSeek-V3, DeepSeek-R1 | `openai` (compatible) |
| xAI | Grok-3 | `openai` (compatible) |

#### Tier 3 — Month 3-6

| Provider | Models | SDK |
|---|---|---|
| Fireworks AI | Fine-tuned model hosting | `openai` (compatible) |
| Replicate | Community model marketplace | `replicate` |
| Perplexity | pplx-online (search-augmented) | `openai` (compatible) |
| Alibaba (Qwen) | Qwen 3, Wan video models | Custom |
| ByteDance | Seedance video models | Custom |
| Ollama | Local/self-hosted open-source | `openai` (compatible) |
| Cerebras | Ultra-fast inference | `cerebras` |
| HuggingFace | Community model hosting | `huggingface_hub` |

### 7.2 Provider Adapter Interface (Python)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from pydantic import BaseModel

class ProviderAdapter(ABC):
    """Base class for all provider adapters."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def supported_modalities(self) -> list[str]: ...

    @abstractmethod
    async def normalize_request(self, unified_request: UnifiedRequest) -> dict:
        """Convert unified schema to provider-specific request."""
        ...

    @abstractmethod
    async def normalize_response(self, provider_response: dict) -> UnifiedResponse:
        """Convert provider-specific response to unified schema."""
        ...

    @abstractmethod
    async def stream_response(self, provider_stream) -> AsyncIterator[UnifiedChunk]:
        """Normalize streaming SSE chunks."""
        ...

    @abstractmethod
    async def count_tokens(self, messages: list[dict]) -> TokenCount:
        """Count input tokens using provider-native tokenizer."""
        ...

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Ping provider and measure latency."""
        ...

    @abstractmethod
    def pricing(self, model: str) -> PricingTier:
        """Return per-token pricing for a model."""
        ...
```

### 7.3 Schema Normalization Requirements

| ID | Requirement | Priority |
|---|---|---|
| PI-001 | Normalize all provider request schemas to OpenAI chat completions format | P0 |
| PI-002 | Normalize all provider response schemas to OpenAI response format | P0 |
| PI-003 | Handle provider-specific parameters via `provider` passthrough object | P0 |
| PI-004 | Translate tool/function calling schemas across providers | P0 |
| PI-005 | Handle structured output / JSON mode differences | P0 |
| PI-006 | Normalize finish reasons to: `stop`, `length`, `tool_calls`, `content_filter`, `error` | P0 |
| PI-007 | Translate token counts using provider-native tokenizers (tiktoken, etc.) | P0 |
| PI-008 | Support provider-specific features (e.g., Anthropic prompt caching, Google grounding) | P1 |
| PI-009 | Handle multimodal content blocks (image, audio, video, PDF) consistently | P0 |
| PI-010 | Auto-detect and handle provider API version changes without breaking clients | P1 |

### 7.4 Adding a New Provider (Developer Guide)

Adding a new provider should take < 1 day:

1. Create `providers/{name}.py` extending `ProviderAdapter`
2. Implement `normalize_request` and `normalize_response`
3. Add provider to `registry.py`
4. Add model entries to `models_catalog`
5. Write adapter tests with mock responses
6. Add provider API key to Vault
7. Deploy — Go gateway picks up new provider via config hot-reload

---

## 8. Module 5 — Multimodal API Surface

### 8.1 Text Generation (Synchronous + Streaming)

```
POST /api/v1/chat/completions
```

- Standard chat completions with messages array
- Streaming via SSE (`stream: true`)
- Structured outputs (`response_format: { type: "json_schema", json_schema: {...} }`)
- Tool/function calling with parallel tool calls
- System, user, assistant, tool message roles
- Temperature, top_p, top_k, frequency_penalty, presence_penalty, max_tokens
- Logprobs support
- Stop sequences
- Reasoning effort parameter (for reasoning models like o-series, DeepSeek-R1)
- Reasoning token tracking in usage response

### 8.2 Image Generation

```
POST /api/v1/images/generations
```

- Text-to-image
- Image-to-image (editing, variation)
- Configurable: size, quality, style, number of images
- Supported models: DALL-E 3, Imagen 3, Stable Diffusion, Flux
- Response: base64 or URL

### 8.3 Video Generation (Asynchronous)

```
POST /api/v1/videos                        # Submit generation job
GET  /api/v1/videos/{job_id}               # Poll job status
GET  /api/v1/videos/{job_id}/content       # Download completed video
GET  /api/v1/videos/models                 # List video models & capabilities
```

- Text-to-video and image-to-video
- Asynchronous job-based workflow (submit → poll → download)
- Normalized parameters: resolution, duration, aspect_ratio, fps
- Frame image support: `frame_images` with `first_frame` / `last_frame`
- Reference images: `input_references` for style/content guidance
- Provider-specific passthrough via `provider` object
- Job status lifecycle: `pending` → `processing` → `completed` / `failed`
- `unsigned_urls` array in completed response for download
- Supported models: Sora 2 Pro, Veo 3.1, Wan 2.6/2.7, Seedance 2.0/1.5
- Video storage on S3 with signed download URLs (24-hour expiry)
- Celery worker processes async job lifecycle

### 8.4 Audio

```
POST /api/v1/audio/transcriptions     # Speech-to-text (Whisper-compatible)
POST /api/v1/audio/translations       # Speech translation
POST /api/v1/audio/speech             # Text-to-speech
POST /api/v1/chat/completions         # Audio I/O via content blocks
```

- Whisper-compatible transcription API
- Text-to-speech with voice selection and format (MP3, WAV, PCM16)
- Audio input/output in chat completions (Gemini, GPT-4o audio)
- Supported formats: WAV, MP3, FLAC, OGG, PCM16
- Audio files stored on S3 with signed URLs

### 8.5 Embeddings

```
POST /api/v1/embeddings
```

- Text embeddings for vector search and RAG
- Batch embedding support
- Dimension specification (for models with variable dimensions)
- Supported models: text-embedding-3-small/large, Cohere embed-v4, Voyage AI

### 8.6 Reranking

```
POST /api/v1/rerank
```

- Document reranking for search and RAG pipelines
- Input: query + documents array
- Output: reranked documents with relevance scores
- Supported models: Cohere rerank-v3.5, Jina reranker

### 8.7 PDF & Document Processing

- PDF input in chat completions via base64 content blocks
- Intelligent PDF parsing (text extraction + OCR for scanned)
- Page-level processing for large documents

---

## 9. Module 6 — Routing & Load Balancing Engine

### 9.1 Routing Strategies

| ID | Strategy | Description | Priority | Implementation |
|---|---|---|---|---|
| RT-001 | Explicit model routing | User specifies `model: "anthropic/claude-sonnet-4-20250514"` | P0 | Go gateway |
| RT-002 | Auto routing | `model: "openrouter/auto"` — system selects best model | P1 | Python routing engine |
| RT-003 | Fallback chain | Ordered fallback: `[claude, gpt-4o, gemini]` | P0 | Go gateway |
| RT-004 | Cost-optimized | Route to cheapest provider for requested model | P0 | Go gateway (config-driven) |
| RT-005 | Latency-optimized | Route to fastest provider based on real-time health | P1 | Go gateway (health scores from Python) |
| RT-006 | Quality-optimized | Route based on benchmark + real usage quality | P2 | Python scoring engine |
| RT-007 | Geo-aware | Route to provider endpoints closest to user | P1 | Go gateway (GeoIP → provider region map) |
| RT-008 | Data-residency | Ensure requests only go to providers in specified jurisdictions | P1 | Go gateway (policy from Python) |
| RT-009 | Semantic routing | Classify request complexity → route to appropriate model tier | P2 | Python ML classifier |
| RT-010 | Canary routing | Send % of traffic to new model for A/B testing | P2 | Go gateway (weighted random) |

### 9.2 Auto Exacto (Real-Time Provider Scoring)

Python background service that re-evaluates providers every 5 minutes:

```python
class ProviderScorer:
    """
    Score = w1 * throughput_score
          + w2 * tool_call_success_rate
          + w3 * benchmark_score
          + w4 * uptime_score
          - penalty * recent_error_rate
    """

    async def score_provider(self, provider: str, model: str) -> float:
        throughput = await self.get_throughput_percentile(provider, model)
        tool_success = await self.get_tool_call_telemetry(provider, model)
        benchmark = await self.get_benchmark_score(model)
        uptime = await self.get_uptime(provider, model)
        errors = await self.get_recent_error_rate(provider, model)

        return (
            0.25 * throughput
            + 0.30 * tool_success
            + 0.20 * benchmark
            + 0.15 * uptime
            - 0.10 * errors
        )
```

- Scores published to Redis; Go gateway reads them for routing decisions
- Auto-enabled for requests that include tools
- Dashboard shows provider scores per model

### 9.3 Load Balancing

| ID | Requirement | Priority |
|---|---|---|
| LB-001 | Weighted round-robin across providers for same model | P0 |
| LB-002 | API key rotation (distribute across multiple keys per provider) | P0 |
| LB-003 | Circuit breaker (open after N failures, half-open to test recovery) | P0 |
| LB-004 | Adaptive load balancing based on real-time latency | P1 |
| LB-005 | Provider health scoring updated every 30 seconds | P0 |
| LB-006 | Graceful backpressure during provider rate limiting | P0 |

### 9.4 Failover Logic (Implemented in Go Gateway)

```
1. Receive request for model X
2. Select primary provider based on routing strategy
   (read provider scores + routing config from Redis)
3. Send request to primary provider
4. IF response is 5xx, timeout, or 429:
   a. Mark provider as degraded (Redis health key)
   b. Open circuit breaker if failures > threshold
   c. Select next provider from fallback chain
   d. Retry request (max 2 retries)
5. IF all providers fail:
   a. Check exact-match cache
   b. Return 503 with clear error + Retry-After header
6. Emit routing event to NATS for async logging
```

---

## 10. Module 7 — Caching System

### 10.1 Dual-Layer Cache Architecture

| Layer | Type | Storage | Implementation | Hit Latency |
|---|---|---|---|---|
| L1 | Exact match | Redis | Go gateway — `SHA-256(model + messages + params)` | < 1ms |
| L2 | Semantic match | pgvector | Python service — embedding cosine similarity > 0.85 threshold | < 10ms |

### 10.2 Requirements

| ID | Requirement | Priority |
|---|---|---|
| CA-001 | Exact-match cache with configurable TTL per model | P0 |
| CA-002 | Semantic cache using sentence-transformers embeddings | P1 |
| CA-003 | Cache invalidation on model version updates | P0 |
| CA-004 | Per-user cache opt-out via header (`X-No-Cache: true`) | P0 |
| CA-005 | Cache hit/miss metrics exposed to Prometheus | P0 |
| CA-006 | Cache warming for popular queries | P2 |
| CA-007 | Provider-side prompt caching passthrough (Anthropic, OpenAI) | P1 |
| CA-008 | Cache storage limits and LRU eviction | P0 |
| CA-009 | Configurable similarity threshold per org | P2 |

### 10.3 Cache Flow

```
Request arrives at Go gateway
  │
  ├── Compute hash = SHA-256(model + messages + params)
  ├── L1: Redis GET hash
  │     ├── HIT → Return cached response (free, < 1ms)
  │     └── MISS → Continue
  │
  ├── L2: Call Python semantic cache service (if enabled)
  │     ├── Python generates embedding via sentence-transformers
  │     ├── pgvector cosine similarity search
  │     ├── HIT (similarity > threshold) → Return cached response
  │     └── MISS → Continue
  │
  ├── Route to provider → Get response
  │
  ├── Async: Store in L1 (Redis SET with TTL)
  ├── Async: Store embedding + response in L2 (pgvector INSERT)
  └── Return response to client
```

---

## 11. Module 8 — Authentication & API Key Management

### 11.1 API Key Types

| Key Type | Scope | Use Case |
|---|---|---|
| Personal key | Single user | Individual developer usage |
| Project key | Specific project | Application-specific access |
| Team key | All projects within a team | Team-wide access |
| Admin key | Full org access | Administrative operations |
| BYOK passthrough | User's own provider key | Direct provider billing |

### 11.2 Requirements

| ID | Requirement | Priority |
|---|---|---|
| AK-001 | Key format: `sk-or-v1-{random_64_hex_chars}` | P0 |
| AK-002 | Key hashing with argon2id — never store plaintext | P0 |
| AK-003 | Key creation with optional: name, expiry, model allowlist, rate limit, budget | P0 |
| AK-004 | Key revocation (immediate — propagated to Redis in < 5s) | P0 |
| AK-005 | Key rotation with grace period (old key valid for N hours) | P1 |
| AK-006 | OAuth2/OIDC token authentication (via authlib) | P1 |
| AK-007 | BYOK: accept user's own provider key in header, bypass billing | P1 |
| AK-008 | Key usage analytics (requests, tokens, cost per key) | P0 |
| AK-009 | IP allowlisting per key | P2 |
| AK-010 | Key permissions: model allowlist/denylist per key | P1 |

### 11.3 Auth Flow

```
1. Client sends request with header: Authorization: Bearer sk-or-v1-{key}
2. Go gateway extracts key, computes hash
3. Redis lookup: GET auth:{key_hash}
   ├── HIT → Get key metadata (org_id, permissions, rate limits, budget)
   └── MISS → Call Python auth service → Cache result in Redis (TTL 60s)
4. Validate: key not expired, not revoked, model allowed, budget remaining
5. If valid → proceed with request
6. If invalid → return 401/403 with specific error message
```

---

## 12. Module 9 — Billing, Metering & Cost Control

### 12.1 Billing Model

- Credits-based prepaid system (1 credit = $1 USD)
- Platform fee: configurable % on credit purchases (OpenRouter charges 5.5%)
- Pay-as-you-go: charge provider rate per model per token
- Enterprise: custom contracts with monthly invoicing

### 12.2 Requirements

| ID | Requirement | Priority |
|---|---|---|
| BL-001 | Token-level metering per request (input, output, cached, reasoning) | P0 |
| BL-002 | Real-time cost calculation based on model pricing | P0 |
| BL-003 | Credit balance management with low-balance alerts | P0 |
| BL-004 | Stripe integration (Python `stripe` SDK) for payments | P0 |
| BL-005 | Invoice generation (monthly, per-org) | P1 |
| BL-006 | Cost allocation by team, project, and API key | P1 |
| BL-007 | Hierarchical budget limits: org → team → project → key | P1 |
| BL-008 | Hard spending caps (reject requests when budget exhausted) | P0 |
| BL-009 | Soft spending alerts (email/webhook at 50%, 80%, 100%) | P1 |
| BL-010 | Free tier: configurable limits for new accounts | P0 |
| BL-011 | `GET /api/v1/models` includes per-token pricing | P0 |
| BL-012 | Usage export (CSV/JSON) for accounting | P1 |
| BL-013 | Video billing: per-second pricing with resolution multipliers | P0 |
| BL-014 | Image billing: per-image pricing with quality/size tiers | P0 |

### 12.3 Token Counting (Python)

```python
import tiktoken

class TokenCounter:
    """Count tokens using provider-native tokenizers."""

    def count_openai(self, messages: list[dict], model: str) -> int:
        enc = tiktoken.encoding_for_model(model)
        return sum(len(enc.encode(m["content"])) for m in messages)

    def count_anthropic(self, messages: list[dict]) -> int:
        # Use Anthropic's tokenizer or approximate via tiktoken cl100k
        ...

    def count_from_response(self, response: dict) -> TokenUsage:
        """Extract token counts from provider response usage object."""
        return TokenUsage(
            input_tokens=response["usage"]["prompt_tokens"],
            output_tokens=response["usage"]["completion_tokens"],
            cached_tokens=response["usage"].get("cached_tokens", 0),
            reasoning_tokens=response["usage"].get("reasoning_tokens", 0),
        )
```

### 12.4 Metering Pipeline

```
Request completes → Go gateway emits usage event to NATS
  │
  └── Python metering worker consumes event
        ├── Count tokens (provider-reported or tiktoken)
        ├── Calculate cost = tokens × model_price_per_token
        ├── Deduct from credit balance (PostgreSQL UPDATE)
        ├── Write UsageRecord to PostgreSQL
        ├── Update Redis budget counters
        └── Check budget thresholds → send alerts if needed
```

---

## 13. Module 10 — Rate Limiting & Throttling

### 13.1 Rate Limit Dimensions

| Dimension | Scope | Implementation |
|---|---|---|
| Requests per minute (RPM) | Per API key | Redis sliding window (Go gateway) |
| Tokens per minute (TPM) | Per API key | Redis token bucket (Go gateway) |
| Requests per minute | Per model | Prevent single model overload |
| Concurrent requests | Per API key | Redis semaphore (Go gateway) |
| Requests per day | Per free-tier key | Redis daily counter |

### 13.2 Requirements

| ID | Requirement | Priority |
|---|---|---|
| RL-001 | Configurable rate limits per key, per model, per org | P0 |
| RL-002 | Return 429 with `Retry-After` header and clear error | P0 |
| RL-003 | Rate limit headers on every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` | P0 |
| RL-004 | Free tier defaults: 20 RPM, 50 requests/day | P0 |
| RL-005 | Burst allowance: 2x normal rate for 10-second window | P1 |
| RL-006 | Provider-side rate limit detection and backoff (Go gateway) | P0 |
| RL-007 | Rate limit dashboard (TypeScript frontend) | P1 |

---

## 14. Module 11 — Guardrails, Safety & Compliance

### 14.1 Input Guardrails (Python)

| ID | Guardrail | Tool | Priority |
|---|---|---|---|
| GR-001 | Prompt injection detection | `llm-guard` / custom classifier | P0 |
| GR-002 | PII detection and redaction | `presidio` / `llm-guard` | P1 |
| GR-003 | Content policy enforcement | `guardrails-ai` validators | P1 |
| GR-004 | Token limit enforcement | `tiktoken` count check | P0 |
| GR-005 | Model allowlist/denylist | Policy engine | P0 |
| GR-006 | Custom input validators | User-defined regex/keyword filters | P2 |

### 14.2 Output Guardrails (Python)

| ID | Guardrail | Tool | Priority |
|---|---|---|---|
| GR-007 | Content safety filtering | `guardrails-ai` / `nemo-guardrails` | P1 |
| GR-008 | PII detection in responses | `presidio` / `llm-guard` | P1 |
| GR-009 | Hallucination detection | Grounding comparison (RAG) | P2 |
| GR-010 | Schema validation for structured outputs | `pydantic` / `jsonschema` | P1 |
| GR-011 | Data exfiltration prevention | Custom heuristics | P2 |

### 14.3 Guardrail Pipeline Architecture (Python)

```python
class GuardrailPipeline:
    """Ordered chain of input/output validators."""

    def __init__(self, config: GuardrailConfig):
        self.input_guards = []
        self.output_guards = []

        if config.pii_detection:
            self.input_guards.append(PIIDetector())
        if config.injection_detection:
            self.input_guards.append(InjectionDetector())
        if config.content_policy:
            self.input_guards.append(ContentPolicyChecker(config.content_policy))
        if config.pii_output_detection:
            self.output_guards.append(PIIDetector())
        if config.content_safety:
            self.output_guards.append(ContentSafetyFilter())

    async def check_input(self, request: UnifiedRequest) -> GuardrailResult:
        for guard in self.input_guards:
            result = await guard.check(request)
            if result.blocked:
                return result  # Stop early, return violation
        return GuardrailResult(passed=True)

    async def check_output(self, response: UnifiedResponse) -> GuardrailResult:
        for guard in self.output_guards:
            result = await guard.check(response)
            if result.blocked:
                return result
        return GuardrailResult(passed=True)
```

### 14.4 Compliance

| ID | Requirement | Priority |
|---|---|---|
| CO-001 | SOC 2 Type II audit readiness | P1 |
| CO-002 | GDPR — data residency, right to deletion, DPA | P1 |
| CO-003 | HIPAA — BAA support, PHI handling | P2 |
| CO-004 | ISO 27001 alignment | P2 |
| CO-005 | Content provenance metadata (C2PA, SynthID) for generated media | P2 |
| CO-006 | Configurable log retention per org | P1 |
| CO-007 | Complete audit trail for all admin operations | P0 |

---

## 15. Module 12 — MCP Gateway (Model Context Protocol)

### 15.1 Purpose

Serve as an MCP server and client, enabling AI agents to access external tools and data sources through a governed, centralized gateway. Implemented in Python for access to the full MCP ecosystem.

### 15.2 Requirements

| ID | Requirement | Priority |
|---|---|---|
| MCP-001 | MCP server exposing gateway capabilities as tools | P1 |
| MCP-002 | MCP client for connecting to external tool servers | P1 |
| MCP-003 | Transports: Streamable HTTP (modern) + SSE (compat) + stdio | P1 |
| MCP-004 | Agent Mode: autonomous tool execution with auto-approval config | P2 |
| MCP-005 | Code Mode: AI writes Python to orchestrate tools in one pass (50% fewer tokens, 40% lower latency) | P2 |
| MCP-006 | Federated auth: OAuth 2.0 with PKCE + automatic token refresh | P1 |
| MCP-007 | On-behalf-of (OBO): execute with requesting user's permissions | P1 |
| MCP-008 | Tool filtering: restrict MCP tools per key/org via policy | P1 |
| MCP-009 | MCP call logging and observability | P1 |
| MCP-010 | REST-to-MCP bridge: expose existing REST APIs as MCP tools without code changes | P2 |

### 15.3 Python MCP Implementation

```python
from mcp import Server, Tool
from mcp.transports import StreamableHTTPTransport

class GatewayMCPServer:
    """Expose gateway capabilities as MCP tools."""

    def __init__(self):
        self.server = Server("openrouter-gateway")
        self.register_tools()

    def register_tools(self):
        @self.server.tool("chat_completion")
        async def chat(model: str, messages: list[dict]) -> str:
            """Send a chat completion request through the gateway."""
            ...

        @self.server.tool("list_models")
        async def list_models(modality: str = "text") -> list[dict]:
            """List available models filtered by modality."""
            ...

        @self.server.tool("generate_image")
        async def generate_image(prompt: str, model: str) -> str:
            """Generate an image and return URL."""
            ...
```

---

## 16. Module 13 — Agentic Workflow Support

### 16.1 Purpose

Support multi-step agent workflows where a single user request triggers dozens of LLM calls, tool invocations, and reasoning chains.

### 16.2 Requirements

| ID | Requirement | Priority |
|---|---|---|
| AG-001 | Session tracking across multi-step agent workflows | P1 |
| AG-002 | Session-level cost aggregation | P1 |
| AG-003 | Per-session rate limits and budget caps | P1 |
| AG-004 | Agent tracing: full trace of model calls, tool uses, data access | P1 |
| AG-005 | Mixed-model sessions (Claude → Haiku → tool → verify) | P1 |
| AG-006 | Agent guardrails: limit max steps, max tool calls, max tokens per session | P1 |
| AG-007 | Framework compatibility: LangChain, LangGraph, CrewAI, OpenAI Agents SDK, Vercel AI SDK | P1 |
| AG-008 | Reasoning token tracking for o-series, DeepSeek-R1 | P0 |

### 16.3 Session Implementation

```python
class AgentSession:
    session_id: str
    org_id: str
    key_id: str
    started_at: datetime
    steps: list[SessionStep]  # Each LLM call or tool invocation
    total_tokens: int
    total_cost: float
    max_steps: int            # Guardrail
    max_cost: float           # Budget cap
    status: str               # active, completed, budget_exceeded, step_limit
```

---

## 17. Module 14 — Observability & Monitoring

### 17.1 Metrics (Prometheus)

| Metric | Type | Labels | Emitted By |
|---|---|---|---|
| `gateway_requests_total` | Counter | model, provider, status, key_id | Go |
| `gateway_request_duration_seconds` | Histogram | model, provider, cache_hit | Go |
| `gateway_tokens_total` | Counter | model, provider, direction, key_id | Python |
| `gateway_cost_dollars` | Counter | model, provider, key_id, org_id | Python |
| `gateway_errors_total` | Counter | model, provider, error_type | Go |
| `gateway_cache_hits_total` | Counter | cache_layer (L1/L2), model | Go / Python |
| `provider_health_score` | Gauge | provider, model | Python |
| `provider_latency_seconds` | Histogram | provider, model | Go |
| `active_connections` | Gauge | provider | Go |
| `rate_limit_rejections_total` | Counter | key_id, limit_type | Go |
| `guardrail_blocks_total` | Counter | guardrail_type, model | Python |
| `video_jobs_total` | Counter | model, status | Python |

### 17.2 Distributed Tracing (OpenTelemetry)

| ID | Requirement | Emitted By | Priority |
|---|---|---|---|
| OB-001 | End-to-end trace: client → gateway → routing → provider → response | Go + Python | P0 |
| OB-002 | Span attributes: model, provider, tokens, cost, cache_hit, routing_decision | Go + Python | P0 |
| OB-003 | Agent session tracing: link all spans within a session | Python | P1 |
| OB-004 | Export to Grafana Tempo / Jaeger / Datadog | Both | P0 |
| OB-005 | MCP tool call spans with input/output capture | Python | P1 |

### 17.3 Logging

| ID | Requirement | Implementation | Priority |
|---|---|---|---|
| OB-006 | Structured JSON logging | Go: `slog`, Python: `structlog` | P0 |
| OB-007 | Configurable log levels per component | Both | P0 |
| OB-008 | Centralized aggregation via Grafana Loki | Both | P0 |
| OB-009 | Prompt/response logging (opt-in, PII redacted) | Python | P1 |
| OB-010 | Log retention policies per org (GDPR) | Python | P1 |

### 17.4 Alerting

- P95 latency exceeds threshold → PagerDuty/Slack
- Provider error rate > 5% → Circuit breaker + alert
- Credit balance below threshold → Email + webhook
- Unusual usage spike → Abuse detection alert
- Video job failure rate > 10% → Alert

---

## 18. Module 15 — Developer Experience (DX)

### 18.1 SDK Compatibility

| ID | Requirement | Priority |
|---|---|---|
| DX-001 | OpenAI Python SDK works by changing only `base_url` | P0 |
| DX-002 | OpenAI Node.js SDK works by changing only `baseURL` | P0 |
| DX-003 | Anthropic SDK compatibility for Claude-specific features | P1 |
| DX-004 | cURL works with standard OpenAI request format | P0 |
| DX-005 | Framework support: LangChain, LlamaIndex, Vercel AI SDK | P1 |
| DX-006 | Coding agent support: Claude Code, Cursor, Aider, Continue.dev | P1 |

### 18.2 Developer Portal (TypeScript / Next.js)

| ID | Requirement | Priority |
|---|---|---|
| DX-007 | Interactive API docs (OpenAPI spec from FastAPI) | P0 |
| DX-008 | API playground: test any model from browser | P0 |
| DX-009 | Request builder with code snippets (Python, JS, cURL, Go) | P0 |
| DX-010 | Model comparison (side-by-side pricing, speed, quality) | P1 |
| DX-011 | Quickstart guides per language and framework | P0 |
| DX-012 | Changelog and status page | P0 |
| DX-013 | Community (Discord/Slack) integration | P2 |
| DX-014 | Video playground: submit, poll, preview | P1 |

### 18.3 Prompt Management

| ID | Requirement | Priority |
|---|---|---|
| PM-001 | Create, version, and store prompt templates | P2 |
| PM-002 | Variable substitution (`{{user_name}}`, `{{context}}`) | P2 |
| PM-003 | Environment promotion: dev → staging → production | P2 |
| PM-004 | A/B testing of prompt versions | P2 |
| PM-005 | Prompt performance analytics per version | P2 |
| PM-006 | Invoke via header: `X-Prompt-Version: v3` | P2 |

---

## 19. Module 16 — Marketplace & Model Discovery

### 19.1 Requirements

| ID | Requirement | Priority |
|---|---|---|
| MK-001 | Model catalog with search, filter, sort (TypeScript frontend) | P0 |
| MK-002 | Filter by: modality, provider, pricing, context window, features | P0 |
| MK-003 | Rankings based on real usage data (tokens processed, app count) | P1 |
| MK-004 | Model detail pages: pricing, capabilities, playground, performance | P0 |
| MK-005 | Provider uptime tracking per model | P1 |
| MK-006 | Performance benchmarks (latency, throughput) per provider | P1 |
| MK-007 | App attribution: which apps use which models (leaderboard) | P2 |
| MK-008 | Curated collections: "Best for coding", "Free models", "Video models" | P1 |
| MK-009 | Trending models and new model announcements | P1 |
| MK-010 | API: `GET /api/v1/models` returns full catalog with pricing | P0 |

---

## 20. Module 17 — Admin Dashboard & Analytics

### 20.1 User-Facing Dashboard (TypeScript)

| ID | Feature | Priority |
|---|---|---|
| AD-001 | Usage overview: tokens, requests, cost — daily/weekly/monthly | P0 |
| AD-002 | Per-model usage breakdown with cost attribution | P0 |
| AD-003 | API key management UI | P0 |
| AD-004 | Credit balance and billing history | P0 |
| AD-005 | Rate limit status visualization | P1 |
| AD-006 | Team/project-level usage breakdown | P1 |
| AD-007 | Request logs viewer with search | P1 |
| AD-008 | Cost alerts configuration | P1 |

### 20.2 Internal Admin Dashboard (TypeScript — protected)

| ID | Feature | Priority |
|---|---|---|
| AD-009 | Platform-wide metrics: total tokens, revenue, active users | P0 |
| AD-010 | Provider health dashboard | P0 |
| AD-011 | Model registry management (add/update/disable) | P0 |
| AD-012 | User management (view/edit/suspend) | P0 |
| AD-013 | Pricing management | P0 |
| AD-014 | Abuse detection and flagging | P1 |
| AD-015 | Revenue analytics: GMV, margin per model, provider costs | P1 |

---

## 21. Module 18 — Security Infrastructure

### 21.1 Requirements

| ID | Requirement | Implementation | Priority |
|---|---|---|---|
| SE-001 | TLS 1.3 everywhere | Cloudflare / Nginx | P0 |
| SE-002 | AES-256 encryption at rest | PostgreSQL TDE / AWS RDS | P0 |
| SE-003 | Secret management | HashiCorp Vault | P0 |
| SE-004 | API key hashing (argon2id) | Python passlib | P0 |
| SE-005 | DDoS protection | Cloudflare / AWS Shield | P0 |
| SE-006 | WAF rules | Cloudflare WAF | P0 |
| SE-007 | CORS configuration | Go gateway + FastAPI | P0 |
| SE-008 | Provider request signing (AWS SigV4) | Python boto3 | P0 |
| SE-009 | Dependency vulnerability scanning | Dependabot, Snyk, pip-audit | P1 |
| SE-010 | Penetration testing (quarterly) | External firm | P1 |
| SE-011 | Bug bounty program | HackerOne | P2 |
| SE-012 | Zero-trust networking between services | Wireguard / Tailscale | P1 |
| SE-013 | Agentic access control: verify identity on every MCP call | Python auth middleware | P1 |

---

## 22. Module 19 — Infrastructure & Deployment

### 22.1 Requirements

| ID | Requirement | Priority |
|---|---|---|
| IN-001 | Docker containers for all services | P0 |
| IN-002 | Kubernetes with Helm charts | P0 |
| IN-003 | Horizontal auto-scaling (HPA on RPS and CPU) | P0 |
| IN-004 | Multi-region deployment (minimum 3 regions) | P1 |
| IN-005 | Blue-green / canary deployments | P1 |
| IN-006 | Database migrations via Alembic (Python) | P0 |
| IN-007 | CI/CD: lint → test → build → deploy | P0 |
| IN-008 | Infrastructure-as-code (Terraform) | P0 |
| IN-009 | Self-hosted deployment option (Docker Compose + docs) | P2 |
| IN-010 | Air-gapped deployment support | P2 |

### 22.2 Container Image Sizes

| Service | Base Image | Target Size |
|---|---|---|
| Go gateway | `scratch` or `alpine` | < 30MB |
| Python backend | `python:3.12-slim` | < 500MB (with ML deps) |
| Python backend (minimal) | `python:3.12-slim` (no ML) | < 200MB |
| Next.js frontend | `node:20-alpine` | < 200MB |
| Celery workers | `python:3.12-slim` | < 500MB |

### 22.3 Infrastructure Components

| Component | Technology | Purpose |
|---|---|---|
| Primary database | PostgreSQL 16 + pgvector | Users, keys, usage, billing, vectors |
| Cache / rate limiter | Redis 7 / Valkey | Rate limits, exact cache, sessions, pub/sub |
| Message queue | NATS / Redis Streams | Async events: logging, metering, webhooks |
| Task queue | Celery + Redis broker | Video jobs, usage aggregation, scheduled tasks |
| Object storage | AWS S3 / GCS | Generated video/image/audio files |
| CDN | Cloudflare | Static assets, edge caching, DDoS |
| DNS | Cloudflare DNS / Route53 | Multi-region, health-based routing |
| Monitoring | Prometheus + Grafana | Metrics dashboards |
| Tracing | OpenTelemetry → Grafana Tempo | Distributed traces |
| Logging | Grafana Loki | Centralized logs |
| Alerting | PagerDuty / Opsgenie | Incident management |
| Secrets | HashiCorp Vault | Provider keys, encryption keys |
| Search | Meilisearch | Model catalog search |

---

## 23. Module 20 — Testing Strategy

### 23.1 Test Categories

| Category | Scope | Tools | Coverage |
|---|---|---|---|
| Go unit tests | Gateway functions | `go test`, `testify` | > 80% |
| Python unit tests | Service logic | `pytest`, `pytest-asyncio` | > 80% |
| Python integration | DB + Redis + services | `pytest` + `testcontainers-python` | > 70% |
| API contract tests | OpenAI compat | Custom test suite vs OpenAI spec | 100% of endpoints |
| Provider adapter tests | Each adapter | Mock responses via `respx` / `httpx` | 100% of adapters |
| Frontend tests | React components | `vitest`, `React Testing Library` | > 70% |
| E2E tests | Full user workflows | `Playwright` | Critical journeys |
| Load tests | Throughput, latency | `k6`, `locust` | 5,000 RPS sustained |
| Chaos tests | Failure scenarios | `Chaos Monkey`, `Litmus` | All failover paths |
| Security tests | Vulnerabilities | `OWASP ZAP`, `Snyk`, `pip-audit`, `Trivy` | Critical/High = 0 |

### 23.2 Provider Mock Server (Python)

```python
# tests/mock_providers/server.py
from fastapi import FastAPI

mock_app = FastAPI()

@mock_app.post("/v1/chat/completions")
async def mock_chat(request: dict):
    """Emulate OpenAI chat completions with configurable behavior."""
    # Configurable: latency, error rate, token counts
    # Supports: streaming SSE, tool calls, structured output
    # Simulates: rate limiting (429), server errors (500), timeouts
    ...
```

Used in CI/CD for all integration tests without calling real provider APIs.

---

## 24. Module 21 — Competitive Feature Matrix

| Feature | OpenRouter | Portkey | Bifrost | Kong AI | Cloudflare AI | Our Target |
|---|---|---|---|---|---|---|
| Unified OpenAI-compatible API | Yes | Yes | Yes | Yes | Yes | Yes (P0) |
| Provider count | 60+ | 200+ | 20+ | 10+ | 20+ | 20+ launch, 60+ Y1 |
| Text generation | Yes | Yes | Yes | Yes | Yes | Yes (P0) |
| Image generation | Yes | Yes | No | No | No | Yes (P0) |
| Video generation | Yes | No | No | No | No | Yes (P1) |
| Audio I/O | Yes | Yes | No | No | No | Yes (P1) |
| Embeddings + reranking | Yes | Yes | Yes | Yes | Yes | Yes (P0) |
| Streaming (SSE) | Yes | Yes | Yes | Yes | Yes | Yes (P0) |
| Automatic failover | Yes | Yes | Yes | Yes | Yes | Yes (P0) |
| Semantic caching | No | Yes | Yes | Yes | Yes | Yes (P1) |
| Semantic routing | Limited | Yes | No | Yes | No | Yes (P2) |
| Structured outputs | Yes | Yes | Yes | No | No | Yes (P0) |
| Prompt management | No | Yes | Yes | No | No | Yes (P2) |
| Guardrails (PII, injection) | No | Yes | Yes | Yes | No | Yes (P1) |
| MCP gateway | No | Yes | Yes | No | No | Yes (P1) |
| Agentic session tracking | No | Yes | Yes | No | No | Yes (P1) |
| RBAC / multi-tenant | Limited | Yes | Yes | Yes | No | Yes (P0) |
| SOC 2 / HIPAA | No | Yes | Yes | Yes | No | Yes (P1) |
| Self-hosted option | No | Partial | Yes | Yes | No | Yes (P2) |
| Model marketplace | Yes | No | No | No | No | Yes (P1) |
| Video playground | Yes | No | No | No | No | Yes (P1) |
| BYOK | Yes | Yes | Yes | Yes | No | Yes (P1) |
| Hierarchical budgets | No | Yes | Yes | No | Yes | Yes (P1) |
| Auto model selection | Yes | Yes | No | No | No | Yes (P1) |
| Canary/A/B routing | No | Yes | No | No | No | Yes (P2) |
| Reasoning token tracking | Yes | Yes | Yes | No | No | Yes (P0) |

---

## 25. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-001 | Availability | 99.95% uptime (< 4.38 hrs downtime/year) |
| NFR-002 | Gateway latency overhead | < 15µs P99 at 5,000 RPS |
| NFR-003 | Time to first token (streaming) | < 200ms gateway contribution |
| NFR-004 | Backend API response (excl. provider) | < 50ms P95 |
| NFR-005 | Throughput | 10,000+ RPS sustained |
| NFR-006 | Data durability | 99.999% (PostgreSQL replication) |
| NFR-007 | Recovery time objective (RTO) | < 5 minutes |
| NFR-008 | Recovery point objective (RPO) | < 1 minute |
| NFR-009 | Scalability | Horizontal — add instances, no re-architecture |
| NFR-010 | Cold start | Go: < 200ms, Python: < 5s |
| NFR-011 | API backward compat | No breaking changes without 6-month deprecation |

---

## 26. Development Phases & Milestones

### Phase 1 — Foundation (Months 1-3)

**Team: 2 Go + 2 Python + 1 TypeScript + 1 DevOps**

- Go gateway core with OpenAI-compatible endpoint
- 5 provider adapters in Python (OpenAI, Anthropic, Google, Mistral, Groq)
- Text generation with streaming (SSE)
- FastAPI backend: user registration, API key management
- PostgreSQL + Redis setup
- Rate limiting (Go + Redis)
- Basic failover (retry on 5xx)
- Exact-match caching (Redis)
- Token counting and usage tracking
- Basic docs site (Next.js + MDX)
- Docker + CI/CD pipeline (GitHub Actions)
- Provider mock server for testing
- **Milestone: Internal alpha — text-only, 5 providers**

### Phase 2 — Billing & Dashboard (Months 3-5)

**Team: 2 Go + 3 Python + 2 TypeScript + 1 DevOps**

- Stripe billing integration
- Credit system with purchase flow
- Hierarchical budget controls
- OAuth2 login (Google, GitHub)
- RBAC per org/team/project
- Audit logging
- User dashboard: usage charts, billing, API key management
- Model marketplace with search and filtering
- API playground (text models)
- 15+ provider adapters
- Prometheus + Grafana monitoring
- OpenTelemetry tracing
- **Milestone: Public beta — billing, teams, 15 providers**

### Phase 3 — Multimodal & Intelligence (Months 5-8)

**Team: 2 Go + 4 Python + 2 TypeScript + 1 DevOps + 1 ML**

- Image generation API
- Video generation API (Celery async jobs, S3 storage)
- Audio I/O support
- Embeddings and reranking APIs
- Semantic caching (sentence-transformers + pgvector)
- Smart routing (cost, latency, quality optimization via Auto Exacto)
- Auto model selection (`openrouter/auto`)
- Guardrails engine (PII detection, prompt injection, content safety)
- Video playground and image playground
- Model comparison tool
- 30+ provider adapters
- **Milestone: GA launch — full multimodal, 30 providers, guardrails**

### Phase 4 — Agentic & Enterprise (Months 8-12)

**Team: 3 Go + 4 Python + 3 TypeScript + 2 DevOps + 1 ML + 1 Security**

- MCP gateway (server + client, Python)
- Agentic session tracking and tracing
- Prompt management and versioning
- Semantic routing (ML classifier)
- Canary/A/B routing
- Self-hosted deployment (Docker Compose + Helm chart + docs)
- SOC 2 Type II preparation
- GDPR/HIPAA compliance tooling
- On-behalf-of execution for MCP
- App attribution and leaderboards
- CLI tool (TypeScript/Node.js)
- 60+ provider adapters
- **Milestone: Enterprise GA — MCP, compliance, self-hosted, 60 providers**

---

## 27. Technology Stack Summary

| Layer | Technology | Why |
|---|---|---|
| **Gateway core** | Go 1.24+ (Gin or custom) | 11µs overhead, goroutines, single binary. Industry standard for AI gateways. |
| **Backend API** | Python 3.12+ / FastAPI | Native provider SDKs, richest AI/ML ecosystem, async, auto-OpenAPI. |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, flexible, async PostgreSQL support. |
| **Migrations** | Alembic | Auto-generated schema migrations. |
| **Task queue** | Celery + Redis | Async video jobs, webhooks, aggregation. |
| **Frontend** | Next.js 15 / React 19 / TypeScript | SSR dashboard, streaming playground, docs site. |
| **Styling** | Tailwind CSS 4 + shadcn/ui | Consistent, modern design system. |
| **Primary DB** | PostgreSQL 16 + pgvector | Relational data + vector embeddings in one DB. |
| **Cache** | Redis 7 / Valkey | Rate limiting, exact cache, pub/sub, sessions. |
| **Message queue** | NATS / Redis Streams | Async events between Go and Python. |
| **Object storage** | AWS S3 / GCS | Generated media files. |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards. |
| **Tracing** | OpenTelemetry → Grafana Tempo | Distributed traces across Go + Python. |
| **Logging** | Go: slog, Python: structlog → Loki | Structured, centralized logging. |
| **Secrets** | HashiCorp Vault | Provider API keys, encryption keys. |
| **Containers** | Docker + Kubernetes + Helm | Deployment and scaling. |
| **CI/CD** | GitHub Actions + ArgoCD | Automated pipeline. |
| **IaC** | Terraform | Infrastructure provisioning. |
| **CDN/WAF** | Cloudflare | Edge security and caching. |
| **Billing** | Stripe (Python SDK) | Payment processing. |
| **Auth** | authlib + python-jose (OAuth2/OIDC) | SSO integration. |
| **Guardrails** | guardrails-ai + llm-guard + nemo-guardrails | AI safety pipeline. |
| **Tokenizer** | tiktoken (Python) | Accurate token counting. |
| **Embeddings** | sentence-transformers (Python) | Semantic cache and routing. |
| **Search** | Meilisearch | Model catalog search. |
| **Testing** | Go: testify, Python: pytest, TS: vitest + Playwright | Full test coverage. |

---

## 28. Glossary

| Term | Definition |
|---|---|
| **AI Gateway** | Reverse proxy that routes AI/LLM API requests to multiple providers through a single endpoint |
| **BYOK** | Bring Your Own Key — users supply their own provider API keys |
| **Circuit Breaker** | Pattern that stops routing to a failing provider after repeated failures |
| **Exact-Match Cache** | Cache returning stored responses for identical requests (hash match) |
| **Failover** | Automatically routing to backup provider when primary fails |
| **FastAPI** | High-performance Python web framework with automatic OpenAPI docs |
| **GIL** | Global Interpreter Lock — Python threading limitation; mitigated via multiprocessing |
| **Guardrails** | Safety filters that validate/block AI inputs and outputs |
| **Hot Path** | Latency-critical request processing (Go gateway — microseconds) |
| **MCP** | Model Context Protocol — standard for connecting AI models to external tools |
| **NATS** | Lightweight message queue for async events between services |
| **OBO** | On-Behalf-Of — executing with requesting user's permissions |
| **P99** | 99th percentile latency — 99% of requests faster than this value |
| **pgvector** | PostgreSQL extension for vector similarity search |
| **PII** | Personally Identifiable Information |
| **RBAC** | Role-Based Access Control |
| **RPS** | Requests Per Second |
| **Schema Normalization** | Translating provider-specific formats into one unified format |
| **Semantic Cache** | Cache matching by meaning (embedding similarity) not exact text |
| **SSE** | Server-Sent Events — protocol for streaming LLM responses |
| **Structured Output** | Forcing LLM responses to conform to a JSON schema |
| **Warm Path** | Business logic not requiring sub-millisecond latency (Python backend) |

---

*Document maintained by: Engineering Team*
*Architecture: Go (Gateway) + Python (Backend & ML) + TypeScript (Frontend & DX)*
*Next review: Monthly at architecture review meeting*
