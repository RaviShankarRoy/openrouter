package auth

import (
	"context"
	"errors"
	"fmt"
	"sync"

	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials/insecure"

	authv1 "github.com/openrouter/gateway-go/internal/repository/proto/auth/v1"
)

// newGRPCAuthClient builds a backendAuthClient that dials the Python backend's
// AuthService. The connection is established lazily on first call so a missing
// or unhealthy backend doesn't block gateway startup. Internal mTLS is provided
// by the service mesh in production; the gRPC layer itself uses insecure creds.
func newGRPCAuthClient(addr string) backendAuthClient {
	return &grpcAuthClient{addr: addr}
}

type grpcAuthClient struct {
	addr string

	once sync.Once
	cc   *grpc.ClientConn
	cli  authv1.AuthServiceClient
	err  error
}

func (c *grpcAuthClient) connect() error {
	c.once.Do(func() {
		if c.addr == "" {
			c.err = errors.New("auth: backend address empty")
			return
		}
		cc, err := grpc.NewClient(c.addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
		if err != nil {
			c.err = fmt.Errorf("auth: grpc.NewClient: %w", err)
			return
		}
		c.cc = cc
		c.cli = authv1.NewAuthServiceClient(cc)
	})
	return c.err
}

func (c *grpcAuthClient) Validate(ctx context.Context, keyHash string) (Metadata, error) {
	if err := c.connect(); err != nil {
		return Metadata{}, err
	}
	resp, err := c.cli.ValidateKey(ctx, &authv1.ValidateKeyRequest{KeyHash: keyHash})
	if err != nil {
		return Metadata{}, fmt.Errorf("auth: backend ValidateKey: %w", err)
	}
	// Treat "unknown_key" as cache miss so the cache layer applies the
	// negative-cache TTL uniformly with Redis misses.
	if !resp.Valid && resp.RevocationReason == "unknown_key" {
		return Metadata{}, ErrCacheMiss
	}
	m := Metadata{
		Valid:         resp.Valid,
		KeyID:         resp.KeyId,
		OrgID:         resp.OrgId,
		UserID:        resp.UserId,
		AllowedModels: resp.AllowedModels,
		DeniedModels:  resp.DeniedModels,
	}
	if rl := resp.RateLimit; rl != nil {
		m.RateLimit = RateLimitPolicy{
			RequestsPerMinute:  rl.RequestsPerMinute,
			TokensPerMinute:    rl.TokensPerMinute,
			ConcurrentRequests: rl.ConcurrentRequests,
			RequestsPerDay:     rl.RequestsPerDay,
		}
	}
	if b := resp.Budget; b != nil {
		m.Budget = BudgetPolicy{
			RemainingCredits: b.RemainingCredits,
			HardStop:         b.HardStop,
		}
	}
	if resp.ExpiresAt != nil {
		m.ExpiresAt = resp.ExpiresAt.AsTime()
	}
	return m, nil
}

func (c *grpcAuthClient) PingHealth(ctx context.Context) error {
	if err := c.connect(); err != nil {
		return err
	}
	state := c.cc.GetState()
	if state == connectivity.Shutdown || state == connectivity.TransientFailure {
		return fmt.Errorf("auth: backend connection state %s", state)
	}
	return nil
}
