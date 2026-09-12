"""Async gRPC server bootstrap (DRD PY-019).

Registers AuthService (auth.proto) and RoutingService (routing.proto). The
generated stubs live in `app.repository.grpc.gen.*` and are produced by
`make proto`. We import the servicers lazily so this module loads even before
codegen has run (e.g. in unit tests that don't need gRPC).
"""
from __future__ import annotations

import grpc
from grpc.aio import Server

from app.shared.config import settings
from app.shared.logging import get_logger

_log = get_logger(__name__)

_MAX_MESSAGE_BYTES = 16 * 1024 * 1024  # 16 MB; sufficient for vision payloads


async def create_server() -> Server:
    """Build a configured but unstarted gRPC server.

    Caller is responsible for `await server.start()` and `await server.wait_for_termination()`.
    """
    server = grpc.aio.server(
        options=[
            ("grpc.max_send_message_length", _MAX_MESSAGE_BYTES),
            ("grpc.max_receive_message_length", _MAX_MESSAGE_BYTES),
        ]
    )
    _register_servicers(server)
    bind_addr = f"[::]:{settings.backend_grpc_port}"
    server.add_insecure_port(bind_addr)
    _log.info("grpc_server_configured", bind=bind_addr)
    return server


def _register_servicers(server: Server) -> None:
    """Wire generated servicers. Imports are lazy so unit tests don't need codegen."""
    try:
        from app.repository.grpc.auth_servicer import AuthServicer
        from app.repository.grpc.gen.auth.v1 import auth_pb2_grpc  # type: ignore[import-not-found]

        auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServicer(), server)
    except ImportError:
        # Codegen not present yet — log and continue. Run `make proto` to generate.
        _log.warning("grpc_auth_stubs_missing", action="run `make proto`")

    try:
        from app.repository.grpc.gen.routing.v1 import routing_pb2_grpc  # type: ignore[import-not-found]
        from app.repository.grpc.routing_servicer import RoutingServicer

        routing_pb2_grpc.add_RoutingServiceServicer_to_server(RoutingServicer(), server)
    except ImportError:
        _log.warning("grpc_routing_stubs_missing", action="run `make proto`")
