import { clientEnv } from "@/service/config/env";
import { fromResponse } from "@/repository/errors";

// OTel API is loaded lazily so we don't import it on the client bundle when
// instrumentation is disabled (e.g. local dev without an OTLP endpoint).
type TraceCarrier = Record<string, string>;
async function injectTraceContext(): Promise<TraceCarrier> {
  if (typeof window !== "undefined") return {};
  try {
    // Non-literal specifier: @opentelemetry/api is only present when the
    // OTel peer deps are installed, and pnpm does not hoist transitives.
    const spec = "@opentelemetry/api";
    const { context, propagation } = (await import(spec)) as {
      context: { active(): unknown };
      propagation: { inject(ctx: unknown, carrier: TraceCarrier): void };
    };
    const carrier: TraceCarrier = {};
    propagation.inject(context.active(), carrier);
    return carrier;
  } catch {
    return {};
  }
}

// Repository-pattern transport. Features import generated typed methods that
// call into this client; they never hit `fetch` directly.
//
// - Auth: server-side requests inject the user's session bearer; client-side
//   requests rely on the BFF route at /api/proxy/* to attach credentials.
// - Retry: idempotent verbs only, exponential backoff with jitter, capped at 3.
// - OTel: propagates W3C traceparent so the gateway span chains correctly.

export type RequestOptions = RequestInit & {
  retries?: number;
  signal?: AbortSignal;
  bearerToken?: string;
};

const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);
const IDEMPOTENT_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiClient {
  constructor(private readonly baseUrl: string = clientEnv.NEXT_PUBLIC_API_BASE_URL) {}

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { retries = 2, bearerToken, headers, signal, ...rest } = options;
    const url = new URL(path.replace(/^\//, ""), this.baseUrl.endsWith("/") ? this.baseUrl : `${this.baseUrl}/`);

    const traceCarrier = await injectTraceContext();

    const init: RequestInit = {
      ...rest,
      headers: {
        accept: "application/json",
        "content-type": "application/json",
        ...(bearerToken ? { authorization: `Bearer ${bearerToken}` } : {}),
        ...traceCarrier,
        ...(headers as Record<string, string> | undefined),
      },
      signal: signal ?? AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
    };

    const method = (init.method ?? "GET").toUpperCase();
    const allowRetry = IDEMPOTENT_METHODS.has(method);

    let attempt = 0;
    // Retries only for idempotent verbs on transient failures.
    while (true) {
      const response = await fetch(url, init);
      if (response.ok) return await this.parse<T>(response);
      if (!allowRetry || !RETRYABLE_STATUS.has(response.status) || attempt >= retries) {
        throw await fromResponse(response);
      }
      await delay(backoffMs(attempt));
      attempt += 1;
    }
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "POST", body: body ? JSON.stringify(body) : undefined });
  }
  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "PATCH", body: body ? JSON.stringify(body) : undefined });
  }
  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }

  private async parse<T>(response: Response): Promise<T> {
    if (response.status === 204) return undefined as T;
    const ct = response.headers.get("content-type") ?? "";
    if (ct.includes("application/json")) return (await response.json()) as T;
    return (await response.text()) as unknown as T;
  }
}

function backoffMs(attempt: number): number {
  const base = 250 * 2 ** attempt;
  return base + Math.random() * 100;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Browser-side singleton points at the BFF (/api/proxy/*) so cookies, not
// bearer tokens, drive auth.
export const apiClient = new ApiClient(
  typeof window === "undefined" ? clientEnv.NEXT_PUBLIC_API_BASE_URL : "/api/proxy",
);
