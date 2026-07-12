// Package handlers contains thin HTTP adapters. They parse, validate, and
// delegate to use cases — no business logic lives here.
package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"time"

	"github.com/openrouter/gateway-go/internal/cache"
	"github.com/openrouter/gateway-go/internal/proxy"
)

// DependencyChecks maps dependency name → ping function for /ready.
type DependencyChecks map[string]func(context.Context) error

// --- /health (always 200, never blocks) ---

func Health(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"status":    "healthy",
		"timestamp": time.Now().UTC(),
	})
}

// --- /ready (checks dependencies, may return 503) ---

func Ready(checks DependencyChecks) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		results := make(map[string]any, len(checks))
		ready := true
		for name, ping := range checks {
			if err := ping(ctx); err != nil {
				results[name] = map[string]string{"status": "down", "error": err.Error()}
				ready = false
			} else {
				results[name] = map[string]string{"status": "up"}
			}
		}
		w.Header().Set("Content-Type", "application/json")
		if !ready {
			w.WriteHeader(http.StatusServiceUnavailable)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"status":       statusFor(ready),
			"dependencies": results,
		})
	}
}

func statusFor(ok bool) string {
	if ok {
		return "healthy"
	}
	return "unhealthy"
}

// --- /chat/completions ---

type ChatHandler struct {
	proxy *proxy.Proxy
	cache cache.ExactCache
}

func NewChatHandler(p *proxy.Proxy, c cache.ExactCache) *ChatHandler {
	return &ChatHandler{proxy: p, cache: c}
}

type chatRequest struct {
	Model  string `json:"model"`
	Stream bool   `json:"stream"`
}

func (h *ChatHandler) Create(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, 10<<20)) // 10MB cap
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request", err.Error())
		return
	}
	var req chatRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request", "malformed JSON: "+err.Error())
		return
	}
	if req.Model == "" {
		writeError(w, http.StatusBadRequest, "invalid_request", "model is required")
		return
	}

	// L1 exact-match cache lookup (DRD CA-001) — only for non-streaming requests.
	noCache := r.Header.Get("X-No-Cache") == "true"
	if !req.Stream && !noCache {
		key := cache.HashRequest(req.Model, body)
		if entry, hit, err := h.cache.Get(r.Context(), key); err == nil && hit {
			w.Header().Set("X-Cache", "HIT")
			w.Header().Set("Content-Type", entry.ContentType)
			w.WriteHeader(entry.Status)
			_, _ = w.Write(entry.Body)
			return
		}
	}

	if req.Stream {
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")
	}

	if err := h.proxy.ChatCompletion(r.Context(), req.Model, body, req.Stream, w); err != nil {
		if errors.Is(err, context.Canceled) {
			return // client disconnected
		}
		writeError(w, http.StatusServiceUnavailable, "providers_unavailable", err.Error())
		return
	}
	// TODO: write to cache asynchronously for non-stream success paths.
}

func writeError(w http.ResponseWriter, status int, code, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"error": map[string]string{
			"message": msg,
			"type":    code,
			"code":    code,
		},
	})
}
