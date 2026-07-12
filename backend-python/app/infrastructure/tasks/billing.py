"""Billing background tasks — daily aggregation, low-balance alerts (DRD §12.4)."""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from celery import Task
from sqlalchemy import text

from app.core.logging import get_logger
from app.infrastructure.celery_app import celery_app
from app.infrastructure.database import get_session_factory

_log = get_logger(__name__)

# Threshold below which we notify org owners. Tuned per-DRD; 5 USD is a
# placeholder until per-org policies land in Phase 2.
_LOW_BALANCE_USD = 5.00


@celery_app.task(name="billing.aggregate_daily_usage", bind=True, max_retries=3)
def aggregate_daily_usage(self: Task, day_iso: str | None = None) -> int:
    """Roll yesterday's per-org usage into a daily summary table.

    Returns the number of org rows aggregated. The summary table is created
    in the next phase (`usage_daily`); this task is a placeholder that runs
    a no-op aggregate query so the schedule is wired today.
    """
    target_day = date.fromisoformat(day_iso) if day_iso else (datetime.now(UTC).date() - timedelta(days=1))
    start = datetime.combine(target_day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    factory = get_session_factory()

    async def _run() -> int:
        async with factory() as session:
            stmt = text(
                """
                SELECT org_id, COUNT(*) AS req, COALESCE(SUM(cost_usd),0) AS cost
                FROM usage_records
                WHERE created_at >= :start AND created_at < :end
                GROUP BY org_id
                """
            )
            rows = (await session.execute(stmt, {"start": start, "end": end})).all()
            return len(rows)

    import asyncio

    count = asyncio.run(_run())
    _log.info("billing_aggregated", day=str(target_day), org_count=count)
    return count


@celery_app.task(name="billing.send_low_balance_alert", bind=True, max_retries=3)
def send_low_balance_alert(self: Task, org_id: str, available_usd: float) -> bool:
    """Notify the org that their balance is low (DRD §12.5)."""
    if available_usd >= _LOW_BALANCE_USD:
        return False
    _log.info("low_balance_alert", org_id=org_id, available_usd=available_usd)
    # Phase-2: enqueue email / dashboard notification. Stub returns success.
    return True
