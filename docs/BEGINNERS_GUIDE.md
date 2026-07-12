# Beginner's Guide — What This Project Is and How We'll Build It

This document is for someone who is new to the codebase, new to backend systems, or new to building large software. It explains:

1. What this project actually does (in plain English).
2. Every concept and tool used, with an example.
3. The development plan, translated into language a beginner can follow.

If you know what an API is and have used a terminal, you should be able to read this front to back.

> Sister documents (more technical):
> - [README.md](../README.md) — quick start
> - [ARCHITECTURE.md](../ARCHITECTURE.md) — runtime topology
> - [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) — requirement traceability
> - [ADDING_NEW_MODELS_GUIDE.md](ADDING_NEW_MODELS_GUIDE.md) — beginner-friendly walkthrough of how a new model (Gemma 4, Qwen 3.6) is plugged in, plus a cheat sheet for the next one

---

## Part 1 — What is this project?

### The one-sentence pitch

> A single API that lets you talk to any AI model (OpenAI, Anthropic, Google, Mistral, ...) using one key, one bill, and one URL.

### The Stripe analogy

Stripe is one API for many payment processors (Visa, Mastercard, banks). You integrate Stripe once and you can accept any card.

This project does the same thing for AI models. You integrate **once**, and you can call **any** model.

```bash
# Without us — you write code per provider:
curl https://api.openai.com/v1/chat/completions   -H "Authorization: Bearer sk-openai-..."
curl https://api.anthropic.com/v1/messages        -H "x-api-key: sk-ant-..."
curl https://generativelanguage.googleapis.com/...

# With us — same shape, any provider:
curl https://our-gateway.example/v1/chat/completions \
  -H "Authorization: Bearer or-yourkey-..." \
  -d '{"model": "anthropic/claude-3-opus", "messages": [...]}'
```

### Why does this need to exist?

Real problems we solve:

| Problem | Without us | With us |
|---|---|---|
| **Many APIs, many keys, many bills** | You manage 5 vendor logins | One key, one invoice |
| **A provider goes down** | Your app breaks | We auto-fail-over to a backup |
| **Cost optimization** | You hand-pick the cheapest model | We route to cheapest that meets quality bar |
| **Caching** | Every request hits the provider | Identical requests are cached for free |
| **Rate limits** | Each provider has its own | We give you one consistent limit |
| **Safety / guardrails** | You build PII / jailbreak filters yourself | One pipeline, all providers |

---

## Part 2 — A tour of the system

### The four buildings

Think of the project as four buildings on the same street.

| Building | Folder | Job | Language |
|---|---|---|---|
| **The toll booth** | [gateway-go/](../gateway-go/) | Receive every request, decide where to send it, return the answer fast | Go |
| **The office** | [backend-python/](../backend-python/) | Slower work: billing, accounts, ML, sending emails | Python |
| **The shop window** | [frontend-web/](../frontend-web/) | Website / dashboard customers see | TypeScript (Next.js) |
| **The mailroom** | [cli/](../cli/) | Command-line tool for power users | TypeScript (Node.js) |

> **Why two backends?** Go is brutally fast (microseconds) and great for a high-volume hot path, but its libraries for things like Stripe billing and ML are weaker. Python is slower, but its ecosystem (FastAPI, SQLAlchemy, Stripe SDK, ML libs) is richer. So Go does the *fast bit* (proxying), Python does the *thoughtful bit* (everything else). This is called a **polyglot architecture**.

### Walking one request through the system

You ask: "Hey AI, what is 2 + 2?"

```
1. Your code            → POST /v1/chat/completions
2. Cloudflare           → blocks bots, then forwards
3. gateway-go           → checks your API key, your quota, your cache
                          picks a provider (e.g. OpenAI)
                          streams the answer back to you
4. backend-python       → in the background, records "you used 12 tokens, that
                          cost $0.0003, deduct from your balance"
5. You receive          → "2 + 2 = 4"
```

