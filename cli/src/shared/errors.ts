// Typed error hierarchy. Exit codes are part of the contract:
//   0 success, 1 user error, 2 server error.
import { logger } from './logger.js';

export type ExitCode = 0 | 1 | 2;

export abstract class CliError extends Error {
  abstract readonly exitCode: ExitCode;
  abstract readonly kind: string;
  override readonly cause?: unknown;

  constructor(message: string, options?: { cause?: unknown }) {
    super(message);
    this.name = this.constructor.name;
    if (options?.cause !== undefined) this.cause = options.cause;
  }
}

export class AuthError extends CliError {
  readonly exitCode: ExitCode = 1;
  readonly kind = 'auth';
}

export class ValidationError extends CliError {
  readonly exitCode: ExitCode = 1;
  readonly kind = 'validation';
}

export class ConfigError extends CliError {
  readonly exitCode: ExitCode = 1;
  readonly kind = 'config';
}

export class NetworkError extends CliError {
  readonly exitCode: ExitCode = 2;
  readonly kind = 'network';
}

export class ServerError extends CliError {
  readonly exitCode: ExitCode = 2;
  readonly kind = 'server';
  readonly status: number;

  constructor(message: string, status: number, options?: { cause?: unknown }) {
    super(message, options);
    this.status = status;
  }
}

export class RateLimitError extends ServerError {
  override readonly kind = 'rate_limit';
  readonly retryAfterSeconds?: number;

  constructor(message: string, retryAfterSeconds?: number) {
    super(message, 429);
    if (retryAfterSeconds !== undefined) this.retryAfterSeconds = retryAfterSeconds;
  }
}

// Friendly user-facing message map. Keep terse: surface tells the user what to *do*.
function friendlyMessage(err: CliError): string {
  switch (err.kind) {
    case 'auth':
      return `${err.message}\n\nTry: openrouter login`;
    case 'rate_limit': {
      const ra = (err as RateLimitError).retryAfterSeconds;
      return ra !== undefined
        ? `${err.message}\nRetry after ${ra}s.`
        : err.message;
    }
    case 'config':
      return `${err.message}\n\nCheck the config file or run with --base-url <url>.`;
    case 'network':
      return `${err.message}\n\nCheck your network connection.`;
    default:
      return err.message;
  }
}

export function exitWithError(err: unknown): never {
  if (err instanceof CliError) {
    process.stderr.write(`error: ${friendlyMessage(err)}\n`);
    if (err.cause !== undefined) {
      logger.debug({ cause: err.cause }, 'error cause');
    }
    process.exit(err.exitCode);
  }
  if (err instanceof Error) {
    process.stderr.write(`error: ${err.message}\n`);
    logger.debug({ stack: err.stack }, 'unhandled error');
    process.exit(2);
  }
  process.stderr.write(`error: ${String(err)}\n`);
  process.exit(2);
}
