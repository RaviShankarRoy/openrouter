# frontend-web — Dashboard + Playground + Marketplace

Next.js 15 App Router + React 19 + Tailwind 4 + shadcn/ui + Vercel AI SDK. Feature-Sliced Design. RSC by default.

## Commands

```bash
pnpm install
pnpm dev                  # next dev on :3000
pnpm build                # production build (runs OTel instrumentation)
pnpm test                 # vitest unit tests
pnpm test -- --watch      # watch mode
pnpm lint                 # eslint
pnpm typecheck            # tsc --noEmit
pnpm e2e                  # playwright e2e — requires docker-compose up + backend running
```

## Layout (Feature-Sliced)

```
src/
├── app/                          # App Router (each folder = route segment)
│   ├── (marketing)/              # landing
│   ├── dashboard/                # FE-005 usage overview
│   ├── playground/               # FE-003 streaming chat (Vercel AI SDK)
│   ├── models/                   # FE-006 marketplace
│   ├── docs/[...slug]/page.tsx   # MDX docs renderer
│   ├── admin/                    # FE-011 (protected)
│   ├── login/                    # FE-012 OAuth
│   ├── api/                      # BFF: proxy + nextauth routes
│   └── layout.tsx                # root layout, providers
├── features/                     # cross-cutting features
│   ├── billing/
│   ├── code-snippets/            # FE-007 request builder
│   └── playground/
├── entities/                     # domain models for UI
├── widgets/                      # composed UI blocks
├── shared/
│   ├── api/                      # OpenAPI-generated fetch client (src/shared/api/client.ts)
│   ├── config/env.ts             # zod-validated env, server vs client split
│   ├── ui/                       # shadcn/ui primitives
│   ├── providers/                # auth, theme, query client
│   └── hooks/
├── middleware.ts                 # auth gate for protected routes
└── instrumentation.ts            # OpenTelemetry init
```

## RSC Rules

- **Default to server components.** Add `'use client'` only when you need state, effects, browser APIs, or event handlers.
- **Server env vars** (no `NEXT_PUBLIC_` prefix) are validated in `src/shared/config/env.ts` and gated by `isServer`. Add `import "server-only"` to any module that touches `serverEnv` to prevent accidental client bundling.
- **`NEXT_PUBLIC_*` vars are bundled into the client** — never put secrets there.

## BFF Proxy

`src/app/api/proxy/[...path]/route.ts` forwards to the Go gateway. Current header filter is a **denylist of 4 headers** — consider switching to an allowlist (`accept`, `content-type`, `accept-encoding`, `user-agent`, `traceparent`, `tracestate`). The proxy currently forwards `x-forwarded-*`, `cookie`, etc. unchanged.

## NextAuth (v5)

OAuth flow in `src/app/api/auth/[...nextauth]/route.ts`. The JWT callback exchanges the Google access token with backend `/v1/oauth/exchange` to mint an internal JWT. **The provider's raw access token is currently persisted on the session** — exposes Google tokens to BFF logs. Prefer mint-then-discard.

## Security Headers

`next.config.ts` declares `securityHeaders` but **no CSP**. Add at minimum `default-src 'self'; frame-ancestors 'none';` and per-route nonces when client scripts settle.

## Streaming UI

`features/playground/` uses the Vercel AI SDK `useChat` hook. SSE comes from the Go gateway via the BFF proxy. Keep `experimental_useFormStatus` patterns in client components.

## Testing

- `vitest` for unit tests with `vitest.setup.ts`.
- `playwright.config.ts` for e2e — needs `docker-compose up` + `make dev-all`.
- Component tests live alongside (`Component.test.tsx`).

## Known Issues (from audit)

- `app/docs/[...slug]/page.tsx` mixes `dynamic = "force-static"` with `fs.readFile` at request time — contradictory. Sanitizer also lets empty segments through after `.`/`/` stripping (path-traversal-shaped).
- `middleware.ts` checks cookie presence, not signature. Real auth gate lives in RSC; document this on protected routes.
- `next.config.ts` lacks CSP, COOP, COEP headers.
- `apiClient` shared `AbortSignal.timeout(30s)` is global across retry attempts — first attempt eats the budget.

## Dependencies

`next@15`, `react@19`, `tailwindcss@4`, `next-auth@^5`, `@vercel/ai`, `@tanstack/react-query`, `recharts`, `monaco-editor`. pnpm-managed (`pnpm-lock.yaml`).
