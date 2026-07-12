package auth

import (
	"context"
	"net"
	"testing"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/types/known/timestamppb"

	authv1 "github.com/openrouter/gateway-go/internal/proto/auth/v1"
)

// fakeAuthServer implements authv1.AuthServiceServer for tests. It returns a
// canned response per key_hash so we can exercise the translation in
// grpcAuthClient.Validate without standing up the Python backend.
type fakeAuthServer struct {
	authv1.UnimplementedAuthServiceServer
	responses map[string]*authv1.ValidateKeyResponse
}

func (f *fakeAuthServer) ValidateKey(_ context.Context, req *authv1.ValidateKeyRequest) (*authv1.ValidateKeyResponse, error) {
	if r, ok := f.responses[req.GetKeyHash()]; ok {
		return r, nil
	}
	return &authv1.ValidateKeyResponse{Valid: false, RevocationReason: "unknown_key"}, nil
}

// startFakeServer returns the listening address; cleanup stops the server.
func startFakeServer(t *testing.T, fake *fakeAuthServer) string {
	t.Helper()
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	srv := grpc.NewServer()
	authv1.RegisterAuthServiceServer(srv, fake)
	go func() { _ = srv.Serve(lis) }()
	t.Cleanup(srv.Stop)
	return lis.Addr().String()
}

func TestGRPCAuthClient_Validate_Valid(t *testing.T) {
	expires := time.Now().Add(24 * time.Hour).UTC().Truncate(time.Second)
	fake := &fakeAuthServer{
		responses: map[string]*authv1.ValidateKeyResponse{
			"hash-good": {
				Valid:         true,
				KeyId:         "key-1",
				OrgId:         "org-1",
				UserId:        "user-1",
				AllowedModels: []string{"openai/gpt-4o", "anthropic/claude-3"},
				DeniedModels:  []string{"openai/gpt-3.5"},
				RateLimit: &authv1.RateLimitPolicy{
					RequestsPerMinute:  120,
					TokensPerMinute:    100_000,
					ConcurrentRequests: 10,
					RequestsPerDay:     50_000,
				},
				Budget: &authv1.BudgetPolicy{
					RemainingCredits: 12.34,
					DailyCap:         5,
					MonthlyCap:       100,
					HardStop:         true,
				},
				ExpiresAt: timestamppb.New(expires),
			},
		},
	}
	addr := startFakeServer(t, fake)

	c := newGRPCAuthClient(addr)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	m, err := c.Validate(ctx, "hash-good")
	if err != nil {
		t.Fatalf("Validate: %v", err)
	}
	if !m.Valid {
		t.Fatalf("expected Valid=true, got %+v", m)
	}
	if m.KeyID != "key-1" || m.OrgID != "org-1" || m.UserID != "user-1" {
		t.Errorf("identity mismatch: %+v", m)
	}
	if len(m.AllowedModels) != 2 || m.AllowedModels[0] != "openai/gpt-4o" {
		t.Errorf("allowed_models: %v", m.AllowedModels)
	}
	if m.RateLimit.RequestsPerMinute != 120 || m.RateLimit.TokensPerMinute != 100_000 {
		t.Errorf("rate_limit: %+v", m.RateLimit)
	}
	if m.Budget.RemainingCredits != 12.34 || !m.Budget.HardStop {
		t.Errorf("budget: %+v", m.Budget)
	}
	if !m.ExpiresAt.Equal(expires) {
		t.Errorf("expires_at: got %v, want %v", m.ExpiresAt, expires)
	}
}

func TestGRPCAuthClient_Validate_UnknownKey_ReturnsCacheMiss(t *testing.T) {
	fake := &fakeAuthServer{responses: nil}
	addr := startFakeServer(t, fake)

	c := newGRPCAuthClient(addr)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	_, err := c.Validate(ctx, "hash-unknown")
	if err == nil {
		t.Fatal("expected ErrCacheMiss, got nil")
	}
	if err != ErrCacheMiss {
		t.Fatalf("expected ErrCacheMiss, got %v", err)
	}
}

func TestGRPCAuthClient_Validate_RevokedKey_ReturnsInvalid(t *testing.T) {
	fake := &fakeAuthServer{
		responses: map[string]*authv1.ValidateKeyResponse{
			"hash-revoked": {Valid: false, RevocationReason: "revoked_by_admin"},
		},
	}
	addr := startFakeServer(t, fake)

	c := newGRPCAuthClient(addr)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	m, err := c.Validate(ctx, "hash-revoked")
	if err != nil {
		t.Fatalf("Validate: %v", err)
	}
	if m.Valid {
		t.Fatal("expected Valid=false for revoked key")
	}
}

func TestGRPCAuthClient_EmptyAddr_ReturnsError(t *testing.T) {
	c := newGRPCAuthClient("")
	_, err := c.Validate(context.Background(), "any")
	if err == nil {
		t.Fatal("expected error for empty addr, got nil")
	}
}

// Compile-time assertion that the constructor still satisfies the loader's interface.
var _ backendAuthClient = (*grpcAuthClient)(nil)

// Suppress "imported and not used" if insecure happens to be unused in some builds.
var _ = insecure.NewCredentials
