// Sustained 5 K RPS for 5 min — the primary NFR-005 baseline test.
//
// Uses k6's constant-arrival-rate executor so the rate stays flat even when
// individual responses vary. preAllocatedVUs sized for ~1ms gateway latency
// at 5K RPS; tune up if the gateway is slower than expected.

import http from 'k6/http';
import { authHeaders } from '../lib/auth.js';
import { chatPayload, tagsFor } from '../lib/payloads.js';
import { checkChatResponse } from '../lib/checks.js';
import { withBase } from '../options.js';
import { sustainedLoadThresholds } from '../thresholds.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = withBase({
  scenarios: {
    sustained: {
      executor: 'constant-arrival-rate',
      rate: 5000,
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 200,
      maxVUs: 500,
    },
  },
  thresholds: sustainedLoadThresholds,
  tags: { scenario: 'load' },
});

export default function () {
  // Mix payload sizes so the pool/buffer reuse paths are exercised.
  const size = Math.random() < 0.7 ? 'small' : Math.random() < 0.9 ? 'medium' : 'large';
  const res = http.post(
    `${BASE_URL}/api/v1/chat/completions`,
    chatPayload(size),
    { headers: authHeaders(), tags: tagsFor(size) },
  );
  checkChatResponse(res);
}
