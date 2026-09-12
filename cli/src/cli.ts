#!/usr/bin/env node
// Entry point. Wires commander, applies global options, dispatches subcommands.
// Implements DRD CLI-001..CLI-005 surface registration.
import { Command, Option } from 'commander';
import { getVersion } from './repository/version.js';
import { exitWithError } from './shared/errors.js';
import { registerLogin } from './api/login.js';
import { registerLogout } from './api/logout.js';
import { registerModels } from './api/models.js';
import { registerChat } from './api/chat.js';
import { registerUsage } from './api/usage.js';
import { registerKeys } from './api/keys.js';

export interface GlobalOptions {
  json: boolean;
  color: boolean;
  debug: boolean;
  baseUrl?: string;
}

export function buildProgram(): Command {
  const program = new Command();
  const v = getVersion();

  program
    .name('openrouter')
    .description('OpenRouter CLI — login, list models, chat, manage keys, view usage.')
    .version(`${v.cli} (node ${v.node})`, '-V, --version', 'output the version number')
    .option('--json', 'machine-readable JSON output', false)
    .addOption(new Option('--no-color', 'disable ANSI color (also: NO_COLOR=1)'))
    .option('--debug', 'verbose logs', false)
    .option('--base-url <url>', 'override gateway base URL')
    .showHelpAfterError(true)
    .enablePositionalOptions();

  registerLogin(program);
  registerLogout(program);
  registerModels(program);
  registerChat(program);
  registerUsage(program);
  registerKeys(program);

  return program;
}

export async function main(argv: readonly string[] = process.argv): Promise<void> {
  // NO_COLOR per https://no-color.org/.
  if (process.env['NO_COLOR'] !== undefined && process.env['NO_COLOR'] !== '') {
    process.env['FORCE_COLOR'] = '0';
  }
  const program = buildProgram();
  try {
    await program.parseAsync(argv as string[]);
  } catch (err) {
    exitWithError(err);
  }
}

// Run only when invoked as the entry script. tsup bundling preserves import.meta.url.
const invokedAsScript =
  typeof process !== 'undefined' &&
  Array.isArray(process.argv) &&
  process.argv[1] !== undefined &&
  import.meta.url === `file://${process.argv[1]}`;

if (invokedAsScript) {
  void main();
}
