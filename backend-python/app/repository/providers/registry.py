"""Provider registry — Factory + Registry pattern.

Adapters self-register at import time. Lookup by provider name is O(1).
"""
from __future__ import annotations

from app.repository.providers.base import ProviderAdapter


class ProviderRegistry:
    """Singleton registry. Modules register on import."""

    _instance: "ProviderRegistry | None" = None

    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    @classmethod
    def instance(cls) -> "ProviderRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, adapter: ProviderAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> ProviderAdapter:
        if name not in self._adapters:
            raise KeyError(f"Provider not registered: {name}")
        return self._adapters[name]

    def names(self) -> list[str]:
        return sorted(self._adapters.keys())
