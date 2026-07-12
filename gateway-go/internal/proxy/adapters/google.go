package adapters

import (
	"bytes"

	"github.com/openrouter/gateway-go/internal/router"
)

// Google adapter — stub for Phase 1. Full Gemini translation lives in the
// Python adapter; this Go stub forwards everything verbatim and lets the
// Python backend handle Gemini-specific request shapes when needed.
type Google struct{}

func NewGoogle() *Google { return &Google{} }

func (g *Google) Name() string { return "google" }

func (g *Google) NormalizeRequest(model string, body []byte, cfg router.ProviderConfig) (UpstreamRequest, error) {
	// TODO(phase 3): implement OpenAI → Gemini Generative Language API translation.
	// Until then we return an error so traffic to "google" is forced through Python.
	return UpstreamRequest{
		Path:    "/models/" + stripProviderPrefix(model) + ":generateContent",
		Headers: map[string]string{"Content-Type": "application/json"},
		Body:    bytes.NewReader(body),
	}, nil
}

func (g *Google) NormalizeResponse(body []byte) ([]byte, error) {
	return body, nil
}

func (g *Google) NewStreamTranslator() StreamTranslator {
	// TODO(phase 3): translate Gemini SSE → OpenAI SSE. For now, passthrough
	// matches the existing TODO on NormalizeRequest — Gemini-shaped requests
	// are pushed through Python until the Go translator is written.
	return NewPassthroughTranslator()
}
