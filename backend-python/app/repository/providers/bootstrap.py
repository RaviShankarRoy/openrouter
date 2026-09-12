"""Provider registration entry point. Imported once at app startup."""
from __future__ import annotations

from app.repository.providers.anthropic_adapter import AnthropicAdapter
from app.repository.providers.gemma_adapter import GemmaAdapter
from app.repository.providers.openai_adapter import OpenAIAdapter
from app.repository.providers.qwen_adapter import QwenAdapter
from app.repository.providers.registry import ProviderRegistry


def register_providers() -> None:
    """Register all built-in adapters. Call from app.main lifespan startup."""
    registry = ProviderRegistry.instance()
    registry.register(OpenAIAdapter())
    registry.register(AnthropicAdapter())
    registry.register(GemmaAdapter())
    registry.register(QwenAdapter())
    # Phase 2-4: register google, mistral, cohere, groq, deepseek,
    # replicate, perplexity, bytedance, ollama, cerebras, hf.
