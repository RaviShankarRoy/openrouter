package adapters

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/openrouter/gateway-go/internal/router"
)

// Anthropic adapts between OpenAI chat-completions format and Anthropic Messages API.
//
// This Go adapter handles the common case (text-only messages, tools).
// Edge cases (image/video content blocks, prompt caching headers) are handled
// by the richer Python adapter when the request includes them.
type Anthropic struct{}

func NewAnthropic() *Anthropic { return &Anthropic{} }

func (a *Anthropic) Name() string { return "anthropic" }

func (a *Anthropic) NormalizeRequest(model string, body []byte, cfg router.ProviderConfig) (UpstreamRequest, error) {
	var oaReq openAIChatRequest
	if err := json.Unmarshal(body, &oaReq); err != nil {
		return UpstreamRequest{}, fmt.Errorf("parse openai request: %w", err)
	}

	anthReq := anthropicMessagesRequest{
		Model:       stripProviderPrefix(model),
		MaxTokens:   defaultIfZero(oaReq.MaxTokens, 4096),
		Temperature: oaReq.Temperature,
		TopP:        oaReq.TopP,
		Stream:      oaReq.Stream,
	}
	for _, m := range oaReq.Messages {
		switch m.Role {
		case "system":
			anthReq.System = appendSystem(anthReq.System, m.Content)
		case "user", "assistant", "tool":
			anthReq.Messages = append(anthReq.Messages, anthropicMessage{
				Role:    m.Role,
				Content: m.Content,
			})
		}
	}
	out, err := json.Marshal(anthReq)
	if err != nil {
		return UpstreamRequest{}, err
	}

	headers := map[string]string{
		"Content-Type":      "application/json",
		"x-api-key":         os.Getenv(cfg.KeyEnv),
		"anthropic-version": "2023-06-01",
	}
	for k, v := range cfg.Headers {
		headers[k] = v
	}
	return UpstreamRequest{
		Path:    "/messages",
		Headers: headers,
		Body:    bytes.NewReader(out),
	}, nil
}

func (a *Anthropic) NormalizeResponse(body []byte) ([]byte, error) {
	var anthResp anthropicMessagesResponse
	if err := json.Unmarshal(body, &anthResp); err != nil {
		return nil, fmt.Errorf("parse anthropic response: %w", err)
	}
	oaResp := openAIChatResponse{
		ID:      anthResp.ID,
		Object:  "chat.completion",
		Created: anthResp.CreatedAt,
		Model:   anthResp.Model,
		Choices: []openAIChoice{{
			Index: 0,
			Message: openAIMessage{
				Role:    "assistant",
				Content: anthResp.contentText(),
			},
			FinishReason: mapAnthropicStopReason(anthResp.StopReason),
		}},
		Usage: openAIUsage{
			PromptTokens:     anthResp.Usage.InputTokens,
			CompletionTokens: anthResp.Usage.OutputTokens,
			TotalTokens:      anthResp.Usage.InputTokens + anthResp.Usage.OutputTokens,
		},
	}
	return json.Marshal(oaResp)
}

func (a *Anthropic) NewStreamTranslator() StreamTranslator {
	return &anthropicStreamTranslator{}
}

// anthropicStreamTranslator parses Anthropic's typed SSE stream and emits the
// flat OpenAI chat.completion.chunk format expected by SDKs. One per request.
//
// Anthropic event sequence (excerpted from their docs):
//
//	event: message_start
//	data: {"type":"message_start","message":{"id":"msg_01...","model":"claude-3-...","usage":{...}}}
//
//	event: content_block_start
//	data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
//
//	event: content_block_delta
//	data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}
//	... more deltas ...
//
//	event: content_block_stop
//	data: {"type":"content_block_stop","index":0}
//
//	event: message_delta
//	data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":42}}
//
//	event: message_stop
//	data: {"type":"message_stop"}
//
// We translate text_delta → openai delta.content, message_delta.stop_reason →
// finish_reason, and emit `data: [DONE]\n\n` on Close. Tool-use streaming and
// thinking blocks fall through (Phase 1 covers text only — DRD §6.1).
type anthropicStreamTranslator struct {
	// SSE parse state.
	lineBuf      bytes.Buffer // partial line carryover across Translate calls
	currentEvent string       // most recent `event:` value
	currentData  bytes.Buffer // accumulated `data:` payload for the current event

	// Translation state, populated from message_start.
	id      string
	model   string
	created int64

	// Lifecycle.
	roleEmitted bool // true after we send the initial `delta:{role:"assistant"}` chunk
	finished    bool // true after Close has run; subsequent calls are no-ops
}

