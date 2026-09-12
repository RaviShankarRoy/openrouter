// Package circuitbreaker wraps sony/gobreaker with a per-provider registry.
// One breaker per (provider, model) tuple — failures on one model don't trip
// other models on the same provider.
package circuitbreaker

import (
	"sync"
	"time"

	"github.com/sony/gobreaker"
)

// Registry is a concurrent-safe map of breakers keyed by provider+model.
type Registry struct {
	mu       sync.RWMutex
	breakers map[string]*gobreaker.CircuitBreaker
	settings gobreaker.Settings
}

// NewRegistry returns a registry with sensible defaults.
// Override per-provider settings via WithSettings.
func NewRegistry() *Registry {
	return &Registry{
		breakers: make(map[string]*gobreaker.CircuitBreaker),
		settings: gobreaker.Settings{
			MaxRequests: 3,                // half-open probe count
			Interval:    60 * time.Second, // counters reset
			Timeout:     30 * time.Second, // open → half-open
			ReadyToTrip: func(c gobreaker.Counts) bool {
				return c.ConsecutiveFailures >= 5
			},
		},
	}
}

// For returns (or creates) the breaker for the given provider+model.
func (r *Registry) For(provider, model string) *gobreaker.CircuitBreaker {
	key := provider + ":" + model
	r.mu.RLock()
	cb, ok := r.breakers[key]
	r.mu.RUnlock()
	if ok {
		return cb
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	// Double-check after acquiring write lock.
	if cb, ok := r.breakers[key]; ok {
		return cb
	}
	settings := r.settings
	settings.Name = key
	cb = gobreaker.NewCircuitBreaker(settings)
	r.breakers[key] = cb
	return cb
}
