// Streaming-specific load test — proves NFR-003 (TTFT < 200 ms).
//
// Uses the constant-VU executor (not arrival-rate) because each iteration
// holds the connection open for the duration of the SSE response — a fixed
// rate would queue up unboundedly.

import http from 'k6/http';
import { Trend } from 'k6/metrics';
import { authHeaders } from '../lib/auth.js';
import { streamingChatPayload, tagsFor } from '../lib/payloads.js';
import { checkStreamingResponse } from '../lib/checks.js';
import { withBase } from '../options.js';
import { streamingThresholds } from '../thresholds.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

// Custom trend for time-to-first-byte (k6's http_req_waiting is close enough
// when the body is consumed greedily; we tag it for the dashboard).
const ttft = new Trend('streaming_ttft_ms', true);

export const options = withBase({
  vus: 200,
  duration: '5m',
  thresholds: {
    ...streamingThresholds,
    streaming_ttft_ms: ['p(95)<200'], // NFR-003
  },
  tags: { scenario: 'streaming' },
});

export default function () {
  const res = http.post(
    `${BASE_URL}/api/v1/chat/completions`,
    streamingChatPayload('small'),
    {
      headers: authHeaders({ Accept: 'text/event-stream' }),
      tags: tagsFor('small'),
      // Tell k6 to keep the connection open until the server closes it.
      timeout: '30s',
    },
  );
  ttft.add(res.timings.waiting);
  checkStreamingResponse(res);
}
