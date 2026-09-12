package adapters

import (
	"bytes"
	"os"

	"github.com/openrouter/gateway-go/internal/shared/model"
)

// OpenAI is a passthrough adapter — the canonical format IS OpenAI.
type OpenAI struct{}

func NewOpenAI() *OpenAI { return &OpenAI{} }

func (o *OpenAI) Name() string { return "openai" }

func (o *OpenAI) NormalizeRequest(modelID string, body []byte, cfg model.ProviderConfig) (UpstreamRequest, error) {
	headers := map[string]string{
		"Content-Type":  "application/json",
		"Authorization": "Bearer " + os.Getenv(cfg.KeyEnv),
	}
	for k, v := range cfg.Headers {
		headers[k] = v
	}
	return UpstreamRequest{
		Path:    "/chat/completions",
		Headers: headers,
		Body:    bytes.NewReader(body),
	}, nil
}

func (o *OpenAI) NormalizeResponse(body []byte) ([]byte, error) {
	return body, nil // already OpenAI format
}

func (o *OpenAI) NewStreamTranslator() StreamTranslator {
	return NewPassthroughTranslator() // already OpenAI SSE format
}
