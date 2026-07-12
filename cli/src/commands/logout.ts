// Companion to CLI-001: clear stored credentials from whatever backend is active.
import type { Command } from 'commander';
import { clearToken, getCredentialStore } from '../lib/auth.js';
import { pickRenderer } from '../lib/output.js';
import { exitWithError } from '../lib/errors.js';
import type { GlobalOptions } from '../cli.js';

export function registerLogout(program: Command): void {
  program
    .command('logout')
    .description('Clear stored credentials')
    .action(async (_opts: GlobalOptions, cmd: Command) => {
      const globals = cmd.optsWithGlobals<GlobalOptions>();
      try {
        await runLogout(globals);
      } catch (err) {
        exitWithError(err);
      }
    });
}

export async function runLogout(opts: GlobalOptions): Promise<void> {
  const r = pickRenderer({ json: opts.json, color: opts.color });
  const store = await getCredentialStore();
  const removed = await clearToken();
  if (opts.json === true) {
    r.json({ ok: true, removed, backend: store.kind });
    return;
  }
  if (removed) r.text(r.color.success('Logged out.'));
  else r.text(r.color.dim('No stored credentials.'));
}
