# frontend-web

Next.js 15 dashboard, marketing site, and developer playground for the OpenRouter-equivalent AI gateway. Implements DRD Module 3 (FE-001 through FE-015).

## Stack

- **Next.js 15** (App Router, React Server Components, Turbopack)
- **React 19** (server actions, `useActionState`)
- **TypeScript 5.7** (strict mode, no `any`)
- **Tailwind CSS 4** + shadcn/ui-style primitives (copied locally, no runtime dependency on shadcn CLI)
- **Vercel AI SDK** (`useChat`) for the streaming playground (FE-003)
- **next-auth v5** (Auth.js) for OAuth (Google, GitHub) (FE-012)
- **TanStack Query** for server state caching
- **pino** for structured JSON logs (matches ARCHITECTURE.md §2.2)
- **zod** for runtime env + form validation
- **Recharts** for usage graphs (FE-005)
- **Monaco Editor** for the request builder (FE-007)

## Layout — Feature-Sliced Design

```
src/
├── app/                    # Next.js App Router (pages, layouts, route handlers)
├── widgets/                # Compositions of features (Sidebar, Topbar, charts)
├── features/               # Self-contained user-facing feature units
├── entities/               # Domain models for the UI (User, Model, ApiKey, Usage)
└── shared/                 # Reusable utilities (api client, hooks, ui primitives)
```

The dependency rule is one-directional: `app → widgets → features → entities → shared`. Lower layers never import from higher ones.

## Design patterns

| Pattern | Where | Why |
|---|---|---|
| **React Server Components by default** | `src/app/**/page.tsx` | Less client JS, better SEO; mark `'use client'` only when interactivity is required |
| **Server Actions** | `src/app/dashboard/keys/actions.ts` | Mutations without a separate API route (FE-004) |
| **Compound Components** | `src/shared/ui/{tabs,dialog}.tsx` | Composable primitives via context |
| **Custom Hooks** | `src/shared/hooks/` | Encapsulate stateful logic |
| **Repository Pattern** | `src/shared/api/client.ts` + `src/entities/*/api.ts` | Hide transport from features |
| **Provider Pattern** | `src/shared/providers/` | Cross-cutting concerns: auth, theme, query client |
| **Container/Presenter** | e.g. `KeyList` (container) wraps a presentational table | Separates data fetching from rendering |

## Run

```bash
make install    # pnpm install
make dev        # next dev --turbopack on :3000
make build      # production build (standalone output)
make start      # node .next/standalone/server.js
make test       # vitest run
make test-e2e   # playwright
make lint       # eslint + tsc --noEmit
make codegen    # regenerate src/shared/api/generated/schema.ts from ../shared/openapi/openapi.yaml
make docker     # multi-stage docker build, < 200MB
```

## Environment

Copy `.env.example` to `.env.local`. The Backend-For-Frontend route at `/api/proxy/*` forwards to `NEXT_PUBLIC_BACKEND_URL` with the user's session token attached server-side, so secrets never reach the browser.

## Observability

- **Tracing:** `instrumentation.ts` boots `@vercel/otel`; OTLP endpoint via `OTEL_EXPORTER_OTLP_ENDPOINT`.
- **Logging:** `src/shared/lib/logger.ts` exports a pino instance; never log PII or raw API keys (ARCHITECTURE.md §2.2).
- **Metrics:** Web Vitals are reported via `app/_vitals.ts` (TODO Phase 2).

## DRD requirement coverage

| Req | Path |
|---|---|
| FE-001 responsive | `app/page.tsx` + `globals.css` |
| FE-002 dark mode | `features/theme/theme-toggle/` + `shared/providers/ThemeProvider.tsx` |
| FE-003 streaming chat | `features/playground/chat/` + `shared/hooks/use-streaming-chat.ts` |
| FE-004 API key UI | `app/dashboard/keys/` + `features/api-keys/` |
| FE-005 usage charts | `app/dashboard/usage/` + `widgets/usage-chart/` |
| FE-006 model comparison | `features/models/model-comparison/` |
| FE-007 code snippets | `features/playground/code-snippets/` |
| FE-010 billing UI | `app/dashboard/billing/` + `features/billing/` |
| FE-012 OAuth | `app/api/auth/[...nextauth]/route.ts` + `features/auth/` |
| FE-015 OpenAPI docs | `app/docs/` (MDX-rendered) |
