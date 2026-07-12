// Package router resolves a logical model name to a concrete provider+endpoint
// and supplies a fallback chain.
//
// Pattern: Strategy — different routing strategies are interchangeable algorithms
// implementing the Strategy interface in internal/router/strategies.
package router

import (
	"fmt"
	"os"
	"sync/atomic"

	"gopkg.in/yaml.v3"
)

// Target is one provider endpoint capable of serving a model.
type Target struct {
	Provider string
	Model    string
}

// ModelEntry binds a logical model id to its primary + fallback chain.
type ModelEntry struct {
	ID       string   `yaml:"id"`
	Provider string   `yaml:"provider"`
	Fallback []Target `yaml:"fallback"`
}

// ProviderConfig is the runtime configuration for one provider.
type ProviderConfig struct {
	BaseURL         string            `yaml:"base_url"`
	KeyEnv          string            `yaml:"key_env"`
	TimeoutSeconds  int               `yaml:"timeout_seconds"`
	MaxIdleConns    int               `yaml:"max_idle_conns"`
	MaxConnsPerHost int               `yaml:"max_conns_per_host"`
	Headers         map[string]string `yaml:"headers"`
}

// configFile is the wire format of providers.yaml.
type configFile struct {
	Providers map[string]ProviderConfig `yaml:"providers"`
	Models    []ModelEntry              `yaml:"models"`
}

// Router holds the parsed config and supports atomic hot-swap on SIGHUP.
type Router struct {
	state atomic.Pointer[state]
}

type state struct {
	providers map[string]ProviderConfig
	models    map[string]ModelEntry
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
		models:    make(map[string]ModelEntry, len(f.Models)),
	}
	for _, m := range f.Models {
		st.models[m.ID] = m
	}
	r := &Router{}
	r.state.Store(st)
	return r, nil
}

// Resolve returns the primary target plus any fallback targets for the model.
func (r *Router) Resolve(model string) (primary Target, fallback []Target, ok bool) {
	st := r.state.Load()
	m, ok := st.models[model]
	if !ok {
		return Target{}, nil, false
	}
	return Target{Provider: m.Provider, Model: m.ID}, m.Fallback, true
}

// Provider returns the provider config for a name.
func (r *Router) Provider(name string) (ProviderConfig, bool) {
	st := r.state.Load()
	p, ok := st.providers[name]
	return p, ok
}

// Swap atomically replaces config with a freshly loaded Router (DRD GW-015).
func (r *Router) Swap(other *Router) {
	r.state.Store(other.state.Load())
}
