"""Standalone gRPC server entrypoint.

Runs the gRPC servicers (AuthService, RoutingService) as their own process,
independent of the FastAPI HTTP workers. In production this is a separate
k8s Deployment so HTTP workers can scale on RPS while gRPC scales on
auth-cache-miss volume.

Run via:
    python -m app.grpc_main
or:
    make -C backend-python grpc-serve
"""
from __future__ import annotations

import asyncio
import signal

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.tracing import init_tracing
from app.infrastructure.database import close_db, init_db
from app.infrastructure.grpc.server import create_server
from app.infrastructure.redis_client import close_redis, init_redis

_log = get_logger(__name__)


async def _serve() -> None:
    configure_logging(settings.environment, settings.log_level)
    init_tracing(settings)
    await init_db(settings)
    await init_redis(settings)

    server = await create_server()
    await server.start()
    _log.info("grpc_server_started", port=settings.backend_grpc_port)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        _log.info("grpc_server_stopping")
        await server.stop(grace=5.0)
        await close_redis()
        await close_db()
        _log.info("grpc_server_stopped")


def main() -> None:
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
