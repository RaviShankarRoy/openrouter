package observability

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Per DRD §17.1, every metric here matches the documented contract.
// Cardinality discipline: NEVER label by user_id or request_id.
var (
	RequestsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "gateway_requests_total",
		Help: "Total HTTP requests by model, provider, status",
	}, []string{"model", "provider", "status"})

	RequestDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "gateway_request_duration_seconds",
		Help:    "End-to-end request duration",
		Buckets: prometheus.ExponentialBuckets(0.001, 2, 16),
	}, []string{"model", "provider", "cache_hit"})

	ProviderLatency = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "gateway_provider_latency_seconds",
		Help:    "Upstream provider call duration",
		Buckets: prometheus.ExponentialBuckets(0.001, 2, 16),
	}, []string{"provider", "model"})

	CacheHits = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "gateway_cache_hits_total",
		Help: "Cache hits by layer",
	}, []string{"layer", "model"})

	RateLimitRejections = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "gateway_rate_limit_rejections_total",
		Help: "Rate limit rejections by limit type",
	}, []string{"limit_type"})

	ProviderErrors = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "gateway_errors_total",
		Help: "Errors by provider, model, error_type",
	}, []string{"provider", "model", "error_type"})

	ActiveConnections = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "gateway_active_connections",
		Help: "Active outbound connections per provider",
	}, []string{"provider"})
)
