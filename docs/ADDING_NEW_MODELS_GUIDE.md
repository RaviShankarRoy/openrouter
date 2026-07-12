# Beginner's Guide — Adding a New AI Model to the Gateway

A friendly, end-to-end walkthrough of what happens when you plug a new AI model
into this project. We'll use the **Gemma 4** (Google) and **Qwen 3.6** (Alibaba)
integration as the worked example, but the same pattern applies to any model
you'll add later.

> **Prerequisite reading:** [BEGINNERS_GUIDE.md](BEGINNERS_GUIDE.md). It explains
> the four "buildings" (gateway-go, backend-python, frontend-web, cli) and the
> general request flow. This guide assumes you've read at least Parts 1 and 2.

---

## Part 1 — The big picture

### What we just did, in one sentence

> We taught the gateway about **8 new AI models** (4 Gemma 4 variants + 4 Qwen 3.x
> variants) so that any user can call them through the same `/v1/chat/completions`
> endpoint they already use for OpenAI or Anthropic.

### The "vending machine" analogy

Think of the gateway as a vending machine. Each row in the machine is a model
the user can pick. Adding Gemma 4 and Qwen is like:

1. **Stocking the row** — telling the machine "row B7 holds Gemma 4 31B".
2. **Wiring the coin slot** — telling it where to send your money so the right
   product drops out (which provider company, which API URL, which API key).
3. **Pricing the row** — telling it "this product costs $0.30 per million input
   tokens" so the bill is right.
4. **Updating the menu** — listing the new product on the LCD screen so customers
   know it exists.

Every model integration is those four steps. Once you've done one, you've done
them all.

### Why these models, specifically?

| Model | Released | License | Why we picked it |
|---|---|---|---|
| **Gemma 4** (E2B / E4B / 26B-MoE / 31B) | April 2026, Google | **Apache 2.0** | First major Google open-weight release with a fully permissive license. Multimodal (text + image + audio + video). Runs anywhere — even on a Raspberry Pi (E2B variant). |
| **Qwen 3.6** (27B / 35B-A3B) | April 2026, Alibaba | **Apache 2.0** | The 27B model beats much larger closed models on coding tasks. Cheap, fast, good at reasoning. |

> **What does "open-weight" mean?** The model file (the trained "brain") is
> publicly downloadable. You can run it on your own GPU, fine-tune it, ship it
> in a container. Compare to **closed-weight** models like GPT-4o or Claude
> where only the company hosting them has the file.

> **Why Apache 2.0 matters.** Apache 2.0 is the gold-standard permissive open
> source license. It says: use it for anything, including commercial products,
> with no royalties or "you owe us if you grow big" clauses. Some other model
> licenses (Llama 3, Cohere Command R) have restrictions; Apache 2.0 has none.

---

## Part 2 — The mental model: how "adding a model" works here

### The single most important fact

Most AI providers today speak the same dialect: **the OpenAI API format**.

This is true for OpenAI itself (obviously), but also for Together, Fireworks,
DeepInfra, Groq, Cerebras, Hyperbolic, vLLM, Ollama, LM Studio… they all accept
the same JSON shape for `/chat/completions`.

That means: **most "new providers" don't need new code. They just need new
config.** This is why the Gemma 4 + Qwen 3.6 integration is mostly editing YAML
files, not writing translator logic.

### When you DO need code

You only write a real "translator" (called an **adapter**) when the provider's
API shape is different. Today the project has three real translators:

| Provider | Adapter file | Why it needs translation |
|---|---|---|
| OpenAI | [adapters/openai.go](../gateway-go/internal/proxy/adapters/openai.go) | Canonical format — passthrough |
| Anthropic | [adapters/anthropic.go](../gateway-go/internal/proxy/adapters/anthropic.go) | Different field names (`messages` shape, system messages, tool roles) |
| Google (Gemini) | [adapters/google.go](../gateway-go/internal/proxy/adapters/google.go) | Completely different REST shape (`generateContent` instead of `chat/completions`) |

