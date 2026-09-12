// Package auth implements the layered cache for API key validation.
//
// Pattern: Read-through cache with two backends.
//   L0: in-process LRU (lock-free reads, ~100ns)
//   L1: Redis (network ~500µs)
//   L2: Backend gRPC (~10ms)
//
// On miss at any layer, populates upstream layers. On revoke, backend
// publishes invalidation events to Redis pub/sub which clears L0 across
// all gateway pods.
package auth

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"
)

// Metadata is the resolved API key information cached at every layer.
type Metadata struct {
	Valid         bool
	KeyID         string
	OrgID         string
	UserID        string
	AllowedModels []string
	DeniedModels  []string
	RateLimit     RateLimitPolicy
	Budget        BudgetPolicy
	ExpiresAt     time.Time
	cachedAt      time.Time
}

type RateLimitPolicy struct {
	RequestsPerMinute  uint32
	TokensPerMinute    uint32
	ConcurrentRequests uint32
	RequestsPerDay     uint32
}

type BudgetPolicy struct {
	RemainingCredits float64
	HardStop         bool
}

// Loader fetches metadata from a backing store. The Cache composes Loaders
// in priority order: try first, fall through on miss.
type Loader interface {
	Load(ctx context.Context, keyHash string) (Metadata, error)
}

// ErrCacheMiss is returned by a Loader when the key is not in its store.
var ErrCacheMiss = errors.New("auth: cache miss")

// Cache is a multi-layer key→Metadata cache.
type Cache struct {
	ttl     time.Duration
	loaders []Loader

	mu   sync.RWMutex
	data map[string]Metadata // L0 LRU; production swaps for golang-lru/v2
	cap  int

	backend BackendPinger
}

// BackendPinger is implemented by loaders that know how to health-check upstream.
type BackendPinger interface {
	Ping(ctx context.Context) error
}

// NewCache builds a layered cache. Loaders are tried in order on miss.
func NewCache(size int, ttl time.Duration, loaders ...Loader) (*Cache, error) {
	if size <= 0 {
		return nil, fmt.Errorf("invalid cache size: %d", size)
	}
	if len(loaders) == 0 {
		return nil, fmt.Errorf("at least one loader required")
	}
	c := &Cache{
		ttl:     ttl,
		loaders: loaders,
		data:    make(map[string]Metadata, size),
		cap:     size,
	}
	if p, ok := loaders[len(loaders)-1].(BackendPinger); ok {
		c.backend = p
	}
	return c, nil
}

// Get returns metadata for keyHash, populating upstream layers on miss.
func (c *Cache) Get(ctx context.Context, keyHash string) (Metadata, error) {
	// L0: in-process.
	c.mu.RLock()
	m, ok := c.data[keyHash]
	c.mu.RUnlock()
	if ok && time.Since(m.cachedAt) < c.ttl {
		return m, nil
	}

	// Fall through loaders.
	var lastErr error
	for _, l := range c.loaders {
		m, err := l.Load(ctx, keyHash)
		if err == nil {
			m.cachedAt = time.Now()
			c.put(keyHash, m)
			return m, nil
		}
		if !errors.Is(err, ErrCacheMiss) {
			lastErr = err
			break
		}
		lastErr = err
	}
	if errors.Is(lastErr, ErrCacheMiss) {
		// Cache the negative result briefly to avoid hammering on bad keys.
		neg := Metadata{Valid: false, cachedAt: time.Now()}
		c.put(keyHash, neg)
		return neg, nil
	}
	return Metadata{}, lastErr
}

// Invalidate removes a key from L0. Triggered by Redis pub/sub on revoke.
func (c *Cache) Invalidate(keyHash string) {
	c.mu.Lock()
	delete(c.data, keyHash)
	c.mu.Unlock()
}

// PingBackend reports whether the deepest loader is reachable.
func (c *Cache) PingBackend(ctx context.Context) error {
	if c.backend == nil {
		return nil
	}
	return c.backend.Ping(ctx)
}

func (c *Cache) put(k string, m Metadata) {
	c.mu.Lock()
	defer c.mu.Unlock()
	// Trivial eviction: drop random entry when full.
	// Production replaces with hashicorp/golang-lru/v2.
	if len(c.data) >= c.cap {
		for ek := range c.data {
			delete(c.data, ek)
			break
		}
	}
	c.data[k] = m
}
