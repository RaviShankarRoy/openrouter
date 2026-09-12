"""Map DomainError subclasses to the OpenAI-format error envelope.

Wire shape per shared/openapi/openapi.yaml#/components/schemas/Error:
    { "error": { "message": ..., "type": ..., "code": ..., "param": ... } }
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.logging import get_logger
from app.service.domain.errors import DomainError

_log = get_logger(__name__)


def _envelope(message: str, error_type: str, code: str, param: str | None = None) -> dict:
    body: dict = {"message": message, "type": error_type, "code": code}
    if param is not None:
        body["param"] = param
    return {"error": body}


def register_exception_handlers(app: FastAPI) -> None:
    """Wire FastAPI to translate every error into the OpenAI envelope."""

    @app.exception_handler(DomainError)
    async def _domain_handler(_: Request, exc: DomainError) -> JSONResponse:
        # Domain errors are expected — log at info, not error.
        _log.info("domain_error", code=exc.code, message=str(exc))
        return JSONResponse(
            status_code=exc.http_status,
            content=_envelope(str(exc) or exc.code, "invalid_request_error", exc.code),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        param = ".".join(str(p) for p in first.get("loc", []))
        return JSONResponse(
            status_code=422,
            content=_envelope(
                first.get("msg", "Invalid request"),
                "invalid_request_error",
                "validation_error",
                param=param or None,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(str(exc.detail), "invalid_request_error", f"http_{exc.status_code}"),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces or internal class names to clients.
        _log.exception("unhandled_exception", exc_class=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=_envelope("Internal server error", "server_error", "internal_error"),
        )
