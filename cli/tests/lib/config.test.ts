import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mkdtempSync, rmSync, writeFileSync, mkdirSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

// We mock `env-paths` so config.ts resolves to a temp directory under our control.
let TMP: string;

vi.mock('env-paths', () => {
  return {
    default: () => ({
      data: join(TMP, 'data'),
      config: join(TMP, 'config'),
      cache: join(TMP, 'cache'),
      log: join(TMP, 'log'),
      temp: join(TMP, 'temp'),
    }),
  };
});

beforeEach(() => {
  TMP = mkdtempSync(join(tmpdir(), 'orcli-cfg-'));
  mkdirSync(join(TMP, 'config'), { recursive: true });
});

afterEach(() => {
  rmSync(TMP, { recursive: true, force: true });
  vi.resetModules();
});

describe('config', () => {
  it('returns defaults when no file exists', async () => {
    const mod = await import('../../src/lib/config.js');
    mod.resetConfigCache();
    const cfg = await mod.loadConfig();
    expect(cfg.baseUrl).toMatch(/^https?:\/\//);
    expect(cfg.defaultModel.length).toBeGreaterThan(0);
    expect(cfg.authBackend).toBe('auto');
  });

  it('reads an existing config file', async () => {
    const mod = await import('../../src/lib/config.js');
    mod.resetConfigCache();
    writeFileSync(
      mod.configFile(),
      JSON.stringify({
        baseUrl: 'https://example.com/v1',
        defaultModel: 'foo/bar',
        authBackend: 'encrypted-file',
      }),
    );
    const cfg = await mod.loadConfig();
    expect(cfg.baseUrl).toBe('https://example.com/v1');
    expect(cfg.defaultModel).toBe('foo/bar');
    expect(cfg.authBackend).toBe('encrypted-file');
  });

  it('rejects an invalid file', async () => {
    const mod = await import('../../src/lib/config.js');
    mod.resetConfigCache();
    writeFileSync(mod.configFile(), JSON.stringify({ baseUrl: 'not-a-url' }));
    await expect(mod.loadConfig()).rejects.toThrow(/Invalid config/);
  });

  it('persists changes via saveConfig with 0600 mode', async () => {
    const mod = await import('../../src/lib/config.js');
    mod.resetConfigCache();
    const next = await mod.saveConfig({ defaultModel: 'a/b' });
    expect(next.defaultModel).toBe('a/b');
    const onDisk = JSON.parse(readFileSync(mod.configFile(), 'utf-8')) as { defaultModel: string };
    expect(onDisk.defaultModel).toBe('a/b');
  });
});
