package auth

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/redis/go-redis/v9"
)

// --- Redis loader (L1) ---

type redisLoader struct {
	client *redis.Client
}

// NewRedisLoader builds a Loader backed by Redis. Key format: auth:{key_hash}.
func NewRedisLoader(url string) Loader {
	opts, err := redis.ParseURL(url)
	if err != nil {
		// Configuration is validated upstream; fail loud here.
		panic("auth: invalid redis url: " + err.Error())
	}
	return &redisLoader{client: redis.NewClient(opts)}
}

func (l *redisLoader) Load(ctx context.Context, keyHash string) (Metadata, error) {
	val, err := l.client.Get(ctx, "auth:"+keyHash).Bytes()
	if errors.Is(err, redis.Nil) {
		return Metadata{}, ErrCacheMiss
	}
	if err != nil {
		return Metadata{}, err
	}
	var m Metadata
	if err := json.Unmarshal(val, &m); err != nil {
		return Metadata{}, err
	}
	return m, nil
}

// --- Backend gRPC loader (L2) ---
//
// In production this dials backend.AuthService.ValidateKey. The interface is
// kept thin so a mock can be substituted in tests.

type backendLoader struct {
	addr   string
	client backendAuthClient // gRPC client; injected for tests
}

type backendAuthClient interface {
	Validate(ctx context.Context, keyHash string) (Metadata, error)
	PingHealth(ctx context.Context) error
}

// NewBackendLoader builds a loader that calls the Python backend over gRPC.
// The actual gRPC client is wired in internal/transport/grpc/clients.go.
func NewBackendLoader(addr string) Loader {
	return &backendLoader{
		addr:   addr,
		client: newGRPCAuthClient(addr),
	}
}

func (l *backendLoader) Load(ctx context.Context, keyHash string) (Metadata, error) {
	ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	return l.client.Validate(ctx, keyHash)
}

func (l *backendLoader) Ping(ctx context.Context) error {
	return l.client.PingHealth(ctx)
}
