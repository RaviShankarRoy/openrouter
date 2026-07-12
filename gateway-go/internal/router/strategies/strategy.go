// Package strategies implements pluggable routing algorithms (DRD §9.1).
//
// Each strategy implements the Strategy interface. The router selects a
// strategy based on the API key's policy or per-request hint header.
package strategies

import (
	"context"

	"github.com/openrouter/gateway-go/internal/router"
)

// Strategy chooses the order in which targets should be tried.
type Strategy interface {
	Name() string
	Order(ctx context.Context, candidates []router.Target) []router.Target
}

// Registry holds all available strategies. Lookups are by name.
type Registry struct {
	m map[string]Strategy
}

func NewRegistry(strategies ...Strategy) *Registry {
	r := &Registry{m: make(map[string]Strategy, len(strategies))}
	for _, s := range strategies {
		r.m[s.Name()] = s
	}
	return r
}

func (r *Registry) Get(name string) (Strategy, bool) {
	s, ok := r.m[name]
	return s, ok
}
