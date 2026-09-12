"""Tests for Money + ModelPricing.cost — pure value-object behaviour."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.service.domain.value_objects import ModelPricing, Money, TokenCounts


def test_money_rejects_negative() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("-1"))


def test_money_addition_and_subtraction() -> None:
    a = Money(Decimal("1.5"))
    b = Money(Decimal("0.5"))
    assert (a + b).amount == Decimal("2.0")
    assert (a - b).amount == Decimal("1.0")
    with pytest.raises(ValueError):
        b - a


def test_money_zero_factory() -> None:
    assert Money.zero().amount == Decimal("0")


def test_pricing_cost_basic() -> None:
    pricing = ModelPricing(
        input_per_million=Decimal("3.00"),
        output_per_million=Decimal("15.00"),
    )
    cost = pricing.cost(TokenCounts(input=1_000_000, output=1_000_000))
    assert cost.amount == Decimal("18.00")


def test_pricing_cost_with_cached_and_reasoning() -> None:
    pricing = ModelPricing(
        input_per_million=Decimal("10.00"),
        output_per_million=Decimal("30.00"),
        cached_input_per_million=Decimal("1.00"),
        reasoning_per_million=Decimal("60.00"),
    )
    cost = pricing.cost(
        TokenCounts(input=1_000_000, output=500_000, cached_input=500_000, reasoning=100_000)
    )
    # 10 + 15 + 0.5 + 6 = 31.5
    assert cost.amount == Decimal("31.5")


def test_pricing_ignores_cached_when_no_pricing_set() -> None:
    pricing = ModelPricing(
        input_per_million=Decimal("2.00"),
        output_per_million=Decimal("8.00"),
    )
    cost = pricing.cost(TokenCounts(input=1_000_000, output=0, cached_input=999_999_999))
    assert cost.amount == Decimal("2.00")
