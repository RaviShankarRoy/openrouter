// XDG-compliant config dir resolution and JSON-backed persistence. Stores non-secret
// preferences only — auth tokens go through repository/auth.ts (keychain or encrypted file).
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import envPaths from 'env-paths';
import { z } from 'zod';
import { ConfigError } from '../shared/errors.js';

const PATHS = envPaths('openrouter-cli', { suffix: '' });

export const ConfigSchema = z.object({
  baseUrl: z.string().url().default('https://api.openrouter.example.com/api/v1'),
  defaultModel: z.string().default('anthropic/claude-sonnet-4-20250514'),
  authBackend: z.enum(['keytar', 'encrypted-file', 'auto']).default('auto'),
});

export type CliConfig = z.infer<typeof ConfigSchema>;

const DEFAULTS: CliConfig = ConfigSchema.parse({});

export function configDir(): string {
  return PATHS.config;
}

export function configFile(): string {
  return join(PATHS.config, 'config.json');
}

export function dataDir(): string {
  return PATHS.data;
}

let cached: CliConfig | undefined;

export async function loadConfig(): Promise<CliConfig> {
  if (cached) return cached;
  try {
    const raw = await readFile(configFile(), 'utf-8');
    const parsed = ConfigSchema.safeParse(JSON.parse(raw));
    if (!parsed.success) {
      throw new ConfigError(`Invalid config at ${configFile()}: ${parsed.error.message}`);
    }
    cached = parsed.data;
    return cached;
  } catch (err) {
    const e = err as NodeJS.ErrnoException;
    if (e.code === 'ENOENT') {
      cached = DEFAULTS;
      return cached;
    }
    throw err;
  }
}

export async function saveConfig(next: Partial<CliConfig>): Promise<CliConfig> {
  const current = await loadConfig();
  const merged = ConfigSchema.parse({ ...current, ...next });
  const path = configFile();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(merged, null, 2) + '\n', { mode: 0o600 });
  cached = merged;
  return merged;
}

export function resetConfigCache(): void {
  cached = undefined;
}

export function defaultConfig(): CliConfig {
  return { ...DEFAULTS };
}
