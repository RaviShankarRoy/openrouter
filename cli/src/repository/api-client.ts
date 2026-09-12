// Repository for the gateway HTTP surface. The only file in the CLI that knows
// the wire format. Built on undici for native HTTP/2 + connection pooling.
//
// Endpoint paths track shared/openapi/openapi.yaml. Auth header is injected from
// repository/auth.ts. SSE parsing follows the OpenAI streaming chunk format.
import { request, type Dispatcher } from 'undici';
import { getVersion } from './version.js';
import { loadConfig } from './config.js';
import { getToken, refreshIfNeeded } from './auth.js';
import {
  AuthError,
  NetworkError,
  RateLimitError,
  ServerError,
  ValidationError,
} from '../shared/errors.js';

// --- Wire types (subset of the OpenAPI schema we actually consume here) ---

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  name?: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
}

export interface ChatCompletionChoice {
  index: number;
  message: ChatMessage;
  finish_reason: string | null;
}

export interface ChatCompletionResponse {
  id: string;
  object: 'chat.completion';
  created: number;
  model: string;
  choices: ChatCompletionChoice[];
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface ChatCompletionDelta {
  role?: ChatMessage['role'];
  content?: string;
}

export interface ChatCompletionChunk {
  id: string;
  object: 'chat.completion.chunk';
  created: number;
  model: string;
  choices: Array<{
    index: number;
    delta: ChatCompletionDelta;
    finish_reason: string | null;
  }>;
}

export interface Pricing {
  input_per_million?: number;
  output_per_million?: number;
  cached_input_per_million?: number;
}

export interface Model {
  id: string;
  provider: string;
  modalities: string[];
  context_window?: number;
  pricing: Pricing;
}

export interface ListModelsResponse {
  data: Model[];
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at?: string | null;
  revoked_at?: string | null;
}

export interface ApiKeyWithSecret extends ApiKey {
  secret: string;
}

export interface UsagePeriodPoint {
  date: string;     // ISO 8601 day
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
}

export interface UsageResponse {
  period: 'day' | 'week' | 'month';
  start: string;
  end: string;
  totals: {
    requests: number;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
  };
  series: UsagePeriodPoint[];
}

export interface DeviceCodeResponse {
  device_code: string;
  user_code: string;
  verification_uri: string;
  verification_uri_complete?: string;
  expires_in: number;
  interval: number;
}

export interface DeviceTokenResponse {
  access_token: string;
  token_type: 'Bearer';
  expires_in?: number;
  refresh_token?: string;
}

// --- Error envelope ---

interface ApiErrorBody {
  error: {
    message: string;
    type: string;
    code?: string;
    param?: string;
  };
}

// --- Client ---

export interface ApiClientOptions {
  baseUrl?: string;
  token?: string;
  timeoutMs?: number;
  fetchImpl?: typeof request;
}

const DEFAULT_TIMEOUT_MS = 60_000;

export class ApiClient {
  private readonly baseUrl: string;
  private readonly token: string | undefined;
  private readonly timeoutMs: number;
  private readonly fetchImpl: typeof request;

  constructor(opts: ApiClientOptions = {}) {
    this.baseUrl = opts.baseUrl ?? '';
    this.token = opts.token;
    this.timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.fetchImpl = opts.fetchImpl ?? request;
  }

  static async create(overrides: { baseUrl?: string } = {}): Promise<ApiClient> {
    const cfg = await loadConfig();
    const token = (await getToken()) ?? undefined;
    const refreshed = token ? await refreshIfNeeded(token) : undefined;
    return new ApiClient({
      baseUrl: overrides.baseUrl ?? cfg.baseUrl,
      ...(refreshed !== undefined ? { token: refreshed } : {}),
    });
  }

  // --- Public API ---

  async listModels(modality?: string): Promise<Model[]> {
    const path = modality ? `/models?modality=${encodeURIComponent(modality)}` : '/models';
    const res = await this.requestJson<ListModelsResponse>('GET', path);
    return res.data;
  }

  async chatCompletion(req: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    return this.requestJson<ChatCompletionResponse>('POST', '/chat/completions', {
      ...req,
      stream: false,
    });
  }

