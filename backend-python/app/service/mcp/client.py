"""MCP client — call external MCP tool servers on behalf of an agent (MCP-002).

Phase-4 stub. Contract: `call_tool(server_url, tool, args)` returns the tool's
response payload. Production wires transports (stdio / SSE / Streamable HTTP)
and OAuth token refresh (MCP-006).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.shared.logging import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class MCPServerEndpoint:
    """Where and how to reach an external MCP server."""

    url: str
    transport: str  # "http" | "sse" | "stdio"
    oauth_token: str | None = None


class MCPClient:
    """Phase-4 stub. Calls into external MCP servers."""

    async def list_tools(self, endpoint: MCPServerEndpoint) -> list[dict[str, Any]]:
        _log.info("mcp_client_list_tools", url=endpoint.url, transport=endpoint.transport)
        return []

    async def call_tool(
        self,
        endpoint: MCPServerEndpoint,
        tool: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        _log.info("mcp_client_call_tool", url=endpoint.url, tool=tool)
        return {"error": "not_implemented", "phase": 4}
