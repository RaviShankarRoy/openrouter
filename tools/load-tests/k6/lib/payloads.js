// Chat completion payloads of varying sizes. Each payload exposes a `tag`
// string so the gateway-specific timing slice (`kind:gateway`) shows in
// the per-payload breakdown of the summary.

const SMALL_PROMPT = 'hi';
const MEDIUM_PROMPT =
  'Summarize the following: ' + 'lorem ipsum dolor sit amet '.repeat(20);
const LARGE_PROMPT = 'Here is a long context: ' + 'lorem ipsum '.repeat(500);

export const sizes = {
  small: { prompt: SMALL_PROMPT, max_tokens: 32 },
  medium: { prompt: MEDIUM_PROMPT, max_tokens: 256 },
  large: { prompt: LARGE_PROMPT, max_tokens: 1024 },
};

export function chatPayload(size = 'small', extra = {}) {
  const cfg = sizes[size] || sizes.small;
  return JSON.stringify({
    model: extra.model || 'gpt-4o-mini',
    messages: [{ role: 'user', content: cfg.prompt }],
    max_tokens: cfg.max_tokens,
    stream: extra.stream || false,
    ...extra,
  });
}

export function streamingChatPayload(size = 'small') {
  return chatPayload(size, { stream: true });
}

export function toolCallPayload() {
  // PI-004 — exercises the tool_calls return path.
  return JSON.stringify({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: 'use the lookup tool' }],
    tools: [
      {
        type: 'function',
        function: {
          name: 'lookup',
          description: 'search a knowledge base',
          parameters: { type: 'object', properties: { q: { type: 'string' } } },
        },
      },
    ],
  });
}

// Pre-baked tag set — k6 metric labels for each payload variant.
export const tagsFor = (size) => ({ kind: 'gateway', payload: size });
