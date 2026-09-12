"""Smoke tests for the new Gemma + Qwen adapters.

These don't hit the network — they verify registration, naming, and pricing
lookups so a typo in a model_id surfaces in CI rather than at billing time.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.repository.providers.bootstrap import register_providers
from app.repository.providers.gemma_adapter import GemmaAdapter, _PRICING as GEMMA_PRICING
from app.repository.providers.qwen_adapter import QwenAdapter, _PRICING as QWEN_PRICING
from app.repository.providers.registry import ProviderRegistry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Each test starts with a fresh registry — module-level singleton otherwise leaks."""
    ProviderRegistry._instance = None  # type: ignore[attr-defined]


def test_bootstrap_registers_gemma_and_qwen() -> None:
    register_providers()
    names = ProviderRegistry.instance().names()
    assert "gemma" in names
    assert "qwen" in names


def test_gemma_adapter_identity() -> None:
    a = GemmaAdapter()
    assert a.name == "gemma"
    assert "video" in a.supported_modalities  # multimodal — DRD §7.2


def test_qwen_adapter_identity() -> None:
    a = QwenAdapter()
    assert a.name == "qwen"
    assert a.supported_modalities == ["text"]


@pytest.mark.parametrize(
    "model,expected_input",
    [
        ("google/gemma-4-31b", Decimal("0.30")),
        ("google/gemma-4-26b-moe", Decimal("0.20")),
        ("google/gemma-4-e4b", Decimal("0.05")),
        ("google/gemma-4-e2b", Decimal("0.02")),
    ],
)
def test_gemma_pricing(model: str, expected_input: Decimal) -> None:
    tier = GemmaAdapter().pricing(model)
    assert tier.input_per_million == expected_input


@pytest.mark.parametrize(
    "model,expected_input",
    [
        ("qwen/qwen3.6-27b", Decimal("0.20")),
        ("qwen/qwen3.6-35b-a3b", Decimal("0.27")),
        ("qwen/qwen3.5-35b-a3b", Decimal("0.27")),
        ("qwen/qwen3.5-122b-a10b", Decimal("0.60")),
    ],
)
def test_qwen_pricing(model: str, expected_input: Decimal) -> None:
    tier = QwenAdapter().pricing(model)
    assert tier.input_per_million == expected_input


def test_unknown_model_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        GemmaAdapter().pricing("google/gemma-4-bogus")
    with pytest.raises(KeyError):
        QwenAdapter().pricing("qwen/qwen-imaginary")


def test_pricing_dict_matches_supported_models() -> None:
    """Defensive: every model_id in providers.yaml should have a pricing entry."""
    # These are the model_ids referenced in gateway-go/configs/providers.yaml.
    expected_gemma = {
        "google/gemma-4-31b",
        "google/gemma-4-26b-moe",
        "google/gemma-4-e4b",
        "google/gemma-4-e2b",
    }
    expected_qwen = {
        "qwen/qwen3.6-27b",
        "qwen/qwen3.6-35b-a3b",
        "qwen/qwen3.5-35b-a3b",
        "qwen/qwen3.5-122b-a10b",
    }
    assert set(GEMMA_PRICING.keys()) == expected_gemma
    assert set(QWEN_PRICING.keys()) == expected_qwen
