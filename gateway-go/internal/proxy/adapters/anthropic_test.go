package adapters

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// fullAnthropicStream is a representative Anthropic SSE stream covering the
// full lifecycle: start, two text deltas, message_delta with stop_reason,
// message_stop. Newlines are CRLF in some real responses; we use \n here.
const fullAnthropicStream = `event: message_start
data: {"type":"message_start","message":{"id":"msg_01abc","model":"claude-3-opus-20240229"}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" world"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":2}}

event: message_stop
data: {"type":"message_stop"}

`

// parseSSEChunks extracts each `data: ...` JSON payload (excluding [DONE]).
func parseSSEChunks(t *testing.T, raw string) []map[string]any {
	t.Helper()
	var out []map[string]any
	for _, evt := range strings.Split(raw, "\n\n") {
		evt = strings.TrimSpace(evt)
		if evt == "" || evt == "data: [DONE]" {
			continue
		}
		const prefix = "data: "
		i := strings.Index(evt, prefix)
		if i < 0 {
			continue
		}
		payload := evt[i+len(prefix):]
		var m map[string]any
		if err := json.Unmarshal([]byte(payload), &m); err != nil {
			t.Fatalf("decode chunk %q: %v", payload, err)
		}
		out = append(out, m)
	}
	return out
}

func TestAnthropicStream_TranslatesFullLifecycle(t *testing.T) {
	a := NewAnthropic()
	tr := a.NewStreamTranslator()

	var out bytes.Buffer
	if err := tr.Translate([]byte(fullAnthropicStream), &out); err != nil {
		t.Fatalf("Translate: %v", err)
	}
	if err := tr.Close(&out); err != nil {
		t.Fatalf("Close: %v", err)
	}

	got := out.String()
	if !strings.HasSuffix(got, "data: [DONE]\n\n") {
		t.Fatalf("expected stream to end with [DONE]:\n%s", got)
	}

	chunks := parseSSEChunks(t, got)
	if len(chunks) < 4 {
		t.Fatalf("expected at least 4 OpenAI chunks (role, hello, world, finish), got %d:\n%v", len(chunks), chunks)
	}

	// First chunk: role=assistant.
	first := chunks[0]
	if obj := first["object"]; obj != "chat.completion.chunk" {
		t.Errorf("first chunk object = %v, want chat.completion.chunk", obj)
	}
	if id := first["id"]; id != "msg_01abc" {
		t.Errorf("first chunk id = %v, want msg_01abc", id)
	}
	delta := firstDelta(t, first)
	if delta["role"] != "assistant" {
		t.Errorf("first chunk delta.role = %v, want assistant", delta["role"])
	}

	// Concatenated content from text_delta events.
	var content strings.Builder
	for _, c := range chunks[1:] {
		if d := firstDelta(t, c); d != nil {
			if s, ok := d["content"].(string); ok {
				content.WriteString(s)
			}
		}
	}
	if got := content.String(); got != "Hello world" {
		t.Errorf("concatenated content = %q, want %q", got, "Hello world")
	}

	// Final chunk: finish_reason="stop".
	last := chunks[len(chunks)-1]
	if reason := firstChoice(t, last)["finish_reason"]; reason != "stop" {
		t.Errorf("last chunk finish_reason = %v, want stop", reason)
	}
}

func TestAnthropicStream_HandlesSplitChunks(t *testing.T) {
	a := NewAnthropic()
	tr := a.NewStreamTranslator()

	// Feed the stream byte-by-byte. The translator must buffer partial lines.
	var out bytes.Buffer
	for i := 0; i < len(fullAnthropicStream); i++ {
		if err := tr.Translate([]byte(fullAnthropicStream[i:i+1]), &out); err != nil {
			t.Fatalf("Translate at %d: %v", i, err)
		}
	}
	if err := tr.Close(&out); err != nil {
		t.Fatalf("Close: %v", err)
	}

	chunks := parseSSEChunks(t, out.String())
	var content strings.Builder
	for _, c := range chunks[1:] {
		if d := firstDelta(t, c); d != nil {
			if s, ok := d["content"].(string); ok {
				content.WriteString(s)
			}
		}
	}
	if got := content.String(); got != "Hello world" {
		t.Errorf("byte-by-byte content = %q, want %q", got, "Hello world")
	}
}

func TestAnthropicStream_DropsToolUseAndEmptyDeltas(t *testing.T) {
	a := NewAnthropic()
	tr := a.NewStreamTranslator()
	stream := `event: message_start
data: {"type":"message_start","message":{"id":"m","model":"claude"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{}"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"ok"}}

`
	var out bytes.Buffer
	if err := tr.Translate([]byte(stream), &out); err != nil {
		t.Fatalf("Translate: %v", err)
	}
	chunks := parseSSEChunks(t, out.String())
	// Expect: 1 role chunk + 1 content chunk = 2.
	if len(chunks) != 2 {
		t.Fatalf("want 2 chunks (role + 'ok'), got %d:\n%v", len(chunks), chunks)
	}
	if d := firstDelta(t, chunks[1]); d["content"] != "ok" {
		t.Errorf("expected 'ok' content, got %v", d["content"])
	}
}

func TestAnthropicStream_CloseIsIdempotent(t *testing.T) {
	tr := NewAnthropic().NewStreamTranslator()
	var out bytes.Buffer
	if err := tr.Close(&out); err != nil {
		t.Fatal(err)
	}
	first := out.String()
	if err := tr.Close(&out); err != nil {
		t.Fatal(err)
	}
	if out.String() != first {
		t.Errorf("Close not idempotent: %q vs %q", first, out.String())
	}
}

func TestPassthroughTranslator_ForwardsVerbatim(t *testing.T) {
	tr := NewPassthroughTranslator()
	var out bytes.Buffer
	in := []byte("data: {\"hello\":\"world\"}\n\n")
	if err := tr.Translate(in, &out); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(out.Bytes(), in) {
		t.Errorf("got %q, want %q", out.Bytes(), in)
	}
	if err := tr.Close(&out); err != nil {
		t.Fatal(err)
	}
	// Close on passthrough is a no-op.
	if !bytes.Equal(out.Bytes(), in) {
		t.Errorf("Close added bytes: %q", out.Bytes())
	}
}

// helpers

func firstDelta(t *testing.T, chunk map[string]any) map[string]any {
	t.Helper()
	choices, _ := chunk["choices"].([]any)
	if len(choices) == 0 {
		return nil
	}
	first, _ := choices[0].(map[string]any)
	delta, _ := first["delta"].(map[string]any)
	return delta
}

func firstChoice(t *testing.T, chunk map[string]any) map[string]any {
	t.Helper()
	choices, _ := chunk["choices"].([]any)
	if len(choices) == 0 {
		return nil
	}
	c, _ := choices[0].(map[string]any)
	return c
}
