"""HTTP middleware — request_id, structured logging, OTel auto-instrument.

CORS is registered in app.main to keep config closer to the composition root.
"""
from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

_REQUEST_ID_HEADER = "x-request-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Stamp every request with an ID and bind it to structlog contextvars.

    Keeps the request_id, method, path, and (when present) the trace_id from
    the upstream tracer in every log line for the duration of the request.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(_REQUEST_ID_HEADER) or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            get_logger(__name__).exception("unhandled_request_error")
            raise
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response.headers[_REQUEST_ID_HEADER] = request_id
        # Hot-path metric line — keep it terse and cardinality-bounded.
        get_logger(__name__).info(
            "request_completed",
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response


def register_middleware(app: FastAPI) -> None:
    """Register HTTP middleware + auto-instrument FastAPI/SQLAlchemy with OTel.

    Order matters: the request-context middleware must run first so subsequent
    middlewares see the bound logger context.
    """
    app.add_middleware(RequestContextMiddleware)
    # OTel auto-instruments after middleware add (startup-time).
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(enable_commenter=True)
