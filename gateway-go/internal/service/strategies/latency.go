package strategies

import (
	"context"
	"sort"

	"github.com/openrouter/gateway-go/internal/shared/model"
)

// Latency orders targets fastest-first based on rolling P50 from the
// metering pipeline (DRD RT-005).
type Latency struct {
	scores ScoreLookup
}

// ScoreLookup returns a 0..1 score where higher is better (lower latency).
type ScoreLookup interface {
	Score(provider, model string) float64
}

func NewLatency(s ScoreLookup) *Latency { return &Latency{scores: s} }

func (l *Latency) Name() string { return "latency" }

func (l *Latency) Order(_ context.Context, candidates []model.Target) []model.Target {
	out := make([]model.Target, len(candidates))
	copy(out, candidates)
	sort.SliceStable(out, func(i, j int) bool {
		return l.scores.Score(out[i].Provider, out[i].Model) >
			l.scores.Score(out[j].Provider, out[j].Model)
	})
	return out
}
