// Package config loads and validates gateway configuration.
// Pattern: koanf with env-var precedence over YAML files.
package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/knadh/koanf/parsers/yaml"
	"github.com/knadh/koanf/providers/env"
	"github.com/knadh/koanf/providers/file"
	"github.com/knadh/koanf/v2"
)

type Config struct {
	Environment string `koanf:"environment"`
	LogLevel    string `koanf:"log_level"`
	Version     string `koanf:"service_version"`

	HTTP    HTTPConfig    `koanf:"http"`
	Metrics MetricsConfig `koanf:"metrics"`
	Redis   RedisConfig   `koanf:"redis"`
	Backend BackendConfig `koanf:"backend"`
	Auth    AuthConfig    `koanf:"auth"`
	NATS    NATSConfig    `koanf:"nats"`
	OTel    OTelConfig    `koanf:"otel"`

	ProviderConfigPath string `koanf:"provider_config"`
}

type HTTPConfig struct {
	Port            int           `koanf:"port"`
	ReadTimeout     time.Duration `koanf:"read_timeout"`
	WriteTimeout    time.Duration `koanf:"write_timeout"`
	ShutdownTimeout time.Duration `koanf:"shutdown_timeout"`
}

type MetricsConfig struct {
	Port int `koanf:"port"`
}

type RedisConfig struct {
	URL      string `koanf:"url"`
	PoolSize int    `koanf:"pool_size"`
}

type BackendConfig struct {
	GRPCAddr string `koanf:"grpc_addr"`
}

type AuthConfig struct {
	CacheTTL  time.Duration `koanf:"cache_ttl"`
	CacheSize int           `koanf:"cache_size"`
}

type NATSConfig struct {
	URL    string `koanf:"url"`
	Stream string `koanf:"stream"`
}

type OTelConfig struct {
	Endpoint   string  `koanf:"endpoint"`
	Service    string  `koanf:"service"`
	SampleRate float64 `koanf:"sample_rate"`
}

// Load builds the config from defaults → optional YAML file → env vars.
// Env vars use the GATEWAY_ prefix; underscores map to nested fields:
//
//	GATEWAY_HTTP_PORT=8080 → cfg.HTTP.Port = 8080
func Load() (*Config, error) {
	k := koanf.New(".")

	// Defaults.
	if err := k.Load(rawDefaults{}, nil); err != nil {
		return nil, fmt.Errorf("load defaults: %w", err)
	}

	// Optional YAML.
	if path := envOr("GATEWAY_CONFIG_FILE", ""); path != "" {
		if err := k.Load(file.Provider(path), yaml.Parser()); err != nil {
			return nil, fmt.Errorf("load yaml %s: %w", path, err)
		}
	}

	// Env overrides.
	if err := k.Load(env.Provider("GATEWAY_", ".", func(s string) string {
		return strings.ReplaceAll(strings.ToLower(strings.TrimPrefix(s, "GATEWAY_")), "_", ".")
	}), nil); err != nil {
		return nil, fmt.Errorf("load env: %w", err)
	}

	cfg := &Config{}
	if err := k.Unmarshal("", cfg); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}

	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}
	return cfg, nil
}

func (c *Config) validate() error {
	if c.HTTP.Port <= 0 || c.HTTP.Port > 65535 {
		return fmt.Errorf("http.port out of range: %d", c.HTTP.Port)
	}
	if c.Redis.URL == "" {
		return fmt.Errorf("redis.url required")
	}
	if c.Backend.GRPCAddr == "" {
		return fmt.Errorf("backend.grpc_addr required")
	}
	return nil
}

// --- defaults provider (implements koanf.Provider interface) ---

type rawDefaults struct{}

func (rawDefaults) ReadBytes() ([]byte, error) { return nil, nil }
func (rawDefaults) Read() (map[string]interface{}, error) {
	return map[string]interface{}{
		"environment":     "dev",
		"log_level":       "info",
		"service_version": "0.1.0",
		"http": map[string]interface{}{
			"port":             8080,
			"read_timeout":     "30s",
			"write_timeout":    "30s",
			"shutdown_timeout": "30s",
		},
		"metrics": map[string]interface{}{"port": 9091},
		"redis": map[string]interface{}{
			"url":       "redis://localhost:6379/0",
			"pool_size": 50,
		},
		"backend": map[string]interface{}{"grpc_addr": "localhost:50051"},
		"auth": map[string]interface{}{
			"cache_ttl":  "60s",
			"cache_size": 10000,
		},
		"nats": map[string]interface{}{
			"url":    "nats://localhost:4222",
			"stream": "GATEWAY_EVENTS",
		},
		"otel": map[string]interface{}{
			"endpoint":    "http://localhost:4317",
			"service":     "gateway-go",
			"sample_rate": 0.01,
		},
		"provider_config": "./configs/providers.yaml",
	}, nil
}

func envOr(k, def string) string {
	v := getEnv(k)
	if v == "" {
		return def
	}
	return v
}

// indirection for testability
var getEnv = func(k string) string { return getenvStdlib(k) }
