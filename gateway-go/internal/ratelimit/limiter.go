// Package ratelimit implements per-key sliding-window rate limiting in Redis.
//
// Pattern: Strategy interface so Redis can be swapped for an in-process limiter
// in tests, or for a regional limiter in multi-region deployments.
package ratelimit

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// Key is the rate limit lookup key, bundling identity + policy.
type Key struct {
	KeyID             string
	RequestsPerMinute uint32
}

// Result is the limiter decision plus headers data.
type Result struct {
	Allowed   bool
	Limit     uint32
	Remaining uint32
	ResetAt   time.Time
}

// Limiter is the strategy interface. All implementations must be safe for concurrent use.
type Limiter interface {
	Check(ctx context.Context, k Key) (Result, error)
}

// --- Redis sliding-window implementation ---

type redisLimiter struct {
	client *redis.Client
}

// NewRedisLimiter dials Redis and returns a sliding-window limiter.
func NewRedisLimiter(url string) (Limiter, error) {
	opts, err := redis.ParseURL(url)
	if err != nil {
		return nil, fmt.Errorf("parse url: %w", err)
	}
	c := redis.NewClient(opts)
	if err := c.Ping(context.Background()).Err(); err != nil {
		return nil, fmt.Errorf("ping redis: %w", err)
	}
	return &redisLimiter{client: c}, nil
}

// slidingWindowScript is an atomic Lua script: sliding window via sorted set.
//
//	KEYS[1] = bucket key
//	ARGV[1] = window size in ms
//	ARGV[2] = limit
//	ARGV[3] = current ts in ms
//	ARGV[4] = unique member (request_id)
//
// Returns: {allowed (0|1), remaining, reset_ts_ms}
const slidingWindowScript = `
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit  = tonumber(ARGV[2])
local now    = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count < limit then
  redis.call('ZADD', key, now, member)
  redis.call('PEXPIRE', key, window)
  return {1, limit - count - 1, now + window}
end
return {0, 0, now + window}
`

func (l *redisLimiter) Check(ctx context.Context, k Key) (Result, error) {
	if k.RequestsPerMinute == 0 {
		// No policy => unlimited.
		return Result{Allowed: true, Limit: 0, Remaining: 0, ResetAt: time.Now().Add(time.Minute)}, nil
	}
	now := time.Now()
	resp, err := l.client.Eval(ctx, slidingWindowScript,
		[]string{"rl:" + k.KeyID},
		60_000,
		k.RequestsPerMinute,
		now.UnixMilli(),
		fmt.Sprintf("%d", now.UnixNano()),
	).Result()
	if err != nil {
		return Result{}, fmt.Errorf("redis eval: %w", err)
	}
	arr, ok := resp.([]interface{})
	if !ok || len(arr) != 3 {
		return Result{}, errors.New("ratelimit: unexpected redis reply")
	}
	allowed, _ := arr[0].(int64)
	remaining, _ := arr[1].(int64)
	resetMs, _ := arr[2].(int64)
	return Result{
		Allowed:   allowed == 1,
		Limit:     k.RequestsPerMinute,
		Remaining: uint32(remaining),
		ResetAt:   time.UnixMilli(resetMs),
	}, nil
}
