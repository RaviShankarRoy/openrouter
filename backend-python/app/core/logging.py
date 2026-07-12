"""Structlog configuration — JSON in prod, pretty in dev.

Per ARCHITECTURE.md §2.2: JSON, UTC, never log secrets.
"""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(environment: str, level: str) -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if environment == "dev":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.extend(
            [
                _scrub_sensitive_fields,
                structlog.processors.JSONRenderer(),
            ]
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_SENSITIVE_KEYS = {
    "api_key",
    "password",
    "secret",
    "token",
    "authorization",
    "x-api-key",
    "stripe_api_key",
}


def _scrub_sensitive_fields(_, __, event_dict: dict) -> dict:
    """Last line of defense — never let credentials reach logs."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