Both Gemma 4 and Qwen 3.6 are served by hosts that **emulate the OpenAI format**,
so they reuse the OpenAI adapter unchanged. Look at [proxy.go:43-51](../gateway-go/internal/proxy/proxy.go#L43-L51):

```go
adapters: map[string]adapters.ProviderAdapter{
    "openai":    openAIAdapter,
    "anthropic": adapters.NewAnthropic(),
    "google":    adapters.NewGoogle(),
    // OpenAI-compatible aggregators / self-host.
    "together":  openAIAdapter,    // ← Gemma + Qwen via Together
    "fireworks": openAIAdapter,    // ← Gemma + Qwen via Fireworks
    "ollama":    openAIAdapter,    // ← self-hosted on your own GPU
},
```

That single map is the wiring diagram for the whole gateway.

---

## Part 3 — The four questions every integration must answer

Whenever you add a model, the gateway needs to know:

| Question | Where the answer lives |
|---|---|
| **1. Where do I send the request?** | [providers.yaml](../gateway-go/configs/providers.yaml) — provider's `base_url` |
| **2. Whose key do I use?** | [providers.yaml](../gateway-go/configs/providers.yaml) — `key_env` field, plus the actual key in `.env` |
| **3. How much does it cost?** | [model_pricing](../backend-python/alembic/versions/20260501_0001_add_gemma_qwen_pricing.py) table (Postgres) |
| **4. What can it do?** | [routing.yaml](../backend-python/configs/routing.yaml) — `capabilities`, `modalities` |

Below is each one walked through in plain English.

### 3.1 — "Where do I send the request?"

The gateway has a YAML file called [providers.yaml](../gateway-go/configs/providers.yaml).
Think of it as the gateway's address book. Each entry is:

```yaml
together:
  base_url: https://api.together.xyz/v1
  key_env: TOGETHER_API_KEY
  timeout_seconds: 120
  circuit_breaker:
    max_failures: 5
    reset_timeout_seconds: 30
```

In plain English:

> "There's a provider I call `together`. Send their HTTP requests to
> `https://api.together.xyz/v1`. Look for the API key in the environment
> variable `TOGETHER_API_KEY`. Wait up to 120 seconds for a response. If
> 5 calls in a row fail, stop trying for 30 seconds (circuit breaker)."

After the providers section, there's a `models` section:

```yaml
- id: qwen/qwen3.6-27b
  provider: together
  fallback:
    - { provider: fireworks, model: accounts/fireworks/models/qwen3p6-27b }
```

In plain English:

> "When a user asks for `qwen/qwen3.6-27b`, send it to `together` first.
> If Together is down, try Fireworks instead — but ask Fireworks for it by
> their internal name, which is `accounts/fireworks/models/qwen3p6-27b`."

This `fallback` chain is one of the most valuable features. If Together has an
outage at 3 AM, your users don't even notice — the gateway transparently tries
Fireworks. (The same pattern is used by Netflix to keep videos playing during
AWS outages, just with movies instead of LLMs.)

> **Hot reload:** This file can be edited and reloaded without restarting the
> gateway — just send the process a `SIGHUP` signal. See
> [server.go:188-200](../gateway-go/internal/server/server.go#L188-L200) for
> the implementation. Means: you can add a model in production with zero
> downtime.

### 3.2 — "Whose key do I use?"

Three places need the key:

| File | Why |
|---|---|
| [.env](../.env) (local dev) | Loaded by both Go and Python at startup |
| [.env.example](../.env.example) | A template for new developers — fill in real keys after `cp .env.example .env` |
| Vault → Kubernetes Secret (production) | The [openrouter-providers ExternalSecret](../infrastructure/kubernetes/base/secrets.yaml) bulk-pulls all keys from one Vault path; just add the new keys to Vault |

For Gemma 4 + Qwen 3.6 we added three new env vars:

```bash
TOGETHER_API_KEY=replace-me      # for Qwen 3.x and some Gemma 4
FIREWORKS_API_KEY=replace-me     # for Gemma 4 and 122B Qwen
OLLAMA_API_KEY=ollama            # self-host (key is ignored by Ollama)
```

> **Why three?** Because *we* don't host Gemma 4 — Google releases the weights
> for free, but you still need a *machine* to run the model on. Together,
> Fireworks, and (for self-hosting) Ollama are companies/tools that host
> open-weight models. Each has its own account and its own key.

### 3.3 — "How much does it cost?"

Pricing lives in a Postgres table called `model_pricing`. We added 8 rows
via an **Alembic migration**:

> **Alembic** is a tool for evolving database schemas safely. Each change is a
> Python file with `upgrade()` (apply it) and `downgrade()` (undo it). They run
> in order, so the database evolves predictably across dev, staging, and prod.

The new migration is at
[backend-python/alembic/versions/20260501_0001_add_gemma_qwen_pricing.py](../backend-python/alembic/versions/20260501_0001_add_gemma_qwen_pricing.py).
It's just an `INSERT` statement for each model:

```python
("google/gemma-4-31b", "gemma", "0.30", "0.50", 256000,
 '["text","image","audio","video","tools"]'),
```

In plain English:

> "Model `google/gemma-4-31b`, served by provider `gemma`, costs $0.30 per
> million input tokens and $0.50 per million output tokens. It has a 256,000
> token context window. It can handle text, images, audio, video, and tool calls."

When a user runs a request, the backend looks up this row, multiplies the
prices by the token counts the provider reported, and debits the user's credit
balance. See [pricing_repository.py](../backend-python/app/infrastructure/billing/pricing_repository.py).

### 3.4 — "What can it do?"

The semantic routing config at
[backend-python/configs/routing.yaml](../backend-python/configs/routing.yaml)
declares each model's capabilities — used when a user asks for `openrouter/auto`
("just pick a good one for me"). More on this in Part 5.

---

## Part 4 — A walking tour of every file we touched

Here's the full picture. Each row links to the file and explains in one
sentence what changed and why.

### Gateway (Go)

| File | What changed | Why |
|---|---|---|
| [providers.yaml](../gateway-go/configs/providers.yaml) | Added 3 providers (`together`, `fireworks`, `ollama`) and 8 model entries | Tells the gateway where to send requests for the new models |
| [proxy.go](../gateway-go/internal/proxy/proxy.go) | Added 3 lines mapping new provider names to the existing OpenAI adapter | All three providers speak OpenAI format — no new translator needed |

### Backend (Python)

| File | What changed | Why |
|---|---|---|
| [openai_adapter.py](../backend-python/app/infrastructure/providers/openai_adapter.py) | Pulled `_provider_name`, `_base_url`, `_api_key_setting` out as class attributes | So Gemma/Qwen can subclass it and only override those three things |
| **NEW** [gemma_adapter.py](../backend-python/app/infrastructure/providers/gemma_adapter.py) | Subclass for Gemma 4 (~30 lines, mostly pricing) | Lets the Python control plane track Gemma usage and bill for it |
| **NEW** [qwen_adapter.py](../backend-python/app/infrastructure/providers/qwen_adapter.py) | Subclass for Qwen 3.x (~30 lines, mostly pricing) | Same as above for Qwen |
| [bootstrap.py](../backend-python/app/infrastructure/providers/bootstrap.py) | Registered both adapters at startup | Makes them visible to the rest of the system |
| [config.py](../backend-python/app/core/config.py) | Added 3 new env-var settings | So Python knows how to read `TOGETHER_API_KEY` etc. |
| **NEW** [alembic migration](../backend-python/alembic/versions/20260501_0001_add_gemma_qwen_pricing.py) | Inserts 8 pricing rows | Surfaces models in `/api/v1/models`, billing, frontend marketplace |

### Semantic routing (Python)

| File | What changed | Why |
|---|---|---|
| **NEW** [routing.yaml](../backend-python/configs/routing.yaml) | Declares the 11-model "auto" candidate pool with capability tags | Decoupled from code — operators can add models without redeploying |
| **NEW** [routing/config.py](../backend-python/app/application/routing/config.py) | YAML loader and `RoutingConfig.filter()` method | Picks candidates that satisfy `RequestHints` (vision, EU residency, etc.) |
| [routing_servicer.py](../backend-python/app/infrastructure/grpc/routing_servicer.py) | Now calls config + strategy registry instead of returning a hardcoded answer | The actual brain of `openrouter/auto` |

### Self-hosting (Docker)

| File | What changed | Why |
|---|---|---|
| [docker-compose.yml](../docker-compose.yml) | Added `ollama` service (GPU block commented out) | Lets you run Gemma 4 / Qwen 3 on your own machine for free |

### Production (Kubernetes / Helm)

| File | What changed | Why |
|---|---|---|
| [values.yaml](../infrastructure/helm/openrouter/values.yaml) | Added together/fireworks/ollama to `gateway.providers.list` | So the production deployment also knows about them |

### Tests

| File | What changed | Why |
|---|---|---|
| **NEW** [test_routing_config.py](../backend-python/tests/unit/test_routing_config.py) | 7 tests covering filter logic | Catches typos in `routing.yaml` before they break production |
| **NEW** [test_provider_adapters.py](../backend-python/tests/unit/test_provider_adapters.py) | 12 tests covering adapter pricing | Catches typos in pricing dicts before they cost the company money |

---

## Part 5 — Semantic routing, explained from scratch

This is the most "magical" piece, so it gets its own section.

### The problem it solves

Most users don't actually care which model they get. They want **a good answer
for the cheapest possible price**. Asking them to memorize 60 model IDs is
unfriendly.

So the gateway accepts a special model name: `openrouter/auto`. When the user
sends:

```json
{ "model": "openrouter/auto", "messages": [...] }
```

…the gateway has to decide *for them* which model is best right now. That
decision is "semantic routing".

### How it used to work

Before this implementation, the routing servicer
[routing_servicer.py](../backend-python/app/infrastructure/grpc/routing_servicer.py)
just returned a hardcoded answer: "always use Claude Sonnet 4, fallback to
GPT-4o-mini." That worked, but it ignored the new models entirely.

### How it works now

The decision is split into three steps:

```
1. Load routing.yaml      ← what models exist + what they can do
2. Filter by hints        ← drop ones the user's request needs but they don't have
3. Run strategy           ← pick the best survivor (cheapest / fastest / highest quality)
```

#### Step 1 — The candidate pool

[routing.yaml](../backend-python/configs/routing.yaml) is just a list of every
model that's eligible for `openrouter/auto`. Each entry looks like:

```yaml
- model: google/gemma-4-31b
  provider: fireworks
  pricing_per_million: 0.30      # $0.30 per million tokens
  quality_score: 0.86            # 0..1, from evals
  latency_p50_ms: 720            # typical response time
  capabilities: [text, vision, audio, video, tools, streaming]
  geos_allowed: ["*"]
  residency: [us, eu, global]
```

This file is the **source of truth** for what auto-routing knows about. To add
a new candidate, just append a new entry — no code change.

#### Step 2 — Filter by request hints

The user's request comes with **hints**: "I need tools," "I need vision,"
"my data must stay in the EU," etc. The filter drops any model that can't
satisfy them.

| Hint | What it does |
|---|---|
| `needs_tools=True` | Drops models without "tools" in their `capabilities` |
| `needs_vision=True` | Drops models without "vision" |
| `needs_streaming=True` | Drops models without "streaming" |
| `user_geo="DE"` | Drops models whose `geos_allowed` doesn't include `*` or `DE` |
| `data_residency=("eu",)` | Drops models whose `residency` doesn't include `eu` |

There's also a **quality floor** (`strategy_floors.quality: 0.70`) and a
**latency ceiling** (`strategy_floors.latency_max_ms: 5000`). Models that
fall below the floor or above the ceiling are dropped automatically.

> **Why the floor?** It's a safety net for the cost strategy. Otherwise the
> cheapest model would always win — even if it's a tiny model that gives bad
> answers. The floor says "we won't recommend anything below quality 0.70 even
> if it's free."

#### Step 3 — Pick the survivor

The remaining candidates are handed to a **strategy**. The project has three:

| Strategy | What it does | Code |
|---|---|---|
| `cost` | Cheapest first | [strategies.py:37-42](../backend-python/app/application/routing/strategies.py#L37) |
| `latency` | Fastest first | [strategies.py:45-50](../backend-python/app/application/routing/strategies.py#L45) |
| `quality` | Highest-quality first | [strategies.py:53-58](../backend-python/app/application/routing/strategies.py#L53) |

The default is `cost`. When we tested it, the `cost` strategy picked
`gpt-4o-mini` ($0.15/M) as primary, with Gemma 4 26B-MoE and Qwen 3.6-27B as
fallbacks. That's a sensible result — cheap headline, but with capable open
backups if OpenAI is having a bad day.

### The picture

```
┌──────────────────────────────────────────────────────────────┐
│  USER REQUEST                                                │
│  { "model": "openrouter/auto", "messages": [...],           │
│    "hints": { "needs_vision": true, "data_residency": ["eu"]} │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  Load routing.yaml (cached, hot-reload) │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────────┐
        │  Filter by needs_vision, residency, floor    │
        │  Survivors: [gpt-4o, gemma-4-31b, gemma-4-26b]│
        └──────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │  Strategy (default: cost)    │
              │  → gemma-4-26b-moe ($0.20)   │
              │    fallback: gemma-4-31b     │
              └─────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Send to Fireworks │
                   └─────────────────┘
```

---

## Part 6 — Trying it yourself

### Prerequisites

```bash
# Get the local stack running
make up                # spins up postgres, redis, nats, minio, jaeger, ollama

# Run database migrations (creates the model_pricing rows)
cd backend-python
alembic upgrade head

# Make sure you have a real API key from a provider
# Sign up at https://api.together.xyz or https://fireworks.ai
echo "TOGETHER_API_KEY=tok-..." >> ../.env

# Start the gateway and the backend
make dev-backend    # in one terminal
make dev-gateway    # in another
```

### Make a real call

Get your dev API key (the one from `python seed_dev.py`) and try:

```bash
curl -N http://localhost:8080/api/v1/chat/completions \
  -H "Authorization: Bearer $DEV_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen/qwen3.6-27b",
    "stream": true,
    "messages": [{"role": "user", "content": "Write a haiku about Linux"}]
  }'
```

You should see tokens stream back word-by-word.

### Check the dashboards

| URL | What you'll see |
|---|---|
| `http://localhost:9091/metrics` | Prometheus metrics — find `provider="together"` counter |
| `http://localhost:16686` | Jaeger trace UI — find your request, see how long each step took |
| `http://localhost:3000/models` | Frontend marketplace — Gemma 4 + Qwen 3.6 should appear |
| `http://localhost:3000/playground` | Interactive chat — try the new models in the dropdown |

### Self-host with Ollama (no API key needed)

```bash
# Pull a small model
docker exec or-ollama ollama pull gemma4:e4b

# Now the gateway can serve google/gemma-4-e4b for free, locally
curl -N http://localhost:8080/api/v1/chat/completions \
  -H "Authorization: Bearer $DEV_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "google/gemma-4-e4b", "messages": [{"role": "user", "content": "hi"}]}'
```

> Self-hosting needs a beefy GPU for the larger models. The "E2B" and "E4B"
> Gemma 4 variants are designed to run on CPU or a small GPU.

### Run the tests

```bash
cd backend-python
uv run pytest tests/unit/test_provider_adapters.py tests/unit/test_routing_config.py -v
```

You should see 19 tests pass.

---

## Part 7 — Frequently asked questions

#### "Why didn't we write a Gemma adapter from scratch like Anthropic?"

Because Gemma 4 is hosted by Together and Fireworks, both of which **emulate
the OpenAI API**. They translate to/from the model's native format on their
end. We get to skip writing translator logic.

If we ever wanted to call Gemma 4 directly through Google's Gemini API
(`generateContent`), we'd write a real adapter — that endpoint has a different
shape.

#### "What if Together is down?"

Each model entry in `providers.yaml` has a `fallback` list. The gateway tries
the primary, then walks down the list. The **circuit breaker**
([circuitbreaker/registry.go](../gateway-go/internal/circuitbreaker/registry.go))
also "trips" — after 5 failures in a row, it stops calling Together for 30
seconds, so subsequent requests don't waste time on a known-bad provider.

#### "Where are my API key billing limits enforced?"

In two places. The **rate limiter**
([ratelimit/limiter.go](../gateway-go/internal/ratelimit/limiter.go)) caps
requests-per-minute. The **credit balance**
([entities.py](../backend-python/app/domain/entities.py)) caps spend. Each
request reserves an estimated cost up front; after the response, the actual
cost is settled. If your balance is too low, the request is rejected before
ever touching a provider.

#### "Why is pricing in two places — Python adapter `_PRICING` dict AND the database?"

Historical: the in-process dict came first (Phase 1 bootstrap), the database
table came later (Phase 2). The database is the **production** source of
truth — it's editable without a redeploy and gets cached in Redis for
performance. The in-process dict is what `/api/v1/models` reads in dev. We're
keeping both consistent for now; eventually `/api/v1/models` should switch to
reading from the database too.

#### "Can I add a model that needs a custom request shape, like a Bedrock model?"

Yes. You'd:

1. Write a new adapter in [gateway-go/internal/proxy/adapters/](../gateway-go/internal/proxy/adapters/)
   that implements the `ProviderAdapter` interface
   ([adapter.go](../gateway-go/internal/proxy/adapters/adapter.go)).
2. Register it in [proxy.go:43](../gateway-go/internal/proxy/proxy.go#L43)'s
   adapter map.
3. Do everything else the same way (providers.yaml, pricing migration, etc.).

The adapter is responsible for translating the OpenAI-format request into the
provider's native shape, and the response back. Look at
[adapters/anthropic.go](../gateway-go/internal/proxy/adapters/anthropic.go) for
a worked example.

#### "What's the difference between `google/gemini-1.5-pro` and `google/gemma-4-31b`?"

Both are Google models, but:

- **Gemini** is closed-weight. You can only call it via Google's hosted API.
- **Gemma** is open-weight, Apache 2.0. The model file is on Hugging Face. You
  can run it on your own GPU, on Together, on Fireworks, on Ollama, anywhere.

Different products with different business models. We integrated Gemini in
Phase 1 (Google adapter); Gemma 4 is the latest add and goes through Together
or Fireworks because we're not hosting it ourselves.

#### "Will my old code break?"

No. The change is **purely additive**. Existing model IDs (`gpt-4o`, `claude-...`,
`gemini-1.5-pro`) keep working exactly as before. We just made more model IDs
also work.

---

## Part 8 — Cheat sheet for adding the next model

You'll want to do this again. Here's the recipe:

```
□ 1. Identify the model and its host
     - Is the host OpenAI-compatible? (Almost always yes for open-weight models)
     - What's the base URL?
     - What's the env var name for its key?

□ 2. Add to providers.yaml (gateway-go/configs/)
     - Provider block (if the host is new)
     - Model entry with primary provider + fallback chain

□ 3. If the provider is brand new, add it to proxy.go's adapter map
     - For OpenAI-compatible: alias it to the existing openAIAdapter
     - For new shape: write a new adapter

□ 4. Add the API key env var to .env, .env.example, and Vault

□ 5. (Python control plane) Create a subclass adapter
     - Override _provider_name, _base_url, _api_key_setting
     - Add a _PRICING dict with input/output rates

□ 6. Register the new adapter in providers/bootstrap.py

□ 7. Create an Alembic migration adding model_pricing rows
     - cd backend-python && alembic revision -m "add foo pricing"
     - Edit the generated file

□ 8. (Optional) Add to routing.yaml so it's eligible for openrouter/auto

□ 9. (Optional) Add to Helm values.yaml under gateway.providers.list

□ 10. Add unit tests
      - Test pricing lookups for every model_id you added
      - Test that bootstrap registers it

□ 11. Verify
      - go build ./... (gateway compiles)
      - alembic upgrade head (DB rows land)
      - pytest tests/unit/ (all green)
      - curl the gateway with the new model_id (real request works)
      - GET /api/v1/models lists it
      - Frontend marketplace shows it
```

That's the entire skill. Once you're comfortable with this loop, every new
model is ~1 hour of work, mostly typing.

---

## Sister documents

- [BEGINNERS_GUIDE.md](BEGINNERS_GUIDE.md) — what the whole project is and how the four buildings fit together
- [ARCHITECTURE.md](../ARCHITECTURE.md) — the runtime topology (request flow, components, services)
- [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) — the requirement traceability matrix
- [local-dev.md](local-dev.md) — getting your local environment running
- [onboarding.md](onboarding.md) — first-week checklist for new engineers

---

*If you found anything in this guide unclear, that's a bug — please open a PR
to fix it. Documentation is code.*