const sseDataPrefix = "data: "

func (t *anthropicStreamTranslator) Translate(chunk []byte, w io.Writer) error {
	// Append and process by line — SSE is line-delimited (\n) with events
	// terminated by an empty line.
	t.lineBuf.Write(chunk)
	for {
		raw := t.lineBuf.Bytes()
		nl := bytes.IndexByte(raw, '\n')
		if nl < 0 {
			break // wait for more bytes
		}
		line := raw[:nl]
		t.lineBuf.Next(nl + 1)
		if len(line) > 0 && line[len(line)-1] == '\r' {
			line = line[:len(line)-1]
		}
		if len(line) == 0 {
			if err := t.dispatch(w); err != nil {
				return err
			}
			t.currentEvent = ""
			t.currentData.Reset()
			continue
		}
		t.consumeLine(line)
	}
	return nil
}

// consumeLine routes one non-blank SSE field line into translator state.
func (t *anthropicStreamTranslator) consumeLine(line []byte) {
	if name, ok := stripPrefix(line, "event:"); ok {
		t.currentEvent = string(bytes.TrimPrefix(name, []byte(" ")))
		return
	}
	if data, ok := stripPrefix(line, "data:"); ok {
		if t.currentData.Len() > 0 {
			t.currentData.WriteByte('\n')
		}
		t.currentData.Write(bytes.TrimPrefix(data, []byte(" ")))
		return
	}
	// `:` comments and unknown fields — ignore per SSE spec.
}

func stripPrefix(line []byte, prefix string) ([]byte, bool) {
	if bytes.HasPrefix(line, []byte(prefix)) {
		return line[len(prefix):], true
	}
	return nil, false
}

func (t *anthropicStreamTranslator) Close(w io.Writer) error {
	if t.finished {
		return nil
	}
	t.finished = true
	_, err := w.Write([]byte("data: [DONE]\n\n"))
	return err
}

// dispatch handles one fully-parsed Anthropic event.
func (t *anthropicStreamTranslator) dispatch(w io.Writer) error {
	if t.currentEvent == "" || t.currentData.Len() == 0 {
		return nil
	}
	switch t.currentEvent {
	case "message_start":
		return t.handleMessageStart(w)
	case "content_block_delta":
		return t.handleContentBlockDelta(w)
	case "message_delta":
		return t.handleMessageDelta(w)
	case "error":
		return t.writeChunk(w, openAIStreamDelta{}, "error")
	default:
		// "message_stop" / "content_block_start" / "content_block_stop" /
		// "ping" / unknown — no OpenAI equivalent.
		return nil
	}
}

func (t *anthropicStreamTranslator) handleMessageStart(w io.Writer) error {
	var ev anthropicEventMessageStart
	if err := json.Unmarshal(t.currentData.Bytes(), &ev); err != nil {
		return fmt.Errorf("anthropic message_start: %w", err)
	}
	t.id = ev.Message.ID
	t.model = ev.Message.Model
	t.created = time.Now().Unix()
	return t.writeChunk(w, openAIStreamDelta{Role: "assistant"}, "")
}

func (t *anthropicStreamTranslator) handleContentBlockDelta(w io.Writer) error {
	var ev anthropicEventContentBlockDelta
	if err := json.Unmarshal(t.currentData.Bytes(), &ev); err != nil {
		return fmt.Errorf("anthropic content_block_delta: %w", err)
	}
	if ev.Delta.Type != "text_delta" || ev.Delta.Text == "" {
		// Tool-use deltas (input_json_delta) are dropped here — Phase 2.
		return nil
	}
	return t.writeChunk(w, openAIStreamDelta{Content: ev.Delta.Text}, "")
}

func (t *anthropicStreamTranslator) handleMessageDelta(w io.Writer) error {
	var ev anthropicEventMessageDelta
	if err := json.Unmarshal(t.currentData.Bytes(), &ev); err != nil {
		return fmt.Errorf("anthropic message_delta: %w", err)
	}
	if ev.Delta.StopReason == "" {
		return nil
	}
	return t.writeChunk(w, openAIStreamDelta{}, mapAnthropicStopReason(ev.Delta.StopReason))
}

