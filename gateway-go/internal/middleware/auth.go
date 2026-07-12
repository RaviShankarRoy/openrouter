package middleware

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"strings"

	"github.com/openrouter/gateway-go/internal/auth"
)

// Identity is what the auth middleware deposits into context.
type Identity struct {
	KeyID         string
	OrgID         string
	UserID        string
	AllowedModels []string
	DeniedModels  []string
	RateLimit     auth.RateLimitPolicy
	Budget        auth.BudgetPolicy
}

// Auth validates the Bearer token against the in-process LRU,
// falling back to Redis, falling back to the backend gRPC service.
// Implements DRD GW-013 (auth via Redis lookup).
func Auth(cache *auth.Cache) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			tok, ok := bearerToken(r)
			if !ok {
				writeAuthError(w, "missing_api_key", "Missing Authorization: Bearer header")
				return
			}
			hash := sha256Hex(tok)

			meta, err := cache.Get(r.Context(), hash)
			if err != nil {
				writeAuthError(w, "auth_unavailable", "Authentication service unavailable")
				return
			}
			if !meta.Valid {
				writeAuthError(w, "invalid_api_key", "Invalid or revoked API key")
				return
			}

			ident := Identity{
				KeyID:         meta.KeyID,
				OrgID:         meta.OrgID,
				UserID:        meta.UserID,
				AllowedModels: meta.AllowedModels,
				DeniedModels:  meta.DeniedModels,
				RateLimit:     meta.RateLimit,
				Budget:        meta.Budget,
			}
			ctx := context.WithValue(r.Context(), ctxKeyAuth, ident)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// AuthIdentityFrom returns the identity attached by Auth middleware.
// Returns zero value if no auth was performed.
func AuthIdentityFrom(ctx context.Context) Identity {
	if v, ok := ctx.Value(ctxKeyAuth).(Identity); ok {
		return v
	}
	return Identity{}
}

func bearerToken(r *http.Request) (string, bool) {
	h := r.Header.Get("Authorization")
	const prefix = "Bearer "
	if !strings.HasPrefix(h, prefix) {
		return "", false
	}
	return strings.TrimSpace(h[len(prefix):]), true
}

func sha256Hex(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

func writeAuthError(w http.ResponseWriter, code, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusUnauthorized)
	_, _ = w.Write([]byte(`{"error":{"message":"` + msg + `","type":"authentication_error","code":"` + code + `"}}`))
}
