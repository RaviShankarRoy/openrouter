// Smoke — 1 VU, 30 s. Run before every other test to confirm the stack is up.

import http from 'k6/http';
import { sleep } from 'k6';
import { authHeaders } from '../lib/auth.js';
import { chatPayload, tagsFor } from '../lib/payloads.js';
import { checkChatResponse } from '../lib/checks.js';
import { withBase } from '../options.js';
import { smokeThresholds } from '../thresholds.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = withBase({
  vus: 1,
  duration: '30s',
  thresholds: smokeThresholds,
  tags: { scenario: 'smoke' },
});

export default function () {
  const res = http.post(
    `${BASE_URL}/api/v1/chat/completions`,
    chatPayload('small'),
    { headers: authHeaders(), tags: tagsFor('small') },
  );
  checkChatResponse(res);
  sleep(1);
}