// writeChunk emits one `data: {...}\n\n` SSE event in OpenAI shape.
func (t *anthropicStreamTranslator) writeChunk(w io.Writer, delta openAIStreamDelta, finishReason string) error {
	chunk := openAIStreamChunk{
		ID:      t.id,
		Object:  "chat.completion.chunk",
		Created: t.created,
		Model:   t.model,
		Choices: []openAIStreamChoice{{
			Index: 0,
			Delta: delta,
		}},
	}
	if finishReason != "" {
		chunk.Choices[0].FinishReason = &finishReason
	}
	body, err := json.Marshal(chunk)
	if err != nil {
		return err
	}
	if _, err := w.Write([]byte(sseDataPrefix)); err != nil {
		return err
	}
	if _, err := w.Write(body); err != nil {
		return err
	}
	_, err = w.Write([]byte("\n\n"))
	if err == nil {
		t.roleEmitted = true
	}
	return err
}

// --- intermediate types ---

type openAIChatRequest struct {
	Model       string          `json:"model"`
	Messages    []openAIMessage `json:"messages"`
	MaxTokens   int             `json:"max_tokens,omitempty"`
	Temperature float64         `json:"temperature,omitempty"`
	TopP        float64         `json:"top_p,omitempty"`
	Stream      bool            `json:"stream,omitempty"`
}

type openAIMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type openAIChatResponse struct {
	ID      string         `json:"id"`
	Object  string         `json:"object"`
	Created int64          `json:"created"`
	Model   string         `json:"model"`
	Choices []openAIChoice `json:"choices"`
	Usage   openAIUsage    `json:"usage"`
}

type openAIChoice struct {
	Index        int           `json:"index"`
	Message      openAIMessage `json:"message"`
	FinishReason string        `json:"finish_reason"`
}

type openAIUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// openAIStreamChunk is one SSE event in OpenAI's chat.completion.chunk shape.
type openAIStreamChunk struct {
	ID      string               `json:"id"`
	Object  string               `json:"object"`
	Created int64                `json:"created"`
	Model   string               `json:"model"`
	Choices []openAIStreamChoice `json:"choices"`
}

type openAIStreamChoice struct {
	Index        int                `json:"index"`
	Delta        openAIStreamDelta  `json:"delta"`
	FinishReason *string            `json:"finish_reason"`
}

type openAIStreamDelta struct {
	Role    string `json:"role,omitempty"`
	Content string `json:"content,omitempty"`
}

type anthropicMessagesRequest struct {
	Model       string             `json:"model"`
	System      string             `json:"system,omitempty"`
	Messages    []anthropicMessage `json:"messages"`
	MaxTokens   int                `json:"max_tokens"`
	Temperature float64            `json:"temperature,omitempty"`
	TopP        float64            `json:"top_p,omitempty"`
	Stream      bool               `json:"stream,omitempty"`
}

type anthropicMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type anthropicMessagesResponse struct {
	ID         string                 `json:"id"`
	Type       string                 `json:"type"`
	Model      string                 `json:"model"`
	CreatedAt  int64                  `json:"created_at"`
	Content    []anthropicContentItem `json:"content"`
	StopReason string                 `json:"stop_reason"`
	Usage      anthropicUsage         `json:"usage"`
}

type anthropicContentItem struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

type anthropicUsage struct {
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

// Anthropic streaming event payloads — only the fields we read are modeled.

type anthropicEventMessageStart struct {
	Message struct {
		ID    string `json:"id"`
		Model string `json:"model"`
	} `json:"message"`
}

type anthropicEventContentBlockDelta struct {
	Index int `json:"index"`
	Delta struct {
		Type        string `json:"type"`
		Text        string `json:"text,omitempty"`
		PartialJSON string `json:"partial_json,omitempty"`
	} `json:"delta"`
}

type anthropicEventMessageDelta struct {
	Delta struct {
		StopReason string `json:"stop_reason"`
	} `json:"delta"`
}

func (a anthropicMessagesResponse) contentText() string {
	var b bytes.Buffer
	for _, c := range a.Content {
		if c.Type == "text" {
			b.WriteString(c.Text)
		}
	}
	return b.String()
}

func mapAnthropicStopReason(s string) string {
	switch s {
	case "end_turn":
		return "stop"
	case "max_tokens":
		return "length"
	case "tool_use":
		return "tool_calls"
	default:
		return "stop"
	}
}

func stripProviderPrefix(model string) string {
	for i, c := range model {
		if c == '/' {
			return model[i+1:]
		}
	}
	return model
}

func defaultIfZero(v, def int) int {
	if v == 0 {
		return def
	}
	return v
}

func appendSystem(existing, addition string) string {
	if existing == "" {
		return addition
	}
	return existing + "\n\n" + addition
}
