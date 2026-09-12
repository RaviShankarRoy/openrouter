"""Domain errors. Map to HTTP status codes in app/api/errors.py."""
from __future__ import annotations


class DomainError(Exception):
    """Base for all expected domain errors. Distinguishes from infra errors."""

    code: str = "domain_error"
    http_status: int = 400


class NotFound(DomainError):
    code = "not_found"
    http_status = 404


class Forbidden(DomainError):
    code = "forbidden"
    http_status = 403


class Conflict(DomainError):
    code = "conflict"
    http_status = 409


class InvalidApiKey(DomainError):
    code = "invalid_api_key"
    http_status = 401


class InsufficientCredits(DomainError):
    code = "insufficient_credits"
    http_status = 402


class BudgetExceeded(DomainError):
    code = "budget_exceeded"
    http_status = 402


class RateLimited(DomainError):
    code = "rate_limit_exceeded"
    http_status = 429


class GuardrailViolation(DomainError):
    code = "guardrail_violation"
    http_status = 400


class ProviderError(DomainError):
    """Upstream provider returned an error we couldn't normalize."""

    code = "provider_error"
    http_status = 502
