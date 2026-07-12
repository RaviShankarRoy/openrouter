// Generates a fake bearer token. The Go gateway is configured (in test profile)
// to recognize `sk-or-v1-loadtest...` keys without hitting Postgres so we
// measure the proxy hot path, not the auth lookup.

const DEFAULT_KEY = 'sk-or-v1-loadtest0000000000000000000000000000000000000000000000000000';

export function bearerToken() {
  // __ENV is k6's env-variable map; fall back to the load-test default key.
  return `Bearer ${__ENV.API_TOKEN || DEFAULT_KEY}`;
}

export function authHeaders(extra = {}) {
  return {
    Authorization: bearerToken(),
    'Content-Type': 'application/json',
    ...extra,
  };
}
