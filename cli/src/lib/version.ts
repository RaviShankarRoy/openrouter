// Resolves package version at runtime. Reads package.json relative to the bundled output
// (works in dev via tsx and after tsup bundling — package.json sits one level up from dist/).
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

interface PkgJson {
  name?: string;
  version?: string;
}

export interface VersionInfo {
  cli: string;
  node: string;
  name: string;
}

let cached: VersionInfo | undefined;

export function getVersion(): VersionInfo {
  if (cached) return cached;

  let version = '0.0.0';
  let name = '@openrouter/cli';
  try {
    const here = dirname(fileURLToPath(import.meta.url));
    // Try sibling package.json first (when running from dist/), then parent (dev/tsx case).
    const candidates = [
      resolve(here, '..', 'package.json'),
      resolve(here, '..', '..', 'package.json'),
    ];
    for (const path of candidates) {
      try {
        const raw = readFileSync(path, 'utf-8');
        const pkg = JSON.parse(raw) as PkgJson;
        if (pkg.version) {
          version = pkg.version;
          name = pkg.name ?? name;
          break;
        }
      } catch {
        // try next candidate
      }
    }
  } catch {
    // fall through with defaults
  }

  cached = {
    cli: version,
    node: process.versions.node,
    name,
  };
  return cached;
}
