package strategies

import (
	"context"
	"sort"

	"github.com/openrouter/gateway-go/internal/shared/model"
)

// Cost orders targets cheapest-first. Pricing data is mirrored into
// the gateway from the backend on a 60s timer.
type Cost struct {
	pricing PricingLookup
}

// PricingLookup returns input+output per-token cost; gateway loads it from Redis.
type PricingLookup interface {
	UnitCost(provider, model string) float64
}

func NewCost(p PricingLookup) *Cost { return &Cost{pricing: p} }

func (c *Cost) Name() string { return "cost" }

func (c *Cost) Order(_ context.Context, candidates []model.Target) []model.Target {
	out := make([]model.Target, len(candidates))
	copy(out, candidates)
	sort.SliceStable(out, func(i, j int) bool {
		return c.pricing.UnitCost(out[i].Provider, out[i].Model) <
			c.pricing.UnitCost(out[j].Provider, out[j].Model)
	})
	return out
}
