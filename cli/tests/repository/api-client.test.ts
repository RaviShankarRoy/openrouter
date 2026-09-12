import { describe, it, expect, vi } from 'vitest';
import { Readable } from 'node:stream';
import { ApiClient } from '../../src/repository/api-client.js';
import { AuthError, RateLimitError, ServerError, ValidationError } from '../../src/shared/errors.js';

interface FakeResponse {
  statusCode: number;
  headers: Record<string, string | string[] | undefined>;
  body: { json: () => Promise<unknown>; dump: () => Promise<void> };
}

function jsonBody(value: unknown): FakeResponse['body'] {
  return {
    json: async () => value,
    dump: async () => undefined,
  };
}

function makeFetch(responses: FakeResponse[]): {
  fn: ReturnType<typeof vi.fn>;
  calls: Array<{ url: string; init: { method?: string; headers?: Record<string, string>; body?: string | undefined } }>;
} {
  const calls: Array<{ url: string; init: { method?: string; headers?: Record<string, string>; body?: string | undefined } }> = [];
  let i = 0;
  const fn = vi.fn(async (url: string, init: { method?: string; headers?: Record<string, string>; body?: string | undefined }) => {
    calls.push({ url, init });
    const r = responses[i++];
    if (!r) throw new Error('no more queued responses');
    return r;
  });
  return { fn, calls };
}

describe('ApiClient', () => {
  it('GETs /models and returns the data array', async () => {
    const data = [{ id: 'm', provider: 'p', modalities: ['text'], pricing: {} }];
    const { fn, calls } = makeFetch([
      { statusCode: 200, headers: {}, body: jsonBody({ data }) },
    ]);
    const api = new ApiClient({
      baseUrl: 'http://x',
      token: 't',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      fetchImpl: fn as any,
    });
    const res = await api.listModels();
    expect(res).toEqual(data);
    expect(calls[0]?.url).toBe('http://x/models');
    expect(calls[0]?.init.method).toBe('GET');
    expect(calls[0]?.init.headers?.authorization).toBe('Bearer t');
  });

  it('forwards modality query parameter', async () => {
    const { fn, calls } = makeFetch([
      { statusCode: 200, headers: {}, body: jsonBody({ data: [] }) },
    ]);
    const api = new ApiClient({ baseUrl: 'http://x', fetchImpl: fn as never });
    await api.listModels('image');
    expect(calls[0]?.url).toBe('http://x/models?modality=image');
  });

  it('maps 401 -> AuthError', async () => {
    const { fn } = makeFetch([
      {
        statusCode: 401,
        headers: {},
        body: jsonBody({ error: { message: 'bad key', type: 'auth' } }),
      },
    ]);
    const api = new ApiClient({ baseUrl: 'http://x', fetchImpl: fn as never });
    await expect(api.listModels()).rejects.toBeInstanceOf(AuthError);
  });

  it('maps 400 -> ValidationError', async () => {
    const { fn } = makeFetch([
      {
        statusCode: 400,
        headers: {},
        body: jsonBody({ error: { message: 'bad', type: 'invalid_request' } }),
      },
    ]);
    const api = new ApiClient({ baseUrl: 'http://x', fetchImpl: fn as never });
    await expect(api.listModels()).rejects.toBeInstanceOf(ValidationError);
  });

  it('maps 429 -> RateLimitError with Retry-After', async () => {
    const { fn } = makeFetch([
      {
        statusCode: 429,
        headers: { 'retry-after': '7' },
        body: jsonBody({ error: { message: 'slow down', type: 'rate_limited' } }),
      },
    ]);
    const api = new ApiClient({ baseUrl: 'http://x', fetchImpl: fn as never });
    const err = await api.listModels().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(RateLimitError);
    expect((err as RateLimitError).retryAfterSeconds).toBe(7);
  });

  it('maps 503 -> ServerError', async () => {
    const { fn } = makeFetch([
      {
        statusCode: 503,
        headers: {},
        body: jsonBody({ error: { message: 'down', type: 'unavailable' } }),
      },
    ]);
    const api = new ApiClient({ baseUrl: 'http://x', fetchImpl: fn as never });
    await expect(api.listModels()).rejects.toBeInstanceOf(ServerError);
  });

  it('parses streaming chat completions', async () => {
    const lines = [
      'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m","choices":[{"index":0,"delta":{"content":"hi "},"finish_reason":null}]}\n\n',
      'data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"m","choices":[{"index":0,"delta":{"content":"there"},"finish_reason":null}]}\n\n',
      'data: [DONE]\n\n',
    ];
    const body = Readable.from(lines.map((l) => Buffer.from(l, 'utf-8')));
    const { fn } = makeFetch([
      {
        statusCode: 200,
        headers: {},
        // streaming endpoint: body is the stream itself; we override the body shape.
        body: {
          json: async () => ({}),
          dump: async () => undefined,
        },
      },
    ]);
    // Override the second branch: the streaming method reads `res.body` as an iterable.
    fn.mockImplementationOnce(async () => ({
      statusCode: 200,
      headers: {},
      body,
    }));
    const api = new ApiClient({ baseUrl: 'http://x', fetchImpl: fn as never });
    const out: string[] = [];
    for await (const chunk of api.chatCompletionStream({
      model: 'm',
      messages: [{ role: 'user', content: 'hi' }],
    })) {
      out.push(chunk.choices[0]?.delta.content ?? '');
    }
    expect(out.join('')).toBe('hi there');
  });
});