  async *chatCompletionStream(req: ChatCompletionRequest): AsyncGenerator<ChatCompletionChunk> {
    const url = this.url('/chat/completions');
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await this.fetchImpl(url, {
        method: 'POST',
        headers: this.headers({ accept: 'text/event-stream' }),
        body: JSON.stringify({ ...req, stream: true }),
        signal: ctrl.signal,
      });
      await this.assertOk(res);
      yield* parseSseChunks(res.body);
    } finally {
      clearTimeout(timer);
    }
  }

  async listKeys(): Promise<ApiKey[]> {
    const res = await this.requestJson<{ data: ApiKey[] }>('GET', '/keys');
    return res.data;
  }

  async createKey(name: string): Promise<ApiKeyWithSecret> {
    return this.requestJson<ApiKeyWithSecret>('POST', '/keys', { name });
  }

  async revokeKey(id: string): Promise<void> {
    await this.requestVoid('DELETE', `/keys/${encodeURIComponent(id)}`);
  }

  async getUsage(period: 'day' | 'week' | 'month'): Promise<UsageResponse> {
    return this.requestJson<UsageResponse>('GET', `/usage?period=${period}`);
  }

  // --- OAuth device-code flow ---

  async deviceCodeStart(clientId: string, codeChallenge: string): Promise<DeviceCodeResponse> {
    const params = new URLSearchParams({
      client_id: clientId,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
      scope: 'cli:full',
    });
    const url = this.url('/oauth/device/code');
    const res = await this.fetchImpl(url, {
      method: 'POST',
      headers: this.headers({ contentType: 'application/x-www-form-urlencoded' }),
      body: params.toString(),
    });
    await this.assertOk(res);
    return (await res.body.json()) as DeviceCodeResponse;
  }

  async deviceCodePoll(
    clientId: string,
    deviceCode: string,
    codeVerifier: string,
  ): Promise<DeviceTokenResponse | { pending: true; slowDown?: boolean }> {
    const params = new URLSearchParams({
      client_id: clientId,
      grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
      device_code: deviceCode,
      code_verifier: codeVerifier,
    });
    const url = this.url('/oauth/token');
    const res = await this.fetchImpl(url, {
      method: 'POST',
      headers: this.headers({ contentType: 'application/x-www-form-urlencoded' }),
      body: params.toString(),
    });
    if (res.statusCode === 200) {
      return (await res.body.json()) as DeviceTokenResponse;
    }
    // OAuth error responses: authorization_pending | slow_down | access_denied | expired_token.
    const body = (await res.body.json().catch(() => ({}))) as { error?: string };
    if (body.error === 'authorization_pending') return { pending: true };
    if (body.error === 'slow_down') return { pending: true, slowDown: true };
    if (body.error === 'access_denied') throw new AuthError('Authorization denied by user.');
    if (body.error === 'expired_token') throw new AuthError('Device code expired. Try login again.');
    throw new AuthError(`OAuth error: ${body.error ?? `HTTP ${res.statusCode}`}`);
  }

  // --- Internals ---

  private url(path: string): string {
    return `${this.baseUrl.replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}`;
  }

  private headers(extra: { accept?: string; contentType?: string } = {}): Record<string, string> {
    const v = getVersion();
    const h: Record<string, string> = {
      'user-agent': `${v.name}/${v.cli} (node/${v.node})`,
      'accept': extra.accept ?? 'application/json',
      'content-type': extra.contentType ?? 'application/json',
    };
    if (this.token) h['authorization'] = `Bearer ${this.token}`;
    return h;
  }

