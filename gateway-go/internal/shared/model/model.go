// Package model holds the data structures shared across every tier.
//
// These types carry no behaviour, so depending on them creates no coupling
// between tiers: the api tier, the service tier and the repository tier can
// all speak the same vocabulary without any of them importing another.
// Keeping them here is what lets repository/adapters take a ProviderConfig
// without importing service/router, which would be an upward dependency.
package model

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
