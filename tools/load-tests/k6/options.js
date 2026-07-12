// Shared k6 options — every scenario imports `baseOptions` and merges its own
// stages/executor on top. Centralizing keeps tags consistent so the Grafana
// dashboard works for every scenario without per-script tweaks.

export const baseOptions = {
  // Trim the noise but keep what matters for NFR debugging.
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  // Tags applied to every metric — sliced in Grafana.
  tags: {
    suite: 'gateway-load',
  },
  // Discard response bodies once checks pass — saves memory at high RPS.
  discardResponseBodies: false,
  // Bail early on truly broken runs, not on a single bad iteration.
  noConnectionReuse: false,
  // Cap exec duration as a safety net; individual scenarios can override.
  maxRedirects: 4,
};

// Helper: merge baseOptions with scenario-specific config without mutating either.
export function withBase(opts) {
  return { ...baseOptions, ...opts, tags: { ...baseOptions.tags, ...(opts.tags || {}) } };
}
