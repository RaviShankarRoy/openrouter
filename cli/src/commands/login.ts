// CLI-001 — OAuth 2.0 device-code flow with PKCE (RFC 7636 + RFC 8628).
//
// Flow:
//   1. POST /oauth/device/code  -> { user_code, verification_uri, device_code, interval, expires_in }
//   2. Open the verification URI in the user's browser (best effort).
//   3. Poll /oauth/token until access_token returned, user denies, or device_code expires.
//   4. Persist access_token via lib/auth.ts (keychain or encrypted file fallback).
import type { Command } from 'commander';
import { createHash, randomBytes } from 'node:crypto';
import open from 'open';
import { ApiClient } from '../lib/api-client.js';
import { setToken, getCredentialStore } from '../lib/auth.js';
import { loadConfig } from '../lib/config.js';
import { pickRenderer } from '../lib/output.js';
import { AuthError, exitWithError } from '../lib/errors.js';
import type { GlobalOptions } from '../cli.js';

const DEFAULT_CLIENT_ID = 'openrouter-cli';

export interface LoginOptions extends GlobalOptions {
  noBrowser?: boolean;
  clientId?: string;
}

export function registerLogin(program: Command): void {
  program
    .command('login')
    .description('Authenticate via OAuth device-code flow (CLI-001)')
    .option('--no-browser', 'do not auto-open the browser')
    .option('--client-id <id>', 'OAuth client id', DEFAULT_CLIENT_ID)
    .action(async (opts: LoginOptions, cmd: Command) => {
      const globals = cmd.optsWithGlobals<LoginOptions>();
      try {
        await runLogin({ ...globals, ...opts });
      } catch (err) {
        exitWithError(err);
      }
    });
}

export async function runLogin(opts: LoginOptions): Promise<void> {
  const r = pickRenderer({ json: opts.json, color: opts.color });
  const cfg = await loadConfig();
  const api = new ApiClient({
    baseUrl: opts.baseUrl ?? cfg.baseUrl,
  });

  const verifier = generatePkceVerifier();
  const challenge = pkceChallenge(verifier);
  const clientId = opts.clientId ?? DEFAULT_CLIENT_ID;

  const init = await api.deviceCodeStart(clientId, challenge);
  const verificationUri = init.verification_uri_complete ?? init.verification_uri;

  if (opts.json === true) {
    r.json({ stage: 'awaiting_user', user_code: init.user_code, verification_uri: verificationUri });
  } else {
    r.text('');
    r.text(r.color.bold('To finish logging in, visit:'));
    r.text(`  ${r.color.primary(verificationUri)}`);
    r.text('');
    r.text(`Enter the code: ${r.color.bold(init.user_code)}`);
    r.text('');
  }

  if (opts.noBrowser !== true && opts.json !== true) {
    try {
      await open(verificationUri);
    } catch {
      // Headless system — that's fine, the URL is on screen.
    }
  }

  const spinner = r.spinner('Waiting for authorization...').start();
  const start = Date.now();
  let interval = Math.max(1, init.interval) * 1000;
  const deadline = start + init.expires_in * 1000;

  // eslint-disable-next-line no-constant-condition
  while (true) {
    if (Date.now() > deadline) {
      spinner.fail('Device code expired.');
      throw new AuthError('Device code expired before authorization completed.');
    }
    await sleep(interval);
    const result = await api.deviceCodePoll(clientId, init.device_code, verifier);
    if ('access_token' in result) {
      await setToken(result.access_token);
      const store = await getCredentialStore();
      spinner.succeed('Logged in.');
      if (opts.json === true) {
        r.json({ ok: true, backend: store.kind });
      } else {
        r.text(r.color.dim(`Token persisted via ${store.kind}.`));
      }
      return;
    }
    if (result.slowDown === true) interval += 5_000;
  }
}

function generatePkceVerifier(): string {
  // 43..128 chars of [A-Z a-z 0-9 - . _ ~]. 32 random bytes -> 43 base64url chars.
  return base64UrlNoPad(randomBytes(32));
}

function pkceChallenge(verifier: string): string {
  return base64UrlNoPad(createHash('sha256').update(verifier).digest());
}

function base64UrlNoPad(buf: Buffer): string {
  return buf.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
