import { z } from "zod";

// Two schemas: server vars (full set) and client-exposed `NEXT_PUBLIC_*` only.
// We validate at module load so a misconfigured deployment fails fast.
const serverSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  NEXTAUTH_URL: z.string().url().optional(),
  NEXTAUTH_SECRET: z.string().min(16).optional(),
  GITHUB_CLIENT_ID: z.string().optional(),
  GITHUB_CLIENT_SECRET: z.string().optional(),
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  OTEL_EXPORTER_OTLP_ENDPOINT: z.string().url().optional(),
  OTEL_SERVICE_NAME: z.string().default("frontend-web"),
  STRIPE_SECRET_KEY: z.string().optional(),
});

const clientSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default("http://localhost:8080"),
  NEXT_PUBLIC_BACKEND_URL: z.string().url().default("http://localhost:8000"),
  NEXT_PUBLIC_SERVICE_VERSION: z.string().default("0.1.0"),
  NEXT_PUBLIC_ENVIRONMENT: z.enum(["dev", "staging", "prod"]).default("dev"),
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: z.string().optional(),
});

const isServer = typeof window === "undefined";

export const clientEnv = clientSchema.parse({
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
  NEXT_PUBLIC_SERVICE_VERSION: process.env.NEXT_PUBLIC_SERVICE_VERSION,
  NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY,
});

export const serverEnv = isServer ? serverSchema.parse(process.env) : null;

export type ClientEnv = z.infer<typeof clientSchema>;
export type ServerEnv = z.infer<typeof serverSchema>;
