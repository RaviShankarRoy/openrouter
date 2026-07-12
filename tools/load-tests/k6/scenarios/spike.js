// Spike — 0 -> 10K -> 0 in 60 s. Proves HPA + circuit breaker behave when
// traffic arrives all at once (real-world: a viral tweet).

import http from 'k6/http';
import { authHeaders } from '../lib/auth.js';
import { chatPayload, tagsFor } from '../lib/payloads.js';
import { withBase } from '../options.js';
import { spikeThresholds } from '../thresholds.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = withBase({
  scenarios: {
    spike: {
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 1000,
      maxVUs: 2000,
      stages: [
        { duration: '10s', target: 10000 }, // surge up
        { duration: '20s', target: 10000 }, // hold
        { duration: '10s', target: 0 },     // crash down
        { duration: '20s', target: 0 },     // recover
      ],
    },
  },
  thresholds: spikeThresholds,
  tags: { scenario: 'spike' },
});

export default function () {
  http.post(`${BASE_URL}/api/v1/chat/completions`, chatPayload('small'), {
    headers: authHeaders(),
    tags: tagsFor('small'),
  });
}
