"""MCP server — exposes gateway capabilities as MCP tools (DRD MCP-001, §15.3).

Phase-4 stub. The class shape is the public contract; bodies will be filled
when the `mcp` SDK lands. Three transports are required (MCP-003): Streamable
HTTP, SSE, stdio. Only the tool-handler interface is sketched here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.shared.logging import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class MCPTool:
    """A registered tool. `handler` is async; `schema` is JSON Schema."""

    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class MCPServer:
    """Skeleton MCP server. Exposes chat_completion / list_models / generate_image.

    DRD §15.3 requires verbatim tool names so that any MCP-compliant client can
    call them. The tool implementations delegate back into the FastAPI route
    handlers via the in-process service layer (no extra HTTP hop).
    """

    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}
        self._register_builtins()

    def register(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool
        _log.info("mcp_tool_registered", name=tool.name)

    async def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name not in self._tools:
            raise KeyError(f"Unknown MCP tool: {name}")
        return await self._tools[name].handler(args)

    def list_tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    def _register_builtins(self) -> None:
        self.register(
            MCPTool(
                name="chat_completion",
                description="Generate a chat completion via the gateway.",
                schema={
                    "type": "object",
                    "required": ["model", "messages"],
                    "properties": {
                        "model": {"type": "string"},
                        "messages": {"type": "array"},
                        "stream": {"type": "boolean"},
                    },
                },
                handler=_phase4_stub("chat_completion"),
            )
        )
        self.register(
            MCPTool(
                name="list_models",
                description="List available models with pricing.",
                schema={"type": "object", "properties": {}},
                handler=_phase4_stub("list_models"),
            )
        )
        self.register(
            MCPTool(
                name="generate_image",
                description="Generate an image from a prompt.",
                schema={
                    "type": "object",
                    "required": ["model", "prompt"],
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                        "size": {"type": "string"},
                    },
                },
                handler=_phase4_stub("generate_image"),
            )
        )


def _phase4_stub(tool_name: str) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    async def _handler(_: dict[str, Any]) -> dict[str, Any]:
        return {"error": "not_implemented", "tool": tool_name, "phase": 4}

    return _handler
