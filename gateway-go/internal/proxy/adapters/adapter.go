// Package adapters implements the Provider Adapter pattern.
//
// Each adapter translates between the canonical OpenAI-compatible request/
// response shape and a provider's native format. Adapters in Go cover the
// hot-path "easy" providers (OpenAI-compatible). Complex providers remain
// in the Python backend (DRD §4.5).
package adapters

import (
	"io"

	"github.com/openrouter/gateway-go/internal/router"
)

// UpstreamRequest is what the proxy sends to the provider's REST API.
type UpstreamRequest struct {
	Path    string            // appended to provider's BaseURL
	Headers map[string]string // includes Authorization
	Body    io.Reader
}

// ProviderAdapter is the contract every provider implementation satisfies.
type ProviderAdapter interface {
	Name() string
	NormalizeRequest(model string, body []byte, cfg router.ProviderConfig) (UpstreamRequest, error)
	NormalizeResponse(body []byte) ([]byte, error)
	// NewStreamTranslator returns a new translator for one streaming request.
	// Each translator carries per-request state (message id, partial-line
	// buffer, etc.) and must not be shared across requests.
	NewStreamTranslator() StreamTranslator
}

// StreamTranslator converts upstream SSE bytes into the canonical OpenAI SSE
// format. One instance per HTTP request. The proxy calls Translate for every
// chunk read from the upstream, then Close exactly once when the upstream EOFs.
type StreamTranslator interface {
	// Translate writes 0+ complete OpenAI-format SSE events derived from the
	// supplied chunk. Partial events are buffered internally.
	Translate(chunk []byte, w io.Writer) error
	// Close writes any final markers (typically `data: [DONE]\n\n`) and
	// flushes buffered state. Idempotent on repeat calls.
	Close(w io.Writer) error
}

// passthroughTranslator forwards chunks verbatim. Suitable for providers that
// already emit the OpenAI SSE format (OpenAI itself, OpenAI-compatible
// aggregators, and the Python backend's preformatted streams).
type passthroughTranslator struct{}

// NewPassthroughTranslator returns a translator that copies upstream bytes
// directly to the writer. Adapters whose providers natively speak the OpenAI
// SSE protocol should return one of these from NewStreamTranslator.
func NewPassthroughTranslator() StreamTranslator { return passthroughTranslator{} }

func (passthroughTranslator) Translate(chunk []byte, w io.Writer) error {
	_, err := w.Write(chunk)
	return err
}

func (passthroughTranslator) Close(io.Writer) error { return nil }
