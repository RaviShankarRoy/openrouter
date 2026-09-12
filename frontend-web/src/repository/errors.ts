// OpenAI-compatible error envelope (ARCHITECTURE.md §2.5).
// We map wire shape → DomainError for the UI layer to switch on.

export type ErrorEnvelope = {
  error: {
    message: string;
    type: string;
    code?: string;
    param?: string;
  };
};

export type DomainErrorKind =
  | "bad_request"
  | "unauthorized"
  | "insufficient_credits"
  | "rate_limited"
  | "providers_unavailable"
  | "not_found"
  | "server_error"
  | "network";

export class DomainError extends Error {
  readonly kind: DomainErrorKind;
  readonly status: number;
  readonly code: string | undefined;
  readonly param: string | undefined;
  readonly retryAfterSeconds: number | undefined;

  constructor(
    kind: DomainErrorKind,
    status: number,
    message: string,
    opts: { code?: string; param?: string; retryAfterSeconds?: number } = {},
  ) {
    super(message);
    this.name = "DomainError";
    this.kind = kind;
    this.status = status;
    this.code = opts.code;
    this.param = opts.param;
    this.retryAfterSeconds = opts.retryAfterSeconds;
  }
}

const STATUS_TO_KIND: Record<number, DomainErrorKind> = {
  400: "bad_request",
  401: "unauthorized",
  402: "insufficient_credits",
  404: "not_found",
  429: "rate_limited",
  503: "providers_unavailable",
};

export async function fromResponse(response: Response): Promise<DomainError> {
  const kind: DomainErrorKind =
    STATUS_TO_KIND[response.status] ?? (response.status >= 500 ? "server_error" : "bad_request");
  const retryAfter = response.headers.get("Retry-After");
  const retryAfterSeconds = retryAfter ? Number.parseInt(retryAfter, 10) : undefined;

  let message = response.statusText || "Request failed";
  let code: string | undefined;
  let param: string | undefined;
  try {
    const body = (await response.clone().json()) as Partial<ErrorEnvelope>;
    if (body?.error?.message) message = body.error.message;
    code = body?.error?.code;
    param = body?.error?.param;
  } catch {
    // body wasn't JSON — keep statusText
  }

  return new DomainError(kind, response.status, message, {
    code,
    param,
    retryAfterSeconds: Number.isFinite(retryAfterSeconds) ? retryAfterSeconds : undefined,
  });
}

export function isDomainError(error: unknown): error is DomainError {
  return error instanceof DomainError;
}
