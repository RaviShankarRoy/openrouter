// Package router resolves a logical model name to a concrete provider+endpoint
// and supplies a fallback chain.
//
// Pattern: Strategy — different routing strategies are interchangeable algorithms
// implementing the Strategy interface in internal/service/strategies.
//
// Tier: service. The shapes it reads and returns live in shared/model so the
// repository tier can use them without importing this package.
package router

import (
	"fmt"
	"os"
	"sync/atomic"

	"gopkg.in/yaml.v3"

	"github.com/openrouter/gateway-go/internal/shared/model"
)

// configFile is the wire format of providers.yaml.
type configFile struct {
	Providers map[string]model.ProviderConfig `yaml:"providers"`
	Models    []model.ModelEntry              `yaml:"models"`
}

// Router holds the parsed config and supports atomic hot-swap on SIGHUP.
type Router struct {
	state atomic.Pointer[state]
}

type state struct {
	providers map[string]model.ProviderConfig
	models    map[string]model.ModelEntry
}

// LoadFromFile parses providers.yaml and returns a Router.
func LoadFromFile(path string) (*Router, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	var f configFile
	if err := yaml.Unmarshal(data, &f); err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}
	st := &state{
		providers: f.Providers,
		models:    make(map[string]model.ModelEntry, len(f.Models)),
	}
	for _, m := range f.Models {
		st.models[m.ID] = m
	}
	r := &Router{}
	r.state.Store(st)
	return r, nil
}

// Resolve returns the primary target plus any fallback targets for the model.
func (r *Router) Resolve(name string) (primary model.Target, fallback []model.Target, ok bool) {
	st := r.state.Load()
	m, ok := st.models[name]
	if !ok {
		return model.Target{}, nil, false
	}
	return model.Target{Provider: m.Provider, Model: m.ID}, m.Fallback, true
}

// Provider returns the provider config for a name.
func (r *Router) Provider(name string) (model.ProviderConfig, bool) {
	st := r.state.Load()
	p, ok := st.providers[name]
	return p, ok
}

// Swap atomically replaces config with a freshly loaded Router (DRD GW-015).
func (r *Router) Swap(other *Router) {
	r.state.Store(other.state.Load())
}
