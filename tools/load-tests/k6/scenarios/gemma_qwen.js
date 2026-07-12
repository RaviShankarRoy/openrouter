// Gemma 4 + Qwen 3.6 load scenario.
//
// Rotates through the open-weight catalog so the dashboard slices by model.
// Why this matters: open-weight providers (Together, Fireworks, Ollama) have
// different throughput caps and warm-up behaviour than OpenAI/Anthropic.
// This scenario isolates that so a regression in the gemma/qwen path doesn't
// hide inside the OpenAI numbers.
//
// Run:
//   make gemma-qwen           # default config (10 VUs, 2 min)
//   make gemma-qwen-stream    # streaming variant

import http from 'k6/http';
import { sleep } from 'k6';
import { authHeaders } from '../lib/auth.js';
import { chatPayload, streamingChatPayload, tagsFor } from '../lib/payloads.js';
import { checkChatResponse, checkStreamingResponse } from '../lib/checks.js';
import { withBase } from '../options.js';
import { smokeThresholds } from '../thresholds.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const STREAM = __ENV.STREAM === '1';

// Catalog from gateway-go/configs/providers.yaml. Add new model IDs here
// when extending the open-weight pool.
const MODELS = [
  'google/gemma-4-31b',
  'google/gemma-4-26b-moe',
  'google/gemma-4-e4b',
  'qwen/qwen3.6-27b',
  'qwen/qwen3.6-35b-a3b',
  'qwen/qwen3.5-35b-a3b',
];

export const options = withBase({
  vus: Number(__ENV.VUS) || 10,
  duration: __ENV.DURATION || '2m',
  // Looser than the OpenAI thresholds: open-weight provider latency varies
  // widely between Together / Fireworks. Tune once you have baseline data.
  thresholds: {
    ...smokeThresholds,
    http_req_duration: ['p(95)<2500'],
    http_req_failed: ['rate<0.02'],
  },
  tags: { scenario: 'gemma_qwen', stream: String(STREAM) },
});

export default function () {
  // Pick a model by VU * iteration so each VU exercises every model evenly.
  const model = MODELS[(__VU + __ITER) % MODELS.length];
  const payload = STREAM
    ? streamingChatPayload('small')
    : chatPayload('small', { model });
  // streamingChatPayload calls chatPayload('small', {stream:true}) — re-wrap
  // to inject our model when streaming.
  const body = STREAM
    ? chatPayload('small', { model, stream: true })
    : payload;

  const res = http.post(`${BASE_URL}/api/v1/chat/completions`, body, {
    headers: authHeaders(STREAM ? { Accept: 'text/event-stream' } : {}),
    tags: { ...tagsFor('small'), model },
    timeout: '30s',
  });

  if (STREAM) {
    checkStreamingResponse(res);
  } else {
    checkChatResponse(res);
  }
  sleep(0.5);
}
