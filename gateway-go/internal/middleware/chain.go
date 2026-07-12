// Package middleware implements the chain-of-responsibility pattern for HTTP processing.
// Each middleware is an http.Handler decorator. Order is set by the server package.
package middleware

import (
	"context"
	"log/slog"
	"net/http"
	"runtime/debug"
	"time"

	"github.com/google/uuid"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
)

type ctxKey int

const (
	ctxKeyRequestID ctxKey = iota
	ctxKeyAuth
	ctxKeyStartTime
)

// RequestID assigns a UUID to every request. Read via RequestIDFrom(ctx).
func RequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := r.Header.Get("X-Request-ID")
		if id == "" {
			id = uuid.NewString()
		}
		w.Header().Set("X-Request-ID", id)
		ctx := context.WithValue(r.Context(), ctxKeyRequestID, id)
		ctx = context.WithValue(ctx, ctxKeyStartTime, time.Now())
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// RequestIDFrom returns the request ID assigned by the RequestID middleware.
func RequestIDFrom(ctx context.Context) string {
	if v, ok := ctx.Value(ctxKeyRequestID).(string); ok {
		return v
	}
	return ""
}

// Recoverer turns panics into 500s without crashing the worker.
func Recoverer(logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if rec := recover(); rec != nil {
					logger.Error("panic recovered",
						"err", rec,
						"stack", string(debug.Stack()),
						"request_id", RequestIDFrom(r.Context()),
					)
					http.Error(w, `{"error":{"message":"internal error","type":"server_error"}}`, http.StatusInternalServerError)
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}

// Logger emits a single line per completed request.
// Body is never logged here — that's an opt-in feature elsewhere (DRD OB-009).
func Logger(logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			rw := &statusRecorder{ResponseWriter: w, status: 200}
			start := time.Now()
			next.ServeHTTP(rw, r)
			logger.Info("http request",
				"method", r.Method,
				"path", r.URL.Path,
				"status", rw.status,
				"duration_ms", time.Since(start).Milliseconds(),
				"request_id", RequestIDFrom(r.Context()),
				"key_id", AuthIdentityFrom(r.Context()).KeyID,
			)
		})
	}
}

// Tracing wraps every request in an OTel span.
func Tracing(serviceName string) func(http.Handler) http.Handler {
	tracer := otel.Tracer(serviceName)
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			ctx, span := tracer.Start(r.Context(), r.Method+" "+r.URL.Path)
			defer span.End()
			span.SetAttributes(
				attribute.String("http.method", r.Method),
				attribute.String("http.path", r.URL.Path),
				attribute.String("request.id", RequestIDFrom(r.Context())),
			)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(code int) {
	s.status = code
	s.ResponseWriter.WriteHeader(code)
}