All of step 3 happens in under 200 microseconds of *our* code (the provider itself takes longer; we can't speed them up).

---

## Part 3 — Concepts glossary, with examples

Skim the headings; read the parts you don't already know.

### 3.1 Architectural concepts

#### Hot path vs. warm path

- **Hot path** = the code that runs on every single request. Must be ruthlessly fast. Lives in Go.
- **Warm path** = code that runs occasionally (signups, monthly invoices, generating embeddings). Can take milliseconds or seconds. Lives in Python.

> **Rule we follow:** if the operation must finish before the user sees a response, it's hot path. Otherwise, push it to the warm path.

#### Reverse proxy / gateway

A program that sits *in front of* other servers and forwards traffic to them. Beginners often think of a proxy as something on *their* computer (client proxy). A **reverse** proxy is on the *server* side.

```
client ──▶  [our gateway]  ──▶  OpenAI
                          ──▶  Anthropic
                          ──▶  Google
```

Our gateway is the front door. We can do anything we want before we forward — auth, caching, blocking, logging.

#### Microservices vs. monolith

- **Monolith** = one big program. Simpler, but if one feature breaks, everything breaks.
- **Microservices** = many small programs that talk to each other. Independently deployable.

We are *not* purely microservices. We are **polyglot services** — four services, each doing one thing, talking via well-defined contracts.

#### Polyglot

Different services written in different languages, picked for their strengths. Cost: you have to maintain four toolchains. Benefit: each service is in the best tool for *its* job.

#### Hexagonal architecture (Go gateway) / DDD (Python backend)

Both are ways to organize code so the **business logic** is in the middle, and the **technical details** (HTTP, databases, Redis) are at the edges. The key benefit: you can test the business logic without spinning up a database.

```
        ┌────────────────────────────────┐
        │   HTTP, Redis, Postgres        │  ← edges (replaceable)
        │   ┌─────────────────────────┐  │
        │   │   Business logic         │  │  ← middle (the valuable stuff)
        │   └─────────────────────────┘  │
        └────────────────────────────────┘
```

**DDD (Domain-Driven Design)** is a flavor of this. It says: model your code after how the *business* talks. If the business says "API key", the code has a class called `ApiKey`, not `KeyRecord` or `KeyEntity`.

---

### 3.2 The middleware chain (gateway-go)

A **middleware** is a small piece of code that runs before the actual handler. We chain them so each does one job.

```go
// Pseudocode of what every request goes through:
RequestID  → Logger  → Auth  → RateLimit  → Cache  → Router  → Proxy
```

| Middleware | What it does | Example |
|---|---|---|
| **RequestID** | Stamp each request with a UUID so we can trace it | `X-Request-Id: 7f3a-...` |
| **Logger** | Write a structured JSON line per request | `{"level":"info","method":"POST","ms":42}` |
| **Auth** | Look up your API key, decide who you are | Reject if invalid → 401 |
| **RateLimit** | Have you used too many requests this minute? | Reject if yes → 429 |
| **Cache** | Have we seen this *exact* request? Return saved answer | Skip provider entirely on hit |
| **Router** | Pick the best provider right now | "OpenAI is healthy, costs less" |
| **Proxy** | Actually call that provider, stream the answer back | `→ api.openai.com` |

This pattern is called the **Chain of Responsibility** design pattern.

---

### 3.3 Streaming (SSE)

When you ask ChatGPT a question, you see words appear one-at-a-time. That's **streaming** — the server sends partial answers as it generates them, instead of waiting for the whole thing.

We use **Server-Sent Events (SSE)**: a one-way streaming format over plain HTTP.

```
data: {"delta": "Hello"}
data: {"delta": " world"}
data: [DONE]
```

The gateway **never buffers** these — every chunk that arrives from the provider is forwarded to the user immediately. That's why our config sets `text/event-stream` and disables Go's default response buffering.

---

### 3.4 Caching (two layers)

**Caching** = remembering an answer so we don't have to recompute it.

| Layer | What we compare | Hit rate (typical) | Where |
|---|---|---|---|
| **L1 — exact cache** | Same model, same messages, same params? | 5–15% | Redis, in gateway-go |
| **L2 — semantic cache** | *Similar enough* messages? (uses embeddings + cosine similarity) | extra 10–25% | Postgres + pgvector, in backend-python |

#### Example

```
User A: "What is the capital of France?"   → MISS, call OpenAI, save.
User B: "What is the capital of France?"   → L1 HIT, free.
User C: "Capital of France?"               → L1 MISS but L2 HIT
                                              (semantic similarity = 0.94)
```

L2 is **opt-in** because semantic similarity can be wrong; users send `X-Semantic-Cache: true` to enable it.

---

### 3.5 Circuit breaker

Inspired by an electrical breaker. If a provider keeps failing, we **stop calling them** for 30 seconds, instead of hammering them and adding to their pain.

States:

```
CLOSED  → all good, traffic flows
   │   too many failures
   ▼
OPEN    → reject immediately, try fallback provider
   │   wait 30s
   ▼
HALF-OPEN → let one trial request through
   │
   ├─ success → CLOSED
   └─ failure → OPEN (wait again)
```

Library used: [`sony/gobreaker`](https://github.com/sony/gobreaker), wrapped per `(provider, model)` pair so one bad model doesn't break the others.

---

### 3.6 Rate limiting

Stops a single user from overwhelming us. We use a **sliding window** algorithm: count how many requests in the last 60 seconds.

```
Limit: 100 requests/min
Now:    [████████████████████░░░░░░░░░] 67/100  ✓ allow
Later:  [██████████████████████████████] 100/100 ✗ deny → 429
```

The check runs as one **atomic Lua script** on Redis so you can't sneak past it during the gap between "check" and "increment".

---

### 3.7 Auth: API keys hashed with argon2id

A user creates a key. It looks like `sk-or-abc123...`. We **never** store that string.

We store `argon2id(key)`, a one-way fingerprint. If our database leaks, the keys are still safe.

```
Plain key  : sk-or-abc123...
Stored hash: $argon2id$v=19$m=65536,t=3,p=4$...$xK9j2...
```

Argon2id is the modern best-practice password hash (memory-hard, GPU-resistant). Parameters: 64MB memory, 3 iterations, 4 parallel threads.

#### Why caching auth in Redis?

Argon2 is *deliberately* slow (~50ms). We can't do that on every API call. So:

```
First call:    Redis MISS → backend hash check (slow) → cache result in Redis
Next calls:    Redis HIT  (1ms)
```

---

### 3.8 gRPC (Go ↔ Python communication)

When the Go gateway needs to ask the Python backend "is this key valid?", it doesn't use REST. It uses **gRPC**.

| | REST/JSON | gRPC |
|---|---|---|
| Format | text JSON | binary protobuf |
| Speed | slower | faster |
| Schema | OpenAPI (optional) | `.proto` file (required) |
| Streaming | hard | first-class |

The schema (a `.proto` file) is committed in [shared/proto/](../shared/proto/). A code generator (`protoc`) reads it and creates Go and Python client/server stubs. Both sides are guaranteed to agree on the wire format.

#### Example .proto definition

```protobuf
service AuthService {
  rpc ValidateKey(ValidateKeyRequest) returns (ValidateKeyResponse);
}

message ValidateKeyRequest {
  string hashed_key = 1;
}
```

---

### 3.9 Event bus and queues

Two different patterns for async work, used for different reasons:

| Tool | Pattern | Use for | Loss tolerance |
|---|---|---|---|
| **NATS** | Pub/sub event bus | Usage events, metrics | Lossy is OK (we have backups) |
| **Celery** | Durable task queue | Video generation, billing aggregation, webhook delivery | Must not lose, must retry |

#### Example

```python
# NATS — fire and forget, ~10µs cost per publish
await nats.publish("gateway.usage", {"key_id": "...", "tokens": 42})

# Celery — durable, will retry on failure, takes seconds
generate_video.delay(prompt="a cat surfing", user_id="...")
```

---

### 3.10 Design patterns we actually use

These are well-known recipes for solving common problems. The book *Design Patterns* (1994) is the canonical reference.

| Pattern | Plain-English meaning | Where in this codebase |
|---|---|---|
| **Adapter** | Translates one shape into another | Each provider's request/response → our common shape |
| **Strategy** | Multiple algorithms, pick one at runtime | Routing: pick by cost OR latency OR quality |
| **Factory** | A function/class that builds objects | `NewOpenAIClient(config)` |
| **Repository** | Hides the database | `KeyRepository.find_by_hash(...)` instead of raw SQL |
| **Unit of Work** | "Do all of this or none of it" | `async with uow:` wraps a transaction |
| **Observer** | Listeners react to events | Health watcher publishes → router subscribes |
| **Decorator** | Wraps a function to add behavior | `@require_permission("admin")` |
| **Pipeline** | Each step transforms data, passes to next | Guardrails: PII filter → toxicity → jailbreak |
| **Object Pool** | Reuse expensive objects | Reusing `[]byte` buffers via `sync.Pool` to avoid garbage-collection pauses |

---

### 3.11 Observability — three pillars

If you can't see what your system is doing, you can't fix it.

| Pillar | What it answers | Tool we use | Where |
|---|---|---|---|
| **Logs** | "What happened at 2:43:01?" | Loki + Promtail | structured JSON, one event per line |
| **Metrics** | "What's the P99 latency this hour?" | Prometheus + Grafana | numeric counters over time |
| **Traces** | "*Why* was this one request slow?" | OpenTelemetry + Tempo | follow a request across services |

#### Example trace

```
trace_id = abc123
├─ gateway-go: handle_request          12ms
│  ├─ auth: redis_get                   1ms
│  ├─ ratelimit: redis_eval             1ms
│  └─ proxy: openai.com                 9ms
│     └─ openai: generate_completion    900ms (their problem)
```

Suddenly you can *see* who is slow.

---

### 3.12 Configuration

Settings (database URL, Redis URL, port number) are **never hard-coded**. They come from environment variables, validated at startup.

| Stack | Library | What it does |
|---|---|---|
| Go | `koanf` | Reads YAML + env, validates struct tags |
| Python | `pydantic-settings` | Reads env, validates types |
| TypeScript | `zod` | Reads env, validates schema |

If a required env var is missing, the service **refuses to start**. Better to crash on boot than serve garbage at 3 AM.

---

### 3.13 Infrastructure as Code (IaC)

We don't click buttons in AWS. We write code that creates the infrastructure.

| Tool | Layer | What it does |
|---|---|---|
| **Docker** | Per-service | Packages a service + its OS dependencies into a single image |
| **docker-compose** | Local dev only | Runs Postgres / Redis / NATS / MinIO on your laptop |
| **Kubernetes (k8s)** | Production runtime | Runs containers across many machines, restarts crashed ones, scales them |
| **Helm** | Package on top of k8s | "Install/upgrade my whole app with one command" |
| **Terraform** | Cloud account | Creates the VPC, EKS cluster, RDS, S3, IAM — everything below k8s |

#### Example: how a deploy flows

```
git push                         (you write code)
  → GitHub Actions builds image  (CI/CD)
  → image pushed to registry
  → Helm chart upgraded
  → k8s rolls pods one by one
  → Terraform untouched (infra didn't change)
```

---

### 3.14 CI/CD

- **CI (Continuous Integration)** — every push runs tests, linters, builds. If anything fails, the merge is blocked.
- **CD (Continuous Deployment)** — passing `main` automatically goes to staging; a manual approval promotes it to production.

We use **GitHub Actions**. Workflow files live in [.github/workflows/](../.github/workflows/).

---

### 3.15 SLO / SLA / SLI / NFR — reliability vocabulary

| Term | Meaning | Example for this project |
|---|---|---|
| **SLI** (Indicator) | A number you measure | "% of requests with latency < 200ms" |
| **SLO** (Objective) | A target for that number | "99.9% of requests finish < 200ms" |
| **SLA** (Agreement) | A contractual promise to customers, with penalties | "We refund if uptime < 99.9% in a month" |
| **NFR** (Non-Functional Requirement) | A quality the system must have | "Gateway P99 overhead < 15µs" |

Functional requirement = "the system must let users create API keys."
Non-functional requirement = "...and the page must load in <500ms."

---

### 3.16 Security & compliance words you'll hear

| Word | Plain English |
|---|---|
| **mTLS** | TLS where both sides prove who they are (not just the server) |
| **SPIFFE** | A naming standard for service identities (`spiffe://prod/sa/gateway-go`) |
| **WAF** | Web Application Firewall — Cloudflare blocks malicious patterns |
| **PII** | Personally Identifiable Information — names, emails, phone numbers |
| **SOC 2** | An audit standard. Type 1 = "you have controls"; Type 2 = "they worked for 6+ months" |
| **GDPR / CCPA** | Privacy laws (EU / California) that give users rights over their data |
| **HIPAA** | US healthcare privacy law; required to handle medical data |
| **DPIA** | Data Protection Impact Assessment — a doc EU regulators may ask for |
| **BAA** | Business Associate Agreement — a contract needed for HIPAA |

---

## Part 4 — The development plan, in plain English

We're going to build this in phases. Each phase has a goal a non-technical person can understand.

### Phase 0 — "Make the scaffold actually work" (Weeks 1–4)

**Problem:** the project today *looks* complete, but several pieces don't talk to each other yet.

**What we'll do, plain English:**
- Run the code generators that turn `.proto` and `.yaml` schema files into actual Go/Python/TypeScript code. Without this, the gateway can't ask the backend "is this key valid?" because the function doesn't exist yet.
- Finish translating Anthropic's streaming format to the OpenAI streaming format (so customers using one SDK can talk to either provider).
- Write proper tests for the Go gateway. Today there's only one.
- Create the deployment automation (GitHub Actions) so a `git push` actually builds and tests the code.
- Create the production cloud infrastructure (Terraform): VPC, Kubernetes cluster, database, Redis, etc.
- Wire up monitoring dashboards (Grafana) so we can see what's happening.

**Done when:** a developer pushes code, CI runs all tests, builds 4 Docker images, deploys to a dev cluster, sends a fake request, sees it on a Grafana dashboard. Today, *none* of this works.

### Phase 1 — Closed beta (Months 2–4)

**Goal:** invite ~50 friendly customers, let them actually use the product.

**What we'll add:**
- 10 important AI providers (we have 2 today: OpenAI and Anthropic).
- Stripe billing — so customers can top up their balance with a credit card.
- A working dashboard — so customers can create API keys, see usage charts, top up.
- Role-based permissions — so an organization admin can invite team members.

### Phase 2 — Public beta (Months 5–7)

**Goal:** open signups to anyone.

**What we'll add:**
- 20 more providers (30 total).
- Image generation, audio transcription, embeddings — not just chat.
- Semantic cache (the smart cache from §3.4 above).
- Per-team budgets and alerts.
- Multi-region deployment so we don't go down if one AWS region does.
- Start the SOC 2 audit — required to sell to bigger companies.

### Phase 3 — General availability (Months 8–10)

**Goal:** stop calling it "beta". Publish a public SLA.

**What we'll add:**
- All 60 providers.
- Safety guardrails — automatically detect and block PII, jailbreak attempts, toxic content.
- Video generation pipeline (long-running jobs via Celery).
- Performance: hit the <15µs P99 latency target.
- SOC 2 Type 1 report finished.

### Phase 4 — Enterprise & agentic (Months 11–12+)

**Goal:** sell to large companies and AI agent builders.

**What we'll add:**
- MCP (Model Context Protocol) gateway — for AI agents that need to call tools.
- Persistent agent sessions with budgets.
- Self-hosted version (some customers can't use the cloud).
- Enterprise sign-on (SAML, SCIM) — corporate IT requires this.

---

## Part 5 — Why this plan is useful

### Why phasing matters

Imagine telling a customer "we'll have everything in 12 months." They will not wait. Phasing means:

| Month | What customers see |
|---|---|
| 1 | (internal — scaffold works) |
| 4 | "I can sign up, get an API key, send a chat completion, pay with a credit card" |
| 7 | "I can do images and embeddings too, and my team can use it" |
| 10 | "It has 60 providers, safety, and an SLA — I trust it for production" |
| 12 | "It works for our enterprise compliance team" |

Each phase produces a usable product. We don't ship an unusable half-built thing.

### Why "exit gates" matter

Before each phase ends, we check explicit conditions: tests passing, uptime achieved, user count hit. If they're not met, we don't move on — we fix the current phase. This stops the classic trap of *"feature done, but it doesn't actually work yet."*

### Why we wrote it down

If this stays in someone's head, only that person can plan. If it's a document, anyone can read it, push back, suggest changes — and a new engineer onboarding in month 6 can read it and understand where we are.

---

## Part 6 — Quick reference

### What runs where?

| Layer | Tool | Why |
|---|---|---|
| Edge | Cloudflare | DDoS, WAF, TLS |
| Ingress | Nginx (k8s ingress) | Routes traffic into the cluster |
| Hot path | Go gateway | Speed |
| Warm path | Python (FastAPI) | Ecosystem |
| Async jobs | Celery workers | Durable retries |
| Events | NATS JetStream | Cheap pub/sub |
| Database | Postgres 16 + pgvector | Relational + vectors for semantic cache |
| Cache | Redis 7 (Valkey) | In-memory, microsecond reads |
| Object storage | S3 (MinIO in dev) | Files, video outputs |
| Frontend | Next.js 16 | SSR + React |

### What should a beginner learn first to contribute?

In this order:

1. **HTTP and JSON** — every part of the system speaks them.
2. **Git + GitHub PR workflow** — how we collaborate.
3. **Docker** — to run the project on your laptop.
4. **One language deeply** (pick Go *or* Python *or* TypeScript). Don't try to learn all three at once.
5. **The middleware chain idea** ([§3.2](#32-the-middleware-chain-gateway-go)) — once it clicks, half the codebase makes sense.
6. **Redis basics** — `GET`, `SET`, `EXPIRE`, sliding-window rate limiting.
7. **One database concept at a time** — start with Postgres + simple SQL; pgvector and migrations come later.
8. **Observability** — read one trace in Tempo, one dashboard in Grafana. Seeing your code's behavior is the unlock.

### Documents to read next

- [README.md](../README.md) — how to start it locally
- [docs/local-dev.md](local-dev.md) — set up your laptop
- [docs/onboarding.md](onboarding.md) — first-week onboarding checklist
- [ARCHITECTURE.md](../ARCHITECTURE.md) — the technical version of Part 2 of this guide
- [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) — the technical version of Part 4

### Glossary cheat sheet

| Term | One-line meaning |
|---|---|
| Hot path | Code on every request; must be fast |
| Reverse proxy | Server that forwards requests to other servers |
| Middleware | Small step that runs before the handler |
| SSE | Streaming over plain HTTP |
| Circuit breaker | Stop calling a dead provider |
| Rate limit | Cap on requests per time window |
| L1 cache | Exact-match cache |
| L2 cache | Semantic-similarity cache |
| Argon2id | Modern password / key hash |
| gRPC | Fast, schema-first RPC over HTTP/2 |
| NATS | Lightweight pub/sub event bus |
| Celery | Durable background-job queue |
| OTel | OpenTelemetry — vendor-neutral tracing standard |
| Prometheus | Metrics database |
| Grafana | Dashboards on top of metrics |
| Loki | Log database |
| Tempo | Trace database |
| k8s | Kubernetes — container orchestrator |
| Helm | "Package manager" for k8s apps |
| Terraform | Cloud infrastructure as code |
| CI/CD | Auto-test on PR, auto-deploy on merge |
| SLO | Reliability target you pick for yourself |
| SLA | Reliability promise you make to customers |
| SOC 2 | Audit standard required by enterprise buyers |

---

*If anything here is still confusing, that's a documentation bug. Open an issue or send a PR with a clearer wording.*
