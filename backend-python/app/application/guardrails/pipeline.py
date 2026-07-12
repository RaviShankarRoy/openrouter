"""Guardrails pipeline — Chain of Responsibility for input/output validation.

Implements DRD §14.3 design verbatim. Each guard is independently testable
and can be enabled per-org via policy.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    blocked: bool
    rule: str | None = None
    detail: str | None = None
    redacted_text: str | None = None  # If set, replaces the original input

    @classmethod
    def passed(cls) -> "GuardrailResult":
        return cls(blocked=False)


class Guardrail(ABC):
    """Abstract guard. Implementations are pure async functions of the payload."""

    name: str

    @abstractmethod
    async def check(self, payload: str) -> GuardrailResult: ...


class GuardrailPipeline:
    """Ordered chain. First blocking guard short-circuits the rest."""

    def __init__(self, input_guards: list[Guardrail], output_guards: list[Guardrail]) -> None:
        self._input = input_guards
        self._output = output_guards

    async def check_input(self, text: str) -> GuardrailResult:
        return await self._run(text, self._input)

    async def check_output(self, text: str) -> GuardrailResult:
        return await self._run(text, self._output)

    @staticmethod
    async def _run(text: str, guards: list[Guardrail]) -> GuardrailResult:
        current = text
        for guard in guards:
            result = await guard.check(current)
            if result.blocked:
                return result
            if result.redacted_text is not None:
                current = result.redacted_text
        if current != text:
            return GuardrailResult(blocked=False, redacted_text=current)
        return GuardrailResult.passed()
