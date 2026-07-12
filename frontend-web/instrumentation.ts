// Loaded automatically by Next.js 15 on server boot.
//
// OTel is opt-in: enable by setting OTEL_ENABLED=true in env. Disabled by
// default so dev doesn't require @vercel/otel + @opentelemetry/api-logs.
// Production deployments install the peers and flip the flag.
//
// The import is wrapped in eval() to keep Turbopack from statically analyzing
// it — if it analyzed, missing peers would fail the dev build.
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  if (process.env.OTEL_ENABLED !== "true") return;

  try {
    // Indirect dynamic import so the bundler doesn't try to resolve it.
    const mod: { registerOTel: (opts: object) => void } = await (0, eval)(
      'import("@vercel/otel")',
    );
    mod.registerOTel({
      serviceName: process.env.OTEL_SERVICE_NAME ?? "frontend-web",
      instrumentationConfig: {
        fetch: { propagateContextUrls: ["*"] },
      },
    });
  } catch (err) {
    console.warn("[otel] failed to initialize", err);
  }
}
