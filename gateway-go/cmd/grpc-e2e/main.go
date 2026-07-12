// Command grpc-e2e probes a running backend AuthService over gRPC.
//
// Usage:
//
//	go run ./cmd/grpc-e2e [addr]
//
// Default addr is localhost:50051. Calls ValidateKey with a known-bogus key
// and asserts the response is valid=false reason="unknown_key". Useful as a
// connectivity smoke test in CI and for incident triage.
package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	authv1 "github.com/openrouter/gateway-go/internal/proto/auth/v1"
)

func main() {
	addr := "localhost:50051"
	if len(os.Args) > 1 {
		addr = os.Args[1]
	}

	cc, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		fmt.Fprintln(os.Stderr, "dial:", err)
		os.Exit(1)
	}
	defer cc.Close()

	cli := authv1.NewAuthServiceClient(cc)
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	resp, err := cli.ValidateKey(ctx, &authv1.ValidateKeyRequest{KeyHash: "nonexistent-smoke-hash"})
	if err != nil {
		fmt.Fprintln(os.Stderr, "ValidateKey:", err)
		os.Exit(1)
	}
	fmt.Printf("addr=%s valid=%v reason=%q key_id=%q\n", addr, resp.Valid, resp.RevocationReason, resp.KeyId)
	if resp.Valid || resp.RevocationReason != "unknown_key" {
		fmt.Fprintln(os.Stderr, "FAIL: expected valid=false reason=unknown_key")
		os.Exit(1)
	}
	fmt.Println("PASS: Go gRPC client ↔ backend AuthService reachable")
}
