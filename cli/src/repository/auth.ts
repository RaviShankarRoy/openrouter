// Credential storage with the Adapter pattern:
//   - KeytarStore: native OS keychain (macOS, Windows, Linux+libsecret).
//   - EncryptedFileStore: AES-256-GCM file fallback for headless/WSL/Alpine systems.
// The active backend is auto-selected at startup; preference can be pinned via
// `openrouter` config (authBackend = "keytar" | "encrypted-file" | "auto").
import { mkdir, readFile, writeFile, unlink, chmod } from 'node:fs/promises';
import { join } from 'node:path';
import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'node:crypto';
import { userInfo } from 'node:os';
import { configDir, loadConfig } from './config.js';
import { AuthError } from '../shared/errors.js';
import { logger } from '../shared/logger.js';

export const SERVICE_NAME = 'openrouter-cli';
export const ACCOUNT_NAME = 'default';

export interface CredentialStore {
  readonly kind: 'keytar' | 'encrypted-file';
  get(account?: string): Promise<string | null>;
  set(token: string, account?: string): Promise<void>;
  remove(account?: string): Promise<boolean>;
}

// ---------- Keytar adapter ----------

// Minimal structural type for the bits of keytar we use. Avoids a hard dep on @types/keytar.
interface KeytarLike {
  getPassword(service: string, account: string): Promise<string | null>;
  setPassword(service: string, account: string, password: string): Promise<void>;
  deletePassword(service: string, account: string): Promise<boolean>;
  findCredentials(service: string): Promise<Array<{ account: string; password: string }>>;
}

class KeytarStore implements CredentialStore {
  readonly kind = 'keytar' as const;
  private readonly keytar: KeytarLike;

  constructor(keytar: KeytarLike) {
    this.keytar = keytar;
  }

  async get(account: string = ACCOUNT_NAME): Promise<string | null> {
    return this.keytar.getPassword(SERVICE_NAME, account);
  }

  async set(token: string, account: string = ACCOUNT_NAME): Promise<void> {
    await this.keytar.setPassword(SERVICE_NAME, account, token);
  }

  async remove(account: string = ACCOUNT_NAME): Promise<boolean> {
    return this.keytar.deletePassword(SERVICE_NAME, account);
  }
}

// ---------- Encrypted-file adapter ----------

interface EncryptedRecord {
  v: 1;
  alg: 'aes-256-gcm';
  iv: string;     // base64
  tag: string;    // base64
  salt: string;   // base64
  ct: string;     // base64
}

class EncryptedFileStore implements CredentialStore {
  readonly kind = 'encrypted-file' as const;
  private readonly dir: string;

  constructor(dir: string) {
    this.dir = dir;
  }

  private filePath(account: string): string {
    // account is `default` in the common case; sanitised to allow only [a-z0-9._-].
    const safe = account.replace(/[^a-z0-9._-]/gi, '_');
    return join(this.dir, `creds.${safe}.enc`);
  }

  private deriveKey(salt: Buffer): Buffer {
    // Master secret = OS user identity. Not bulletproof against a local attacker
    // with the same UID — but parity with how SSH keys live on the same disk.
    const ui = userInfo();
    const material = `${ui.username}:${ui.uid}:${ui.homedir}`;
    return scryptSync(material, salt, 32);
  }

  async get(account: string = ACCOUNT_NAME): Promise<string | null> {
    try {
      const raw = await readFile(this.filePath(account), 'utf-8');
      const rec = JSON.parse(raw) as EncryptedRecord;
      if (rec.v !== 1 || rec.alg !== 'aes-256-gcm') return null;
      const key = this.deriveKey(Buffer.from(rec.salt, 'base64'));
      const decipher = createDecipheriv('aes-256-gcm', key, Buffer.from(rec.iv, 'base64'));
      decipher.setAuthTag(Buffer.from(rec.tag, 'base64'));
      const pt = Buffer.concat([decipher.update(Buffer.from(rec.ct, 'base64')), decipher.final()]);
      return pt.toString('utf-8');
    } catch (err) {
      const e = err as NodeJS.ErrnoException;
      if (e.code === 'ENOENT') return null;
      throw new AuthError('Failed to read encrypted credentials.', { cause: err });
    }
  }

  async set(token: string, account: string = ACCOUNT_NAME): Promise<void> {
    const salt = randomBytes(16);
    const iv = randomBytes(12);
    const key = this.deriveKey(salt);
    const cipher = createCipheriv('aes-256-gcm', key, iv);
    const ct = Buffer.concat([cipher.update(Buffer.from(token, 'utf-8')), cipher.final()]);
    const tag = cipher.getAuthTag();
    const rec: EncryptedRecord = {
      v: 1,
      alg: 'aes-256-gcm',
      iv: iv.toString('base64'),
      tag: tag.toString('base64'),
      salt: salt.toString('base64'),
      ct: ct.toString('base64'),
    };
    await mkdir(this.dir, { recursive: true });
    const path = this.filePath(account);
    await writeFile(path, JSON.stringify(rec), { mode: 0o600 });
    await chmod(path, 0o600);
  }

  async remove(account: string = ACCOUNT_NAME): Promise<boolean> {
    try {
      await unlink(this.filePath(account));
      return true;
    } catch (err) {
      const e = err as NodeJS.ErrnoException;
      if (e.code === 'ENOENT') return false;
      throw new AuthError('Failed to remove encrypted credentials.', { cause: err });
    }
  }
}

// ---------- Selection ----------

let cachedStore: CredentialStore | undefined;

async function loadKeytar(): Promise<CredentialStore | null> {
  try {
    // Dynamic import: keytar is optional & native. Failure to load is non-fatal.
    const mod = (await import('keytar').catch(() => null)) as
      | (KeytarLike & { default?: KeytarLike })
      | null;
    if (!mod) return null;
    const keytar: KeytarLike = mod.default ?? mod;
    // Probe the backend. Linux without libsecret throws on the first call.
    await keytar.findCredentials(SERVICE_NAME);
    return new KeytarStore(keytar);
  } catch (err) {
    logger.debug({ err }, 'keytar unavailable, falling back to encrypted file');
    return null;
  }
}

export async function getCredentialStore(): Promise<CredentialStore> {
  if (cachedStore) return cachedStore;
  const cfg = await loadConfig();

  if (cfg.authBackend === 'encrypted-file') {
    cachedStore = new EncryptedFileStore(configDir());
    return cachedStore;
  }
  if (cfg.authBackend === 'keytar') {
    const k = await loadKeytar();
    if (!k) throw new AuthError('keytar backend requested but unavailable on this system.');
    cachedStore = k;
    return cachedStore;
  }
  // auto
  const k = await loadKeytar();
  cachedStore = k ?? new EncryptedFileStore(configDir());
  return cachedStore;
}

export async function getToken(): Promise<string | null> {
  const store = await getCredentialStore();
  return store.get();
}

export async function setToken(token: string): Promise<void> {
  const store = await getCredentialStore();
  await store.set(token);
}

export async function clearToken(): Promise<boolean> {
  const store = await getCredentialStore();
  return store.remove();
}

export async function requireToken(): Promise<string> {
  const t = await getToken();
  if (!t) throw new AuthError('Not logged in.');
  return t;
}

// Refresh stub — device-flow access tokens here are long-lived API keys returned
// by the gateway. If/when the gateway issues short-lived tokens with refresh, this
// function is the single hook to wire them.
export async function refreshIfNeeded(token: string): Promise<string> {
  return token;
}

// Test seam.
export function _resetForTests(): void {
  cachedStore = undefined;
}
