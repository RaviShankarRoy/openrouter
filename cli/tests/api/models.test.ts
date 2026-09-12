import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { runModelsList } from '../../src/api/models.js';
import { ApiClient, type Model } from '../../src/repository/api-client.js';

const SAMPLE: Model[] = [
  {
    id: 'anthropic/claude-sonnet-4',
    provider: 'anthropic',
    modalities: ['text'],
    context_window: 200_000,
    pricing: { input_per_million: 3, output_per_million: 15 },
  },
  {
    id: 'openai/gpt-4o',
    provider: 'openai',
    modalities: ['text', 'image'],
    context_window: 128_000,
    pricing: { input_per_million: 2.5, output_per_million: 10 },
  },
];

let stdoutSpy: ReturnType<typeof vi.spyOn>;
let stderrSpy: ReturnType<typeof vi.spyOn>;
let writes: string[];

beforeEach(() => {
  writes = [];
  stdoutSpy = vi.spyOn(process.stdout, 'write').mockImplementation(((chunk: string | Uint8Array) => {
    writes.push(typeof chunk === 'string' ? chunk : Buffer.from(chunk).toString('utf8'));
    return true;
  }) as never);
  stderrSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true);
});

afterEach(() => {
  stdoutSpy.mockRestore();
  stderrSpy.mockRestore();
});

function fakeApi(models: Model[] = SAMPLE): ApiClient {
  const api = new ApiClient({ baseUrl: 'http://test' });
  vi.spyOn(api, 'listModels').mockResolvedValue(models);
  return api;
}

describe('models list', () => {
  it('renders a table with all models', async () => {
    const api = fakeApi();
    await runModelsList({ json: false, color: false, debug: false }, api);
    const out = writes.join('');
    expect(out).toContain('anthropic/claude-sonnet-4');
    expect(out).toContain('openai/gpt-4o');
    expect(out).toContain('2 model(s)');
  });

  it('emits JSON when --json is set', async () => {
    const api = fakeApi();
    await runModelsList({ json: true, color: false, debug: false }, api);
    const out = writes.join('').trim();
    const parsed = JSON.parse(out) as Model[];
    expect(parsed).toHaveLength(2);
    expect(parsed[0]?.id).toBe('anthropic/claude-sonnet-4');
  });

  it('passes modality through to the API', async () => {
    const api = fakeApi();
    const spy = vi.spyOn(api, 'listModels').mockResolvedValue([SAMPLE[0]!]);
    await runModelsList({ json: true, color: false, debug: false, modality: 'text' }, api);
    expect(spy).toHaveBeenCalledWith('text');
  });

  it('rejects an invalid modality', async () => {
    const api = fakeApi();
    await expect(
      runModelsList({ json: false, color: false, debug: false, modality: 'pdf' }, api),
    ).rejects.toThrow(/invalid modality/);
  });
});
