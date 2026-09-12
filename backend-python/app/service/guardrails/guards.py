"""Concrete guardrail implementations. Phase-3 work — these are stubs that
demonstrate the interface so the pipeline class can be tested today.

When implemented:
  - PII via `presidio` (DRD GR-002)
  - injection via `llm-guard` classifier (DRD GR-001)
  - content policy via `guardrails-ai` validators (DRD GR-003)
"""
from __future__ import annotations

import re

from app.service.guardrails.pipeline import Guardrail, GuardrailResult


class TokenLimitGuard(Guardrail):
    """DRD GR-004 — reject if token count exceeds policy."""

    name = "token_limit"

    def __init__(self, max_tokens: int) -> None:
        self._max = max_tokens

    async def check(self, payload: str) -> GuardrailResult:
        # Approximate: 1 token ≈ 4 chars. Production uses tiktoken.
        approx = len(payload) // 4
        if approx > self._max:
            return GuardrailResult(
                blocked=True,
                rule=self.name,
                detail=f"~{approx} tokens exceeds limit {self._max}",
            )
        return GuardrailResult.passed()


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


class PIIRedactionGuard(Guardrail):
    """Phase-3 stub for PII redaction. Real implementation uses presidio."""

    name = "pii_redaction"

    async def check(self, payload: str) -> GuardrailResult:
        redacted = _EMAIL_RE.sub("[EMAIL]", payload)
        redacted = _PHONE_RE.sub("[PHONE]", redacted)
        if redacted == payload:
            return GuardrailResult.passed()
        return GuardrailResult(blocked=False, redacted_text=redacted)


class PromptInjectionGuard(Guardrail):
    """Phase-3 stub. Real impl uses llm-guard classifier."""

    name = "prompt_injection"

    _SUSPICIOUS_PHRASES = (
        "ignore previous instructions",
        "ignore all prior",
        "you are now",
        "system prompt",
    )

    async def check(self, payload: str) -> GuardrailResult:
        lowered = payload.lower()
        for phrase in self._SUSPICIOUS_PHRASES:
            if phrase in lowered:
                return GuardrailResult(
                    blocked=True,
                    rule=self.name,
                    detail=f"Suspicious phrase: {phrase!r}",
                )
        return GuardrailResult.passed()
