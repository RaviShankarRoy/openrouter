// Common k6 checks. Centralized so a change to OpenAI's response shape only
// needs editing in one place.

import { check } from 'k6';

export function checkChatResponse(res) {
  return check(res, {
    'status is 200': (r) => r.status === 200,
    'has choices array': (r) => {
      try {
        return Array.isArray(r.json('choices'));
      } catch {
        return false;
      }
    },
    'has usage block': (r) => {
      try {
        return typeof r.json('usage.total_tokens') === 'number';
      } catch {
        return false;
      }
    },
  });
}

export function checkStreamingResponse(res) {
  return check(res, {
    'status is 200': (r) => r.status === 200,
    'is event-stream': (r) => (r.headers['Content-Type'] || '').includes('event-stream'),
    'terminates with [DONE]': (r) => (r.body || '').includes('[DONE]'),
  });
}

export function checkRateLimitHeaders(res) {
  // RL-003 — every response must carry rate-limit headers.
  return check(res, {
    'X-RateLimit-Limit present': (r) => !!r.headers['X-Ratelimit-Limit'],
    'X-RateLimit-Remaining present': (r) => !!r.headers['X-Ratelimit-Remaining'],
  });
}
