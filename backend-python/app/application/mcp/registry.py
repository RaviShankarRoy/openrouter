"""Tool registry + federated OAuth (MCP-006, MCP-007, MCP-008).

Phase-4 stub. Production:
  - persists registered tool servers per-org
  - enforces per-key tool filtering policy (MCP-008)
  - handles OAuth 2.0 + PKCE flows and token refresh (MCP-006)
  - on-behalf-of: forwards user identity to downstream tool calls (MCP-007)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.application.mcp.client import MCPServerEndpoint


@dataclass
class RegisteredToolServer:
    org_id: UUID
    name: str
    endpoint: MCPServerEndpoint
    allowed_for_keys: set[UUID] = field(default_factory=set)  # empty == all


class ToolRegistry:
    """In-memory registry. Phase-4 swaps to DB-backed."""

    def __init__(self) -> None:
        self._by_org: dict[UUID, list[RegisteredToolServer]] = {}

    def register(self, server: RegisteredToolServer) -> None:
        self._by_org.setdefault(server.org_id, []).append(server)

    def list_for_key(self, org_id: UUID, key_id: UUID) -> list[RegisteredToolServer]:
        servers = self._by_org.get(org_id, [])
        return [
            s for s in servers if not s.allowed_for_keys or key_id in s.allowed_for_keys
        ]


class FederatedAuthBroker:
    """OAuth token vault for tool servers (Phase-4 stub)."""

    async def acquire_token(self, org_id: UUID, server_name: str, user_id: UUID) -> str:
        # Phase-4: PKCE flow + refresh.
        return ""

    async def refresh(self, org_id: UUID, server_name: str) -> None:
        # Phase-4: rotate token using stored refresh_token.
        return None
