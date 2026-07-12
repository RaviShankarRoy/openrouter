# @openrouter/cli

Official command-line interface for the OpenRouter-equivalent AI gateway. Implements DRD §6.5 (CLI-001 through CLI-005).

## Install

```bash
# One-shot
npx @openrouter/cli login

# Global
npm install -g @openrouter/cli
openrouter --help
```

Requires Node.js 20 or newer. Cross-platform (Linux, macOS, Windows). On systems without a native keychain (some Linux containers, WSL without `gnome-keyring`) the credential store transparently falls back to an AES-256-GCM-encrypted file under the XDG config dir.

## Commands

| Command | DRD ID | Description |
|---|---|---|
| `openrouter login` | CLI-001 | OAuth 2.0 device-code flow with PKCE; opens browser, persists token to OS keychain. |
| `openrouter logout` | CLI-001 | Clear stored credentials. |
| `openrouter models list [--modality <text\|image\|video\|audio>]` | CLI-002 | List models with pricing. |
| `openrouter chat [--model <id>]` | CLI-003 | Interactive REPL with streaming output, model picker, slash commands. |
| `openrouter usage [--period <day\|week\|month>]` | CLI-004 | Usage stats for the current billing period as a table + sparkline. |
| `openrouter keys create \| list \| revoke` | CLI-005 | API key management. |

### Global flags

| Flag | Effect |
|---|---|
| `--json` | Machine-readable output. Disables spinners, colors and tables. |
| `--no-color` | Disable ANSI color (also honored: `NO_COLOR=1`). |
| `--base-url <url>` | Override the gateway base URL. Persisted via `openrouter config set base_url <url>`. |
| `--debug` | Verbose logs (pino-pretty when stderr is a TTY, JSON otherwise). |
| `-V, --version` | Print CLI + Node version. |
| `-h, --help` | Print help. |

### Slash commands inside `chat`

| Command | Effect |
|---|---|
| `/clear` | Reset the conversation. |
| `/save <path>` | Save the conversation as JSON. |
| `/exit` (also `/quit`) | Leave the REPL. |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | User error — auth, validation, missing config |
| 2 | Server error — gateway or upstream provider failure |

## Design notes

- **Command Pattern.** Every subcommand is a `commander.js` command registered in `src/cli.ts`. Each command file owns its arg parsing, side effects, and exit code semantics.
- **Strategy Pattern.** `lib/output.ts` exposes a `Renderer` interface with `TableRenderer` and `JsonRenderer` strategies, picked at parse time by the `--json` flag.
- **Repository Pattern.** `lib/api-client.ts` is the single component that knows the wire format (OpenAI-compatible endpoints, SSE stream framing). Commands consume only typed methods.
- **Adapter Pattern.** `lib/auth.ts` defines a `CredentialStore` interface with two implementations: `KeytarStore` (primary) and `EncryptedFileStore` (fallback). Selection is automatic at startup.
- **XDG-compliant config.** `lib/config.ts` resolves the config dir via `env-paths`, honoring `XDG_CONFIG_HOME` on Linux and platform conventions elsewhere. The token itself is **never** written there — only non-secret prefs.
- **No `any`.** Strict TypeScript throughout. Untyped third-party surfaces are wrapped at the lib boundary.

## Development

```bash
make install         # npm install
make dev ARGS="--help"
make test
make lint
make build           # bundle to dist/cli.js with shebang
make link            # local global install
make docker          # build < 100MB image
```

## Security

- Tokens live in the OS keychain by default. The fallback store uses a per-user master key derived via `scrypt` from `os.userInfo()` + a randomly generated salt persisted with `0600`.
- The CLI never logs tokens, prompts, or completion text at any log level.
- OAuth uses device-code flow with PKCE (RFC 7636). The `code_verifier` lives only in process memory.

## Telemetry

None. The CLI does not phone home. The only network destination is the configured gateway base URL.
