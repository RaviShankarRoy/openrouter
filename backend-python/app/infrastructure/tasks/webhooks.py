"""Outbound webhook delivery — durable, retried, signed."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx
from celery import Task

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.celery_app import celery_app

_log = get_logger(__name__)


@celery_app.task(
    name="webhooks.deliver",
    bind=True,
    autoretry_for=(httpx.HTTPError, httpx.TimeoutException),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
    max_retries=10,
)
def deliver_webhook(
    self: Task,
    url: str,
    event_type: str,
    payload: dict[str, Any],
    secret: str | None = None,
) -> int:
    """Deliver a JSON webhook with HMAC signature header.

    Retries with exponential backoff up to ~10h. The receiver should be
    idempotent (DRD generally favours at-least-once delivery for webhooks).
    """
    body = json.dumps({"type": event_type, "data": payload, "ts": int(time.time())}).encode()
    headers = {"content-type": "application/json", "x-or-event": event_type}
    sign_key = secret or settings.secret_key.get_secret_value()
    headers["x-or-signature"] = hmac.new(sign_key.encode(), body, hashlib.sha256).hexdigest()
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, content=body, headers=headers)
        resp.raise_for_status()
        _log.info(
            "webhook_delivered",
            url=url,
            status=resp.status_code,
            event=event_type,
            attempt=self.request.retries,
        )
        return resp.status_code
