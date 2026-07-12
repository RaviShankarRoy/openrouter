// Package server is the composition root for HTTP + metrics listeners.
// Hexagonal architecture: this package wires concrete adapters into the domain.
package server

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"sync"

	"github.com/go-chi/chi/v5"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/openrouter/gateway-go/internal/auth"
	"github.com/openrouter/gateway-go/internal/cache"
	"github.com/openrouter/gateway-go/internal/circuitbreaker"
	"github.com/openrouter/gateway-go/internal/config"
	"github.com/openrouter/gateway-go/internal/middleware"
	"github.com/openrouter/gateway-go/internal/proxy"
	"github.com/openrouter/gateway-go/internal/ratelimit"
	"github.com/openrouter/gateway-go/internal/router"
	"github.com/openrouter/gateway-go/internal/transport/http/handlers"
)

// Server orchestrates the HTTP listener and the metrics listener.
type Server struct {
	cfg    *config.Config
	logger *slog.Logger
	mu     sync.RWMutex

	httpSrv    *http.Server
	metricsSrv *http.Server

	// Wired components — replaceable for testing.
	authCache  *auth.Cache
	rateLimit  ratelimit.Limiter
	exactCache cache.ExactCache
	router     *router.Router
	proxy      *proxy.Proxy
	breakers   *circuitbreaker.Registry
}

// New constructs a fully wired server. This is the only place that knows
// which concrete adapter implements which port.
func New(cfg *config.Config, logger *slog.Logger) (*Server, error) {
	// Build adapters in dependency order.
	authCache, err := auth.NewCache(cfg.Auth.CacheSize, cfg.Auth.CacheTTL,
		auth.NewRedisLoader(cfg.Redis.URL),
		auth.NewBackendLoader(cfg.Backend.GRPCAddr),
	)
	if err != nil {
		return nil, fmt.Errorf("auth cache: %w", err)
	}

	rl, err := ratelimit.NewRedisLimiter(cfg.Redis.URL)
	if err != nil {
		return nil, fmt.Errorf("rate limiter: %w", err)
	}

	exactCache, err := cache.NewRedisExact(cfg.Redis.URL)
	if err != nil {
		return nil, fmt.Errorf("exact cache: %w", err)
	}

	rt, err := router.LoadFromFile(cfg.ProviderConfigPath)
	if err != nil {
		return nil, fmt.Errorf("router: %w", err)
	}

	breakers := circuitbreaker.NewRegistry()
	pr := proxy.New(rt, breakers, logger)

	s := &Server{
		cfg:        cfg,
		logger:     logger,
		authCache:  authCache,
		rateLimit:  rl,
		exactCache: exactCache,
		router:     rt,
		proxy:      pr,
		breakers:   breakers,
	}
	s.httpSrv = s.buildHTTPServer()
	s.metricsSrv = s.buildMetricsServer()
	return s, nil
}

// buildHTTPServer assembles the chain-of-responsibility middleware stack
// then mounts handlers. Order matters — this is THE source of truth.
func (s *Server) buildHTTPServer() *http.Server {
	r := chi.NewRouter()

	// Global middleware (applies to every route).
	r.Use(middleware.RequestID)
	r.Use(middleware.Recoverer(s.logger))
	r.Use(middleware.Logger(s.logger))
	r.Use(middleware.Tracing("gateway-go"))

	// Public endpoints (no auth, no rate limit).
	r.Get("/health", handlers.Health)
	r.Get("/ready", handlers.Ready(s.dependencyChecks()))

	// API v1 — protected. Auth + rate limit scoped to this subtree only.
	r.Route("/api/v1", func(r chi.Router) {
		r.Use(middleware.Auth(s.authCache))
		r.Use(middleware.RateLimit(s.rateLimit))

		// Cache only applies to chat completions.
		chat := handlers.NewChatHandler(s.proxy, s.exactCache)
		r.Post("/chat/completions", chat.Create)

		// Pass-through endpoints — no caching, just proxy.
		r.Post("/embeddings", handlers.NewEmbeddingsHandler(s.proxy).Create)
		r.Post("/images/generations", handlers.NewImagesHandler(s.proxy).Create)
		r.Post("/audio/transcriptions", handlers.NewAudioHandler(s.proxy).Transcribe)
		r.Post("/rerank", handlers.NewRerankHandler(s.proxy).Create)

		// Async video jobs delegate fully to backend.
		video := handlers.NewVideoHandler(s.cfg.Backend.GRPCAddr)
		r.Post("/videos", video.Submit)
		r.Get("/videos/{job_id}", video.Status)
		r.Get("/videos/{job_id}/content", video.Content)

		// Catalog — backend-served.
		r.Get("/models", handlers.NewModelsHandler(s.cfg.Backend.GRPCAddr).List)
	})

	return &http.Server{
		Addr:         fmt.Sprintf(":%d", s.cfg.HTTP.Port),
		Handler:      r,
		ReadTimeout:  s.cfg.HTTP.ReadTimeout,
		WriteTimeout: s.cfg.HTTP.WriteTimeout,
	}
}

func (s *Server) buildMetricsServer() *http.Server {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	return &http.Server{
		Addr:    fmt.Sprintf(":%d", s.cfg.Metrics.Port),
		Handler: mux,
	}
}

func (s *Server) dependencyChecks() handlers.DependencyChecks {
	return handlers.DependencyChecks{
		"redis":   s.exactCache.Ping,
		"backend": s.authCache.PingBackend,
	}
}

// ServeHTTP blocks until ctx is canceled.
func (s *Server) ServeHTTP(ctx context.Context) error {
	s.logger.Info("http server listening", "addr", s.httpSrv.Addr)
	go func() {
		<-ctx.Done()
		_ = s.httpSrv.Shutdown(context.Background())
	}()
	return s.httpSrv.ListenAndServe()
}

// ServeMetrics blocks until ctx is canceled.
func (s *Server) ServeMetrics(ctx context.Context) error {
	s.logger.Info("metrics server listening", "addr", s.metricsSrv.Addr)
	go func() {
		<-ctx.Done()
		_ = s.metricsSrv.Shutdown(context.Background())
	}()
	return s.metricsSrv.ListenAndServe()
}

// Shutdown drains both servers within ctx deadline.
func (s *Server) Shutdown(ctx context.Context) error {
	var errs []error
	if err := s.httpSrv.Shutdown(ctx); err != nil {
		errs = append(errs, err)
	}
	if err := s.metricsSrv.Shutdown(ctx); err != nil {
		errs = append(errs, err)
	}
	if len(errs) > 0 {
		return fmt.Errorf("shutdown errors: %v", errs)
	}
	return nil
}

// ReloadConfig hot-reloads the provider routing config (DRD GW-015).
// Auth/ratelimit do not reload — they read live from Redis.
func (s *Server) ReloadConfig() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	rt, err := router.LoadFromFile(s.cfg.ProviderConfigPath)
	if err != nil {
		return err
	}
	s.router.Swap(rt)
	s.logger.Info("provider config reloaded")
	return nil
}
