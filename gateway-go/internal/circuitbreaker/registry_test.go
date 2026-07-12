package circuitbreaker

import (
	"errors"
	"sync"
	"testing"

	"github.com/sony/gobreaker"
)

func TestRegistry_ReturnsSameBreakerForSameKey(t *testing.T) {
	r := NewRegistry()
	a := r.For("openai", "gpt-4o")
	b := r.For("openai", "gpt-4o")
	if a != b {
		t.Error("expected same breaker pointer for repeated For() calls")
	}
}

func TestRegistry_DifferentKeysGetDifferentBreakers(t *testing.T) {
	r := NewRegistry()
	a := r.For("openai", "gpt-4o")
	b := r.For("openai", "gpt-3.5")
	c := r.For("anthropic", "gpt-4o") // different provider, same model name
	if a == b || a == c || b == c {
		t.Error("expected distinct breakers for distinct (provider, model) tuples")
	}
}

func TestRegistry_BreakerNameMatchesKey(t *testing.T) {
	r := NewRegistry()
	cb := r.For("anthropic", "claude-3-opus")
	if cb.Name() != "anthropic:claude-3-opus" {
		t.Errorf("breaker name = %q, want anthropic:claude-3-opus", cb.Name())
	}
}

func TestRegistry_TripsAfter5ConsecutiveFailures(t *testing.T) {
	r := NewRegistry()
	cb := r.For("openai", "gpt-4o")
	want := errors.New("upstream boom")

	for i := 0; i < 5; i++ {
		_, _ = cb.Execute(func() (any, error) { return nil, want })
	}

	// 6th call should be rejected immediately because the breaker is now open.
	_, err := cb.Execute(func() (any, error) { return "should not run", nil })
	if !errors.Is(err, gobreaker.ErrOpenState) {
		t.Errorf("expected ErrOpenState after 5 failures, got %v", err)
	}
}

func TestRegistry_ConcurrentForIsSafe(t *testing.T) {
	r := NewRegistry()
	const n = 100
	var wg sync.WaitGroup
	wg.Add(n)
	results := make([]*gobreaker.CircuitBreaker, n)
	for i := range results {
		go func(i int) {
			defer wg.Done()
			results[i] = r.For("openai", "gpt-4o")
		}(i)
	}
	wg.Wait()
	first := results[0]
	for i, got := range results {
		if got != first {
			t.Fatalf("breaker[%d] differs from breaker[0] — registry is racy", i)
		}
	}
}
