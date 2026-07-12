// Stress — ramp 0 -> 15K RPS over 10 min to find the breaking point.
// Thresholds are loose; we want to *learn* where it breaks, not stay green.

import http from 'k6/http';
import { authHeaders } from '../lib/auth.js';
import { chatPayload, tagsFor } from '../lib/payloads.js';
import { withBase } from '../options.js';
import { stressThresholds } from '../thresholds.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = withBase({
  scenarios: {
    ramp: {
      executor: 'ramping-arrival-rate',
      startRate: 100,
      timeUnit: '1s',
      preAllocatedVUs: 500,
      maxVUs: 2000,
      stages: [
        { duration: '2m', target: 5000 },
        { duration: '2m', target: 10000 },
        { duration: '3m', target: 15000 },
        { duration: '3m', target: 15000 }, // hold at peak
      ],
    },
  },
  thresholds: stressThresholds,
  tags: { scenario: 'stress' },
});

export default function () {
  http.post(`${BASE_URL}/api/v1/chat/completions`, chatPayload('small'), {
    headers: authHeaders(),
    tags: tagsFor('small'),
  });
}
