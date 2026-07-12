// Soak — 2K RPS for 1 hour. Looking for memory leaks, FD exhaustion, slow
// pool growth. Run nightly in CI; failures here usually mean a goroutine or
// connection-pool leak in the gateway.

import http from 'k6/http';
import { authHeaders } from '../lib/auth.js';
import { chatPayload, tagsFor } from '../lib/payloads.js';
import { checkChatResponse } from '../lib/checks.js';
import { withBase } from '../options.js';
import { soakThresholds } from '../thresholds.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = withBase({
  scenarios: {
    soak: {
      executor: 'constant-arrival-rate',
      rate: 2000,
      timeUnit: '1s',
      duration: '1h',
      preAllocatedVUs: 100,
      maxVUs: 300,
    },
  },
  thresholds: soakThresholds,
  tags: { scenario: 'soak' },
});

export default function () {
  const res = http.post(`${BASE_URL}/api/v1/chat/completions`, chatPayload('small'), {
    headers: authHeaders(),
    tags: tagsFor('small'),
  });
  checkChatResponse(res);
}
