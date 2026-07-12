// Threshold definitions — each maps to an NFR ID so a failure tells you what
// was promised, not just what broke. A threshold failure makes the run exit
// non-zero, which is what we want as a CI quality gate.

// NFR-005 — 10K+ RPS sustained, 0% errors.
export const sustainedLoadThresholds = {
  http_req_failed: ['rate<0.001'],                     // <0.1% errors
  http_req_duration: ['p(99)<500', 'p(95)<200'],       // total RTT including mock provider
  // Gateway-only timing isolated by the `kind:gateway` tag in payloads.js.
  'http_req_duration{kind:gateway}': ['p(99)<5'],      // 5 ms slack over 15µs target on real iron
  iterations: ['rate>=4500'],                          // close to 5K iter/s for `load.js`
};

// NFR-002 — Microsecond gateway overhead. We can only assert millisecond
// resolution from k6 (network noise dominates), so we check the proxy adds no
// measurable overhead vs the mock baseline.
export const microLatencyThresholds = {
  'http_req_duration{kind:gateway}': ['p(99)<10'],
};

// NFR-003 — TTFT for streaming.
export const streamingThresholds = {
  http_req_duration: ['p(95)<200'],                    // first byte
  iteration_duration: ['p(95)<3000'],                  // full stream under 3s
};

// Smoke — anything failing means the local stack isn't usable.
export const smokeThresholds = {
  http_req_failed: ['rate<0.01'],
  http_req_duration: ['p(95)<1000'],
};

// Stress — looser; we want to *find* the breaking point, not pass cleanly.
export const stressThresholds = {
  http_req_failed: ['rate<0.05'],
  http_req_duration: ['p(99)<2000'],
};

// Spike — survival, not perfection.
export const spikeThresholds = {
  http_req_failed: ['rate<0.02'],
  http_req_duration: ['p(99)<1500'],
};

// Soak — memory/connection leaks would manifest as slow degradation; the
// thresholds match `load.js` so we know nothing gets worse over an hour.
export const soakThresholds = {
  http_req_failed: ['rate<0.001'],
  http_req_duration: ['p(99)<500'],
};
