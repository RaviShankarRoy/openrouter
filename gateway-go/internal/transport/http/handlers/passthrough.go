package handlers

import (
	"encoding/json"
	"io"
	"net/http"

	"github.com/openrouter/gateway-go/internal/proxy"
)

// Phase 1 stubs: embeddings, images, audio, rerank are simple proxies.
// They share the same shape and could be one handler — kept separate so
// per-endpoint metrics, validation, and SLOs are explicit.

type EmbeddingsHandler struct{ proxy *proxy.Proxy }

func NewEmbeddingsHandler(p *proxy.Proxy) *EmbeddingsHandler { return &EmbeddingsHandler{proxy: p} }
func (h *EmbeddingsHandler) Create(w http.ResponseWriter, r *http.Request) {
	proxyTo(h.proxy, w, r, "/embeddings")
}

type ImagesHandler struct{ proxy *proxy.Proxy }

func NewImagesHandler(p *proxy.Proxy) *ImagesHandler { return &ImagesHandler{proxy: p} }
func (h *ImagesHandler) Create(w http.ResponseWriter, r *http.Request) {
	proxyTo(h.proxy, w, r, "/images/generations")
}

type AudioHandler struct{ proxy *proxy.Proxy }

func NewAudioHandler(p *proxy.Proxy) *AudioHandler { return &AudioHandler{proxy: p} }
func (h *AudioHandler) Transcribe(w http.ResponseWriter, r *http.Request) {
	proxyTo(h.proxy, w, r, "/audio/transcriptions")
}

type RerankHandler struct{ proxy *proxy.Proxy }

func NewRerankHandler(p *proxy.Proxy) *RerankHandler { return &RerankHandler{proxy: p} }
func (h *RerankHandler) Create(w http.ResponseWriter, r *http.Request) {
	proxyTo(h.proxy, w, r, "/rerank")
}

// proxyTo extracts the model from the JSON body and forwards through Proxy.
// All non-chat endpoints share this shape because OpenAI's spec puts `model`
// in the request body for every modality.
func proxyTo(p *proxy.Proxy, w http.ResponseWriter, r *http.Request, _ string) {
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, 50<<20))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request", err.Error())
		return
	}
	var meta struct {
		Model string `json:"model"`
	}
	if err := json.Unmarshal(body, &meta); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request", err.Error())
		return
	}
	if err := p.ChatCompletion(r.Context(), meta.Model, body, false, w); err != nil {
		writeError(w, http.StatusServiceUnavailable, "providers_unavailable", err.Error())
	}
}

// --- Backend-delegated endpoints (videos, models catalog) ---

type VideoHandler struct{ backendAddr string }

func NewVideoHandler(addr string) *VideoHandler              { return &VideoHandler{backendAddr: addr} }
func (h *VideoHandler) Submit(w http.ResponseWriter, r *http.Request)  { backendDelegate(w, r) }
func (h *VideoHandler) Status(w http.ResponseWriter, r *http.Request)  { backendDelegate(w, r) }
func (h *VideoHandler) Content(w http.ResponseWriter, r *http.Request) { backendDelegate(w, r) }

type ModelsHandler struct{ backendAddr string }

func NewModelsHandler(addr string) *ModelsHandler { return &ModelsHandler{backendAddr: addr} }
func (h *ModelsHandler) List(w http.ResponseWriter, r *http.Request) {
	backendDelegate(w, r)
}

// backendDelegate is a stub for Phase 1 — production uses gRPC.
func backendDelegate(w http.ResponseWriter, _ *http.Request) {
	writeError(w, http.StatusNotImplemented, "not_implemented", "backend delegation pending")
}
