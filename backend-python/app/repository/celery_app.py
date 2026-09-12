"""Celery application — durable async jobs (video, webhooks, billing aggregation).

Pattern: Task Queue. Tasks live in submodules and are auto-discovered.
"""
from __future__ import annotations

from celery import Celery

from app.shared.config import settings

celery_app = Celery(
    "openrouter",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.repository.tasks.video",
        "app.repository.tasks.webhooks",
        "app.repository.tasks.billing",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retries with jitter — DRD doesn't specify but it's standard hygiene.
    task_default_retry_delay=10,
    task_max_retries=3,
)
