// Package cache implements the L1 exact-match response cache.
// L2 semantic cache lives in the Python backend.
package cache

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// Entry is a cached response.
type Entry struct {
	Body        []byte    `json:"body"`
	ContentType string    `json:"content_type"`
	Status      int       `json:"status"`
	StoredAt    time.Time `json:"stored_at"`
}

// ExactCache is the strategy interface for L1 caching.
type ExactCache interface {
	Get(ctx context.Context, key string) (Entry, bool, error)
	Put(ctx context.Context, key string, e Entry, ttl time.Duration) error
	Ping(ctx context.Context) error
}

// HashRequest produces the cache key for a chat completion (DRD CA-001).
// Stable across structurally identical requests; different on any param change.
func HashRequest(model string, body []byte) string {
	h := sha256.New()
	h.Write([]byte(model))
	h.Write([]byte{0x00})
	h.Write(body)
	return hex.EncodeToString(h.Sum(nil))
}

// --- Redis implementation ---

type redisExact struct {
	client *redis.Client
}

func NewRedisExact(url string) (ExactCache, error) {
	opts, err := redis.ParseURL(url)
	if err != nil {
		return nil, fmt.Errorf("parse url: %w", err)
	}
	return &redisExact{client: redis.NewClient(opts)}, nil
}

func (r *redisExact) Get(ctx context.Context, key string) (Entry, bool, error) {
	val, err := r.client.Get(ctx, "cache:l1:"+key).Bytes()
	if errors.Is(err, redis.Nil) {
		return Entry{}, false, nil
	}
	if err != nil {
		return Entry{}, false, err
	}
	var e Entry
	if err := json.Unmarshal(val, &e); err != nil {
		return Entry{}, false, err
	}
	return e, true, nil
}

func (r *redisExact) Put(ctx context.Context, key string, e Entry, ttl time.Duration) error {
	b, err := json.Marshal(e)
	if err != nil {
		return err
	}
	return r.client.Set(ctx, "cache:l1:"+key, b, ttl).Err()
}

func (r *redisExact) Ping(ctx context.Context) error {
	return r.client.Ping(ctx).Err()
}
