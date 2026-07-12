package cache

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
)

func TestHashRequest_StableAcrossCalls(t *testing.T) {
	body := []byte(`{"messages":[{"role":"user","content":"hi"}],"temperature":0}`)
	a := HashRequest("openai/gpt-4o", body)
	b := HashRequest("openai/gpt-4o", body)
	if a != b {
		t.Fatalf("hash not stable: %s vs %s", a, b)
	}
	if len(a) != 64 {
		t.Fatalf("want 64-hex sha256, got len=%d", len(a))
	}
}

func TestHashRequest_DifferentInputsDiffer(t *testing.T) {
	hX := HashRequest("openai/gpt-4o", []byte(`{"a":1}`))
	hModel := HashRequest("anthropic/claude-3", []byte(`{"a":1}`))
	hBody := HashRequest("openai/gpt-4o", []byte(`{"a":2}`))
	if hX == hModel {
		t.Error("hash should differ on model")
	}
	if hX == hBody {
		t.Error("hash should differ on body")
	}
}

func TestHashRequest_DelimiterPreventsCollision(t *testing.T) {
	// "ab" + "cd" must hash differently from "abc" + "d" — the null byte
	// delimiter in HashRequest exists exactly to prevent this collision.
	a := HashRequest("ab", []byte("cd"))
	b := HashRequest("abc", []byte("d"))
	if a == b {
		t.Errorf("delimiter missing: hash collided across model/body boundary")
	}
}

func TestRedisExact_PutGetMissRoundtrip(t *testing.T) {
	mr := miniredis.RunT(t)
	cache, err := NewRedisExact("redis://" + mr.Addr())
	if err != nil {
		t.Fatalf("NewRedisExact: %v", err)
	}
	ctx := context.Background()

	// Miss before put.
	_, ok, err := cache.Get(ctx, "k1")
	if err != nil {
		t.Fatalf("Get pre-put: %v", err)
	}
	if ok {
		t.Fatal("expected miss, got hit")
	}

	entry := Entry{
		Body:        []byte(`{"choices":[]}`),
		ContentType: "application/json",
		Status:      200,
		StoredAt:    time.Now().UTC(),
	}
	if err := cache.Put(ctx, "k1", entry, time.Minute); err != nil {
		t.Fatalf("Put: %v", err)
	}

	got, ok, err := cache.Get(ctx, "k1")
	if err != nil {
		t.Fatalf("Get post-put: %v", err)
	}
	if !ok {
		t.Fatal("expected hit after Put")
	}
	if string(got.Body) != string(entry.Body) || got.Status != entry.Status {
		t.Errorf("got %+v, want %+v", got, entry)
	}
}

func TestRedisExact_TTLExpiry(t *testing.T) {
	mr := miniredis.RunT(t)
	cache, _ := NewRedisExact("redis://" + mr.Addr())
	ctx := context.Background()

	if err := cache.Put(ctx, "k", Entry{Body: []byte("x"), Status: 200}, 100*time.Millisecond); err != nil {
		t.Fatal(err)
	}
	mr.FastForward(200 * time.Millisecond)
	_, ok, err := cache.Get(ctx, "k")
	if err != nil {
		t.Fatal(err)
	}
	if ok {
		t.Error("expected expired entry to miss")
	}
}

func TestRedisExact_Ping(t *testing.T) {
	mr := miniredis.RunT(t)
	cache, _ := NewRedisExact("redis://" + mr.Addr())
	if err := cache.Ping(context.Background()); err != nil {
		t.Errorf("Ping should succeed against live redis: %v", err)
	}
}
