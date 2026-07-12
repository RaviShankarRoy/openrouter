// Package proxy is the outbound side of the gateway: pick a provider, normalize
// the request, send it, normalize the response (or stream).
//
// Patterns:
//   Adapter — one ProviderAdapter per provider for request/response shape
//   Object Pool — sync.Pool of buffers to keep allocations off the hot path
//   Circuit Breaker — wraps every outbound call (composed at the call site)
package proxy

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"net/http"

	"github.com/openrouter/gateway-go/internal/circuitbreaker"
	"github.com/openrouter/gateway-go/internal/proxy/adapters"
	"github.com/openrouter/gateway-go/internal/router"
)

// Proxy runs the chain: select target → adapter normalize → send → adapter response.
type Proxy struct {
	router   *router.Router
	breakers *circuitbreaker.Registry
	logger   *slog.Logger
	clients  *clientPool          // HTTP clients per provider, keep-alive enabled
	adapters map[string]adapters.ProviderAdapter
}

// New wires a Proxy with the standard set of adapters.
//
// OpenAI-compatible providers (Together, Fireworks, Ollama, etc.) reuse the
// passthrough OpenAI adapter — only the base URL and key env differ, both of
// which come from providers.yaml at request time.
func New(r *router.Router, b *circuitbreaker.Registry, logger *slog.Logger) *Proxy {
	openAIAdapter := adapters.NewOpenAI()
	return &Proxy{
		router:   r,
		breakers: b,
		logger:   logger,
		clients:  newClientPool(r),
		adapters: map[string]adapters.ProviderAdapter{
			"openai":    openAIAdapter,
			"anthropic": adapters.NewAnthropic(),
			"google":    adapters.NewGoogle(),
			// OpenAI-compatible aggregators / self-host.
			"together":  openAIAdapter,
			"fireworks": openAIAdapter,
			"ollama":    openAIAdapter,
		},
	}
}

// ChatCompletion proxies an OpenAI-format chat completion request through
// the configured fallback chain. Returns the upstream response or 503 if
// every target failed.
func (p *Proxy) ChatCompletion(ctx context.Context, model string, body []byte, stream bool, w http.ResponseWriter) error {
	primary, fallback, ok := p.router.Resolve(model)
	if !ok {
		return fmt.Errorf("unknown model %q", model)
	}
	chain := append([]router.Target{primary}, fallback...)

	var lastErr error
	for _, t := range chain {
		adapter, ok := p.adapters[t.Provider]
		if !ok {
			lastErr = fmt.Errorf("no adapter for provider %q", t.Provider)
			continue
		}
		breaker := p.breakers.For(t.Provider, t.Model)
		_, err := breaker.Execute(func() (any, error) {
			return nil, p.send(ctx, t, adapter, body, stream, w)
		})
		if err == nil {
			return nil
		}
		lastErr = err
		p.logger.Warn("provider failed, trying fallback",
			"provider", t.Provider, "model", t.Model, "err", err)
	}
	return fmt.Errorf("all providers failed: %w", lastErr)
}

func (p *Proxy) send(
	ctx context.Context,
	target router.Target,
	adapter adapters.ProviderAdapter,
	body []byte,
	stream bool,
	w http.ResponseWriter,
) error {
	cfg, ok := p.router.Provider(target.Provider)
	if !ok {
		return fmt.Errorf("provider %q not configured", target.Provider)
	}
	upstream, err := adapter.NormalizeRequest(target.Model, body, cfg)
	if err != nil {
		return fmt.Errorf("normalize: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, cfg.BaseURL+upstream.Path, upstream.Body)
	if err != nil {
		return err
	}
	for k, v := range upstream.Headers {
		req.Header.Set(k, v)
	}
	resp, err := p.clients.For(target.Provider).Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 500 || resp.StatusCode == http.StatusTooManyRequests {
		return fmt.Errorf("provider returned %d", resp.StatusCode)
	}

	w.Header().Set("Content-Type", resp.Header.Get("Content-Type"))
	w.WriteHeader(resp.StatusCode)

	if stream {
		return p.streamResponse(adapter, resp.Body, w)
	}
	return p.bufferedResponse(adapter, resp.Body, w)
}

// streamResponse forwards an SSE stream from the upstream through the
// adapter's translator, flushing every translated event so clients see
// tokens with sub-50ms TTFT.
func (p *Proxy) streamResponse(adapter adapters.ProviderAdapter, src io.Reader, w http.ResponseWriter) error {
	flusher, _ := w.(http.Flusher)
	translator := adapter.NewStreamTranslator()
	buf := getBuffer()
	defer putBuffer(buf)
	for {
		n, rerr := src.Read(buf)
		if err := writeChunk(translator, buf[:n], w, flusher); err != nil {
			return err
		}
		if rerr == io.EOF {
			return finishStream(translator, w, flusher)
		}
		if rerr != nil {
			return rerr
		}
	}
}

func writeChunk(t adapters.StreamTranslator, chunk []byte, w io.Writer, flusher http.Flusher) error {
	if len(chunk) == 0 {
		return nil
	}
	if err := t.Translate(chunk, w); err != nil {
		return err
	}
	if flusher != nil {
		flusher.Flush()
	}
	return nil
}

func finishStream(t adapters.StreamTranslator, w io.Writer, flusher http.Flusher) error {
	if err := t.Close(w); err != nil {
		return err
	}
	if flusher != nil {
		flusher.Flush()
	}
	return nil
}

func (p *Proxy) bufferedResponse(adapter adapters.ProviderAdapter, src io.Reader, w http.ResponseWriter) error {
	full, err := io.ReadAll(src)
	if err != nil {
		return err
	}
	normalized, err := adapter.NormalizeResponse(full)
	if err != nil {
		return err
	}
	_, err = w.Write(normalized)
	return err
}
