"""APScheduler configuration for periodic ETL runs.

Schedules the ETL pipeline to run at configured intervals
(default: every 6 hours, starting at 06:00 CET).
"""

from config.settings import settings


def start_scheduler() -> None:
    """Start the APScheduler background scheduler.

    Registers the ETL pipeline as a cron job running at the
    interval defined by settings.fetch_interval_hours.
    """
    # TODO: Implement in Phase 2
    # from apscheduler.schedulers.asyncio import AsyncIOScheduler
    # from src.pipeline.etl import run_pipeline
    #
    # scheduler = AsyncIOScheduler(timezone="Europe/Amsterdam")
    # scheduler.add_job(
    #     run_pipeline,
    #     trigger="cron",
    #     hour=f"*/{settings.fetch_interval_hours}",
    #     id="etl_pipeline",
    #     replace_existing=True,
    # )
    # scheduler.start()
    raise NotImplementedError("Scheduler not yet implemented")
