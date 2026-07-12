// Package observability holds logger, metrics, and tracing bootstrapping.
package observability

import (
	"context"
	"log/slog"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"

	"github.com/openrouter/gateway-go/internal/config"
)

// NewLogger builds a slog.Logger configured for the environment.
// dev → pretty text on stdout. prod → JSON on stdout (Loki-compatible).
func NewLogger(env, level string) *slog.Logger {
	var lvl slog.Level
	_ = lvl.UnmarshalText([]byte(level))
	opts := &slog.HandlerOptions{Level: lvl, AddSource: env == "dev"}
	if env == "dev" {
		return slog.New(slog.NewTextHandler(os.Stdout, opts))
	}
	return slog.New(slog.NewJSONHandler(os.Stdout, opts))
}

// InitTracing wires OTLP/gRPC export to the configured collector.
// Returns a shutdown function callers must defer.
func InitTracing(ctx context.Context, cfg *config.Config) (func(context.Context) error, error) {
	if cfg.OTel.Endpoint == "" {
		return func(context.Context) error { return nil }, nil
	}
	exp, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(stripScheme(cfg.OTel.Endpoint)),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}
	res, _ := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName(cfg.OTel.Service),
			semconv.ServiceVersion(cfg.Version),
			semconv.DeploymentEnvironment(cfg.Environment),
		),
	)
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.TraceIDRatioBased(cfg.OTel.SampleRate))),
	)
	otel.SetTracerProvider(tp)
	return tp.Shutdown, nil
}

func stripScheme(url string) string {
	for i := 0; i+2 < len(url); i++ {
		if url[i] == ':' && url[i+1] == '/' && url[i+2] == '/' {
			return url[i+3:]
		}
	}
	return url
}
