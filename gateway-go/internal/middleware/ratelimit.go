package middleware

import (
	"net/http"
	"strconv"
	"time"

	"github.com/openrouter/gateway-go/internal/ratelimit"
)

// RateLimit enforces per-key request and token limits using the supplied limiter.
// Implements DRD GW-014 + RL-001..RL-007.
//
// Headers added on every response (DRD RL-003):
//   X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
func RateLimit(limiter ratelimit.Limiter) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			ident := AuthIdentityFrom(r.Context())
			if ident.KeyID == "" {
				next.ServeHTTP(w, r)
				return
			}

			result, err := limiter.Check(r.Context(), ratelimit.Key{
				KeyID:             ident.KeyID,
				RequestsPerMinute: ident.RateLimit.RequestsPerMinute,
			})
			if err != nil {
				// Fail open on limiter errors but log + metric upstream.
				next.ServeHTTP(w, r)
				return
			}

			w.Header().Set("X-RateLimit-Limit", strconv.Itoa(int(result.Limit)))
			w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(int(result.Remaining)))
			w.Header().Set("X-RateLimit-Reset", strconv.FormatInt(result.ResetAt.Unix(), 10))

			if !result.Allowed {
				retryAfter := int(time.Until(result.ResetAt).Seconds())
				if retryAfter < 1 {
					retryAfter = 1
				}
				w.Header().Set("Retry-After", strconv.Itoa(retryAfter))
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusTooManyRequests)
				_, _ = w.Write([]byte(`{"error":{"message":"Rate limit exceeded","type":"rate_limit_error","code":"rate_limit_exceeded"}}`))
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}