  private async requestJson<T>(method: Dispatcher.HttpMethod, path: string, body?: unknown): Promise<T> {
    const url = this.url(path);
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const init: Parameters<typeof request>[1] = {
        method,
        headers: this.headers(),
        signal: ctrl.signal,
      };
      if (body !== undefined) init.body = JSON.stringify(body);
      const res = await this.fetchImpl(url, init);
      await this.assertOk(res);
      return (await res.body.json()) as T;
    } catch (err) {
      throw this.normaliseTransport(err);
    } finally {
      clearTimeout(timer);
    }
  }

  private async requestVoid(method: Dispatcher.HttpMethod, path: string): Promise<void> {
    const url = this.url(path);
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await this.fetchImpl(url, {
        method,
        headers: this.headers(),
        signal: ctrl.signal,
      });
      await this.assertOk(res);
      // Drain to release the connection.
      await res.body.dump();
    } catch (err) {
      throw this.normaliseTransport(err);
    } finally {
      clearTimeout(timer);
    }
  }

  private normaliseTransport(err: unknown): Error {
    if (err instanceof AuthError || err instanceof ServerError || err instanceof ValidationError) {
      return err;
    }
    const code = (err as NodeJS.ErrnoException).code;
    if (code === 'ABORT_ERR' || code === 'UND_ERR_ABORTED') {
      return new NetworkError(`Request timed out after ${this.timeoutMs}ms`, { cause: err });
    }
    if (code === 'ENOTFOUND' || code === 'ECONNREFUSED' || code === 'ECONNRESET') {
      return new NetworkError(`Cannot reach ${this.baseUrl}: ${code}`, { cause: err });
    }
    return new NetworkError((err as Error).message ?? 'Network error', { cause: err });
  }

  private async assertOk(res: { statusCode: number; body: { json: () => Promise<unknown>; dump: () => Promise<void> }; headers: Record<string, string | string[] | undefined> }): Promise<void> {
    if (res.statusCode >= 200 && res.statusCode < 300) return;
    let body: ApiErrorBody | undefined;
    try {
      body = (await res.body.json()) as ApiErrorBody;
    } catch {
      await res.body.dump().catch(() => undefined);
    }
    const message = body?.error?.message ?? `HTTP ${res.statusCode}`;
    if (res.statusCode === 401 || res.statusCode === 403) {
      throw new AuthError(message);
    }
    if (res.statusCode === 400 || res.statusCode === 422) {
      throw new ValidationError(message);
    }
    if (res.statusCode === 429) {
      const ra = parseRetryAfter(res.headers['retry-after']);
      throw new RateLimitError(message, ra);
    }
    throw new ServerError(message, res.statusCode);
  }
}

function parseRetryAfter(h: string | string[] | undefined): number | undefined {
  if (!h) return undefined;
  const value = Array.isArray(h) ? h[0] : h;
  if (value === undefined) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

// ---------- SSE parser (DRD GW-002) ----------
//
// Parses a Server-Sent Events stream of OpenAI-style chunks.
// Each event is a `data:` line followed by JSON, terminated by a blank line,
// with the sentinel `data: [DONE]` to signal completion.
export async function* parseSseChunks(
  body: NodeJS.ReadableStream | AsyncIterable<Uint8Array>,
): AsyncGenerator<ChatCompletionChunk> {
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  for await (const chunkRaw of body as AsyncIterable<Uint8Array | string>) {
    const chunk =
      typeof chunkRaw === 'string'
        ? chunkRaw
        : decoder.decode(chunkRaw, { stream: true });
    buffer += chunk;

    // SSE event boundary is a blank line. Tolerate \r\n, \n\n, \r\r.
    let idx: number;
    while ((idx = indexOfEventBoundary(buffer)) !== -1) {
      const event = buffer.slice(0, idx);
      buffer = buffer.slice(idx).replace(/^(\r?\n){2}|^\r{2}/, '');

      const data = extractDataPayload(event);
      if (data === undefined) continue;
      if (data === '[DONE]') return;

      try {
        yield JSON.parse(data) as ChatCompletionChunk;
      } catch {
        // Malformed chunk — skip, keep streaming.
      }
    }
  }
  // Flush trailing event without terminator.
  if (buffer.trim().length > 0) {
    const data = extractDataPayload(buffer);
    if (data !== undefined && data !== '[DONE]') {
      try {
        yield JSON.parse(data) as ChatCompletionChunk;
      } catch {
        /* ignore */
      }
    }
  }
}

function indexOfEventBoundary(s: string): number {
  const a = s.indexOf('\n\n');
  const b = s.indexOf('\r\n\r\n');
  if (a === -1) return b;
  if (b === -1) return a;
  return Math.min(a, b);
}

function extractDataPayload(event: string): string | undefined {
  // SSE allows comments (`:` prefix) and other field types. We only consume `data:`.
  const lines = event.split(/\r?\n/);
  const data: string[] = [];
  for (const line of lines) {
    if (line.startsWith('data:')) {
      data.push(line.slice(5).replace(/^ /, ''));
    }
  }
  if (data.length === 0) return undefined;
  return data.join('\n');
}
