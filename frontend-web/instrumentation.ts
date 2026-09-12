// Loaded automatically by Next.js on server boot.
//
// OTel is opt-in: enable by setting OTEL_ENABLED=true in env. Disabled by
// default so dev doesn't pay for an OTLP exporter nobody is collecting.
//
// The import is a normal dynamic import, evaluated only after the runtime
// guard below. `(0, eval)('import(...)')` cannot be used here: instrumentation.ts
// is compiled for the Edge runtime as well, and Edge bans dynamic code
// evaluation, which fails the production build.
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  if (process.env.OTEL_ENABLED !== "true") return;

  try {
    const { registerOTel } = await import("@vercel/otel");
    registerOTel({
      serviceName: process.env.OTEL_SERVICE_NAME ?? "frontend-web",
      instrumentationConfig: {
        fetch: { propagateContextUrls: ["*"] },
      },
    });
  } catch (err) {
    console.warn("[otel] failed to initialize", err);
  }
}
