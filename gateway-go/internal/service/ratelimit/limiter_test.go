package ratelimit

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
)

func TestLimiter_NoPolicyMeansUnlimited(t *testing.T) {
	mr := miniredis.RunT(t)
	l, err := NewRedisLimiter("redis://" + mr.Addr())
	if err != nil {
		t.Fatalf("NewRedisLimiter: %v", err)
	}
	r, err := l.Check(context.Background(), Key{KeyID: "u1", RequestsPerMinute: 0})
	if err != nil {
		t.Fatalf("Check: %v", err)
	}
	if !r.Allowed {
		t.Error("expected unlimited policy to always allow")
	}
}

func TestLimiter_AllowsUpToLimitThenRejects(t *testing.T) {
	mr := miniredis.RunT(t)
	l, err := NewRedisLimiter("redis://" + mr.Addr())
	if err != nil {
		t.Fatalf("NewRedisLimiter: %v", err)
	}
	ctx := context.Background()
	k := Key{KeyID: "u2", RequestsPerMinute: 3}

	for i := 0; i < 3; i++ {
		r, err := l.Check(ctx, k)
		if err != nil {
			t.Fatalf("Check %d: %v", i, err)
		}
		if !r.Allowed {
			t.Fatalf("request %d should be allowed", i)
		}
	}

	r, err := l.Check(ctx, k)
	if err != nil {
		t.Fatalf("Check 4: %v", err)
	}
	if r.Allowed {
		t.Error("4th request should be rejected (limit=3)")
	}
	if r.Limit != 3 {
		t.Errorf("Limit = %d, want 3", r.Limit)
	}
}

func TestLimiter_RemainingDecreases(t *testing.T) {
	mr := miniredis.RunT(t)
	l, _ := NewRedisLimiter("redis://" + mr.Addr())
	ctx := context.Background()
	k := Key{KeyID: "u3", RequestsPerMinute: 5}

	var prev uint32 = 100
	for i := 0; i < 5; i++ {
		r, _ := l.Check(ctx, k)
		if !r.Allowed {
			t.Fatalf("request %d unexpectedly rejected", i)
		}
		if r.Remaining >= prev && i > 0 {
			t.Errorf("Remaining did not decrease across calls: %d -> %d", prev, r.Remaining)
		}
		prev = r.Remaining
	}
}

func TestLimiter_WindowExpiryRestoresQuota(t *testing.T) {
	mr := miniredis.RunT(t)
	l, _ := NewRedisLimiter("redis://" + mr.Addr())
	ctx := context.Background()
	k := Key{KeyID: "u4", RequestsPerMinute: 1}

	r1, _ := l.Check(ctx, k)
	if !r1.Allowed {
		t.Fatal("first request should be allowed")
	}
	r2, _ := l.Check(ctx, k)
	if r2.Allowed {
		t.Fatal("second request within window should be rejected")
	}

	// Advance miniredis past the 60s sliding window.
	mr.FastForward(61 * time.Second)
	r3, _ := l.Check(ctx, k)
	if !r3.Allowed {
		t.Error("after window expiry, request should be allowed again")
	}
}

func TestLimiter_ResetAtIsInTheFuture(t *testing.T) {
	mr := miniredis.RunT(t)
	l, _ := NewRedisLimiter("redis://" + mr.Addr())
	r, _ := l.Check(context.Background(), Key{KeyID: "u5", RequestsPerMinute: 10})
	if !r.ResetAt.After(time.Now()) {
		t.Errorf("ResetAt = %v, want a future time", r.ResetAt)
	}
}
