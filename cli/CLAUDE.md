# cli — @openrouter/cli Developer Tool

Node 20 + TypeScript + commander.js. Bundled with tsup. Phase 4 in [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) — command skeletons exist, most behavior is stubbed.

## Commands

```bash
pnpm install
pnpm build                 # tsup → dist/
pnpm dev                   # tsup --watch
pnpm test                  # vitest (4 test files; not currently exercised in CI)
pnpm lint                  # eslint
pnpm typecheck             # tsc --noEmit
node dist/cli.js --help    # run built binary
```

Not wired into the root `Makefile` (no `make test-cli` target). Run from this directory.

## Layout

```
src/
├── cli.ts                # entry point — parses argv, dispatches to command
├── commands/
│   ├── login.ts          # CLI-001 OAuth2 browser flow
│   ├── chat.ts           # CLI-003 interactive REPL
│   ├── models.ts         # CLI-002 list models + pricing
│   ├── usage.ts          # CLI-004 usage stats
│   └── keys.ts           # CLI-005 API key management
└── lib/
    ├── api-client.ts     # fetch wrapper + SSE parser
    ├── auth.ts           # EncryptedFileStore (scrypt-derived AES-GCM)
    ├── config.ts         # ~/.openrouter/config.json
    ├── logger.ts         # pino
    └── output.ts         # formatting helpers
tests/
├── unit/                 # vitest unit tests
└── e2e/                  # not wired
```

## Credential Storage

`src/lib/auth.ts:EncryptedFileStore` encrypts tokens at rest with AES-GCM, key derived via scrypt (defaults: N=16384, r=8, p=1). Salt is per-record. This is obfuscation only — a same-UID attacker who reads the file derives the same key. Document this limitation in user-facing docs.

## CLI Patterns

- Use `commander` for argv parsing — see `cli.ts` for the root program.
- Each command is a function exported from `src/commands/<name>.ts`, registered in `cli.ts`.
- Use `logger` from `lib/logger.ts` for all output that isn't user-facing — keeps stdout clean.
- For interactive prompts, use `readline/promises` (avoid heavy deps like inquirer).
- **Sandbox file writes**: `chat /save <path>` accepts arbitrary paths. When extending, resolve to absolute and confirm before writing outside `$PWD`.

## Cross-Platform Gotchas

- `cli.ts` uses `import.meta.url` script-detection — verify on Windows. `file://${process.argv[1]}` produces wrong URL on Windows; use `pathToFileURL(process.argv[1]).href`.
- Token file path: `${os.homedir()}/.openrouter/credentials.enc` — works on Linux/Mac; on Windows confirm `os.homedir()` returns `C:\Users\<name>`.

## Testing

`vitest.config.ts` + 4 test files under `tests/`. Run with `pnpm test`. No coverage threshold yet.

## Dependencies

`commander`, `node-fetch` (or native fetch on Node 20+), `pino`, `tsup`, `typescript`, `vitest`. Bundled to a single executable via tsup; published as `@openrouter/cli` to npm (not yet released).

## Build Output

`tsup.config.ts` produces ESM + CJS bundles in `dist/`. Shebang `#!/usr/bin/env node` is added by tsup banner. `package.json` `bin` field maps `openrouter` to `dist/cli.js`.
