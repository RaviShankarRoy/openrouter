package auth

import (
	"context"
	"errors"
	"testing"
	"time"
)

type stubLoader struct {
	data map[string]Metadata
	err  error
}

func (s *stubLoader) Load(_ context.Context, key string) (Metadata, error) {
	if s.err != nil {
		return Metadata{}, s.err
	}
	if m, ok := s.data[key]; ok {
		return m, nil
	}
	return Metadata{}, ErrCacheMiss
}

func TestCache_HitFromLoader(t *testing.T) {
	loader := &stubLoader{data: map[string]Metadata{
		"abc": {Valid: true, KeyID: "key_1", OrgID: "org_1"},
	}}
	c, err := NewCache(10, time.Minute, loader)
	if err != nil {
		t.Fatal(err)
	}
	got, err := c.Get(context.Background(), "abc")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.KeyID != "key_1" {
		t.Errorf("want key_1, got %q", got.KeyID)
	}
}

func TestCache_NegativeCacheOnMiss(t *testing.T) {
	c, _ := NewCache(10, time.Minute, &stubLoader{data: map[string]Metadata{}})
	got, err := c.Get(context.Background(), "missing")
	if err != nil {
		t.Fatal(err)
	}
	if got.Valid {
		t.Error("expected Valid=false for missing key")
	}
}

func TestCache_FallsThroughLoaders(t *testing.T) {
	miss := &stubLoader{data: map[string]Metadata{}}
	hit := &stubLoader{data: map[string]Metadata{
		"abc": {Valid: true, KeyID: "key_2"},
	}}
	c, _ := NewCache(10, time.Minute, miss, hit)
	got, _ := c.Get(context.Background(), "abc")
	if got.KeyID != "key_2" {
		t.Errorf("expected key_2, got %q", got.KeyID)
	}
}

func TestCache_InvalidateClearsL0(t *testing.T) {
	loader := &stubLoader{data: map[string]Metadata{
		"abc": {Valid: true, KeyID: "key_1"},
	}}
	c, _ := NewCache(10, time.Minute, loader)
	_, _ = c.Get(context.Background(), "abc")
	c.Invalidate("abc")

	loader.data["abc"] = Metadata{Valid: true, KeyID: "key_1_revoked"}
	got, _ := c.Get(context.Background(), "abc")
	if got.KeyID != "key_1_revoked" {
		t.Errorf("expected refreshed value, got %q", got.KeyID)
	}
}

func TestCache_PropagatesNonMissError(t *testing.T) {
	loader := &stubLoader{err: errors.New("redis down")}
	c, _ := NewCache(10, time.Minute, loader)
	_, err := c.Get(context.Background(), "abc")
	if err == nil {
		t.Error("expected error to propagate")
	}
}
