// CLI-005 — API key management.
//   keys create <name>   create a new key (printed once)
//   keys list             list keys (no secrets)
//   keys revoke <id>      revoke a key (prompts for confirmation unless --yes)
import type { Command } from 'commander';
import { confirm } from '@inquirer/prompts';
import { ApiClient } from '../lib/api-client.js';
import { pickRenderer } from '../lib/output.js';
import { ValidationError, exitWithError } from '../lib/errors.js';
import type { GlobalOptions } from '../cli.js';

export type KeysCreateOptions = GlobalOptions;
export type KeysListOptions = GlobalOptions;
export interface KeysRevokeOptions extends GlobalOptions {
  yes?: boolean;
}

export function registerKeys(program: Command): void {
  const cmd = program
    .command('keys')
    .description('Manage API keys (CLI-005)');

  cmd
    .command('create <name>')
    .description('Create a new API key')
    .action(async (name: string, opts: KeysCreateOptions, sub: Command) => {
      const globals = sub.optsWithGlobals<KeysCreateOptions>();
      try {
        await runKeysCreate(name, { ...globals, ...opts });
      } catch (err) {
        exitWithError(err);
      }
    });

  cmd
    .command('list')
    .description('List API keys')
    .action(async (opts: KeysListOptions, sub: Command) => {
      const globals = sub.optsWithGlobals<KeysListOptions>();
      try {
        await runKeysList({ ...globals, ...opts });
      } catch (err) {
        exitWithError(err);
      }
    });

  cmd
    .command('revoke <id>')
    .description('Revoke an API key')
    .option('-y, --yes', 'skip confirmation', false)
    .action(async (id: string, opts: KeysRevokeOptions, sub: Command) => {
      const globals = sub.optsWithGlobals<KeysRevokeOptions>();
      try {
        await runKeysRevoke(id, { ...globals, ...opts });
      } catch (err) {
        if ((err as { name?: string }).name === 'ExitPromptError') return;
        exitWithError(err);
      }
    });
}

export async function runKeysCreate(
  name: string,
  opts: KeysCreateOptions,
  apiOverride?: ApiClient,
): Promise<void> {
  if (name.trim().length === 0) throw new ValidationError('key name is required.');
  const r = pickRenderer({ json: opts.json, color: opts.color });
  const api = apiOverride ?? (await ApiClient.create({ ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}) }));
  const key = await api.createKey(name);
  if (opts.json === true) {
    r.json(key);
    return;
  }
  r.text(r.color.success(`Key "${key.name}" created.`));
  r.text('');
  r.text(r.color.bold('Secret (shown only once):'));
  r.text(`  ${key.secret}`);
  r.text('');
  r.text(r.color.warn('Store this securely — it will not be displayed again.'));
}

export async function runKeysList(opts: KeysListOptions, apiOverride?: ApiClient): Promise<void> {
  const r = pickRenderer({ json: opts.json, color: opts.color });
  const api = apiOverride ?? (await ApiClient.create({ ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}) }));
  const keys = await api.listKeys();
  if (opts.json === true) {
    r.json(keys);
    return;
  }
  if (keys.length === 0) {
    r.text(r.color.dim('No API keys.'));
    return;
  }
  r.table(
    ['ID', 'NAME', 'PREFIX', 'CREATED', 'LAST USED', 'STATUS'],
    keys.map((k): readonly string[] => [
      k.id,
      k.name,
      k.prefix,
      k.created_at,
      k.last_used_at ?? '-',
      k.revoked_at ? r.color.error('revoked') : r.color.success('active'),
    ]),
  );
}

export async function runKeysRevoke(
  id: string,
  opts: KeysRevokeOptions,
  apiOverride?: ApiClient,
): Promise<void> {
  if (id.trim().length === 0) throw new ValidationError('key id is required.');
  const r = pickRenderer({ json: opts.json, color: opts.color });

  if (opts.yes !== true && opts.json !== true) {
    const ok = await confirm({ message: `Revoke key ${id}?`, default: false });
    if (!ok) {
      r.text(r.color.dim('Aborted.'));
      return;
    }
  }
  const api = apiOverride ?? (await ApiClient.create({ ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}) }));
  await api.revokeKey(id);
  if (opts.json === true) {
    r.json({ ok: true, id });
    return;
  }
  r.text(r.color.success(`Revoked ${id}.`));
}
