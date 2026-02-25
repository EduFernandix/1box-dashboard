"""APScheduler configuration for periodic ETL runs.

Schedules the ETL pipeline to run at configured intervals
(default: every 6 hours). Only starts if API credentials
are configured — safe to run in development with demo data.
"""

import logging

from config.settings import settings

logger = logging.getLogger(__name__)

_scheduler = None


def _has_any_credentials() -> bool:
    """Check if at least one API credential set is configured."""
    has_gads = bool(
        settings.google_ads_developer_token
        and settings.google_ads_refresh_token
    )
    has_ga4 = bool(
        settings.ga4_property_id and settings.google_ads_refresh_token
    )
    return has_gads or has_ga4


def start_scheduler():
    """Start the APScheduler background scheduler.

    Registers the ETL pipeline as a cron job running at the interval
    defined by settings.fetch_interval_hours. Returns the scheduler
    instance, or None if no credentials are configured.
    """
    global _scheduler

    if not _has_any_credentials():
        logger.warning(
            "No API credentials configured. "
            "Scheduler will not start. Use demo data instead."
        )
        return None

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    from src.pipeline.etl import run_pipeline

    _scheduler = AsyncIOScheduler(timezone="Europe/Amsterdam")

    interval = settings.fetch_interval_hours
    hours = ",".join(str(h) for h in range(0, 24, interval))

    _scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=hours, minute="0"),
        id="etl_pipeline",
        name="ETL Pipeline (all sources)",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow up to 1h late execution
    )

    _scheduler.start()
    logger.info(
        f"Scheduler started. Pipeline runs every {interval}h "
        f"at hours: {hours} (Europe/Amsterdam)"
    )
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully stop the scheduler if running."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
        _scheduler = None
