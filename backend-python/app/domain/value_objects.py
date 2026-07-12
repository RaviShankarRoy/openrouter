"""Immutable value objects. Frozen dataclasses for hashability + equality."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    """Money in USD with up to 6 decimal places (per-token cost)."""

    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money cannot be negative")

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Money subtraction yielded negative")
        return Money(result)

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal("0"))


@dataclass(frozen=True, slots=True)
class TokenCounts:
    """Per-request token usage."""

    input: int = 0
    output: int = 0
    cached_input: int = 0
    reasoning: int = 0

    @property
    def total(self) -> int:
        return self.input + self.output + self.reasoning


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Per-million-token pricing for a model."""

    input_per_million: Decimal
    output_per_million: Decimal
    cached_input_per_million: Decimal | None = None
    reasoning_per_million: Decimal | None = None

    def cost(self, tokens: TokenCounts) -> Money:
        m = Decimal("1000000")
        total = (
            (Decimal(tokens.input) * self.input_per_million / m)
            + (Decimal(tokens.output) * self.output_per_million / m)
        )
        if tokens.cached_input and self.cached_input_per_million is not None:
            total += Decimal(tokens.cached_input) * self.cached_input_per_million / m
        if tokens.reasoning and self.reasoning_per_million is not None:
            total += Decimal(tokens.reasoning) * self.reasoning_per_million / m
        return Money(total)
