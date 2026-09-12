"""Video generation pipeline (DRD §8.3).

Three-stage flow, each as a Celery task:
  submit_video_generation → poll_video_status → finalize_video

Bodies are Phase-3 stubs. Signatures are stable so callers (the Go gateway and
the FastAPI route at /v1/videos) can wire against them today.
"""
from __future__ import annotations

from typing import Any

from celery import Task

from app.shared.logging import get_logger
from app.repository.celery_app import celery_app

_log = get_logger(__name__)


@celery_app.task(
    name="video.submit_video_generation",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def submit_video_generation(self: Task, job_id: str, model: str, prompt: str, options: dict) -> str:
    """Submit a generation request to the chosen video provider.

    Returns the provider's job/operation ID for subsequent polling.
    """
    _log.info("video_submit", job_id=job_id, model=model, attempt=self.request.retries)
    # Phase-3: provider adapter (luma/kling/runway/sora) submits the job.
    return f"provider-job-{job_id}"


@celery_app.task(
    name="video.poll_video_status",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=120,  # ~2h with backoff cap
)
def poll_video_status(self: Task, job_id: str, provider_job_id: str) -> dict[str, Any]:
    """Poll provider for status. Re-enqueues itself until terminal."""
    _log.info("video_poll", job_id=job_id, provider_job_id=provider_job_id)
    # Phase-3: real polling. For now, fake a single completed status.
    return {"job_id": job_id, "status": "completed", "provider_urls": []}


@celery_app.task(
    name="video.finalize_video",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5,
)
def finalize_video(self: Task, job_id: str, provider_urls: list[str]) -> list[str]:
    """Download from provider, upload to S3, return signed URLs (24h TTL — DRD §8.3)."""
    _log.info("video_finalize", job_id=job_id, count=len(provider_urls))
    # Phase-3: stream-download + s3 upload + signed URL generation.
    return [f"s3://openrouter-media/videos/{job_id}/{i}.mp4" for i, _ in enumerate(provider_urls)]
