// Package main is the entry point for the gateway binary.
// Composition root only — wires concrete adapters into the domain.
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/openrouter/gateway-go/internal/shared/config"
	"github.com/openrouter/gateway-go/internal/shared/observability"
	"github.com/openrouter/gateway-go/internal/api/server"
)

var version = "dev" // injected via -ldflags

func main() {
	if err := run(); err != nil {
		slog.Error("fatal", "err", err)
		os.Exit(1)
	}
}

func run() error {
	// Configuration first — fail fast on bad config.
	cfg, err := config.Load()
	if err != nil {
		return fmt.Errorf("load config: %w", err)
	}

	// Logger — JSON in prod, text in dev.
	logger := observability.NewLogger(cfg.Environment, cfg.LogLevel)
	slog.SetDefault(logger)
	logger.Info("starting gateway", "version", version, "env", cfg.Environment)

	// Tracing.
	shutdownTracer, err := observability.InitTracing(context.Background(), cfg)
	if err != nil {
		return fmt.Errorf("init tracing: %w", err)
	}
	defer shutdownTracer(context.Background())

	// Build the server with all middleware, routing, and proxy wired.
	srv, err := server.New(cfg, logger)
	if err != nil {
		return fmt.Errorf("build server: %w", err)
	}

	// Run HTTP + metrics in parallel; cancel both on first error.
	rootCtx, cancel := context.WithCancel(context.Background())
	defer cancel()

	errCh := make(chan error, 2)
	go func() { errCh <- srv.ServeHTTP(rootCtx) }()
	go func() { errCh <- srv.ServeMetrics(rootCtx) }()

	// Wait for shutdown signal or fatal error.
	signalCh := make(chan os.Signal, 1)
	signal.Notify(signalCh, syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)

	for {
		select {
		case sig := <-signalCh:
			if sig == syscall.SIGHUP {
				logger.Info("SIGHUP received, hot-reloading config")
				if err := srv.ReloadConfig(); err != nil {
					logger.Error("config reload failed", "err", err)
				}
				continue
			}
			logger.Info("shutdown signal received", "signal", sig)
			cancel()
			shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
			defer shutdownCancel()
			if err := srv.Shutdown(shutdownCtx); err != nil {
				logger.Error("graceful shutdown failed", "err", err)
				return err
			}
			return nil
		case err := <-errCh:
			if err != nil && !errors.Is(err, http.ErrServerClosed) {
				return err
			}
		}
	}
}
