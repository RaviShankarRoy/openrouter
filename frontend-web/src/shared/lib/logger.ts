import pino, { type Logger } from "pino";

// Server-side only. ARCHITECTURE.md §2.2: JSON to stdout in prod, pretty in dev.
// Browser logging is intentionally omitted — surface UX errors via toast/sentry,
// not console spam.
const isProd = process.env.NODE_ENV === "production";

export const logger: Logger = pino({
  level: process.env.LOG_LEVEL ?? "info",
  base: {
    service: process.env.OTEL_SERVICE_NAME ?? "frontend-web",
    version: process.env.NEXT_PUBLIC_SERVICE_VERSION ?? "0.1.0",
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: {
    paths: ["req.headers.authorization", "req.headers.cookie", "*.api_key", "*.password"],
    censor: "[REDACTED]",
  },
  ...(isProd
    ? {}
    : {
        transport: {
          target: "pino-pretty",
          options: { colorize: true, translateTime: "SYS:HH:MM:ss.l" },
        },
      }),
});

export function childLogger(bindings: Record<string, unknown>): Logger {
  return logger.child(bindings);
}
