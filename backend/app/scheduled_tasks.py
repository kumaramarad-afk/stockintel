from __future__ import annotations

import logging
import sys

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = None


def _build_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    from services.newsletter_service import generate_daily_newsletter
    from services.report_cache import refresh_popular_reports

    job_scheduler = BackgroundScheduler(timezone="UTC")

    def send_daily_newsletter() -> None:
        try:
            result = generate_daily_newsletter()
            logger.info("Newsletter job: %s", result)
        except Exception:
            logger.exception("Daily newsletter job failed")

    def refresh_cached_reports() -> None:
        try:
            result = refresh_popular_reports()
            logger.info("Report cache refresh: %s", result)
        except Exception:
            logger.exception("Weekly report cache refresh failed")

    job_scheduler.add_job(
        send_daily_newsletter,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone="UTC"),
        id="daily-newsletter",
        replace_existing=True,
    )
    job_scheduler.add_job(
        refresh_cached_reports,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="UTC"),
        id="weekly-report-refresh",
        replace_existing=True,
    )
    return job_scheduler


def start_scheduler() -> None:
    global scheduler
    if "pytest" in sys.modules or not settings.newsletter_scheduler_enabled:
        return
    if scheduler is not None and scheduler.running:
        return
    try:
        scheduler = _build_scheduler()
        scheduler.start()
        logger.info("Scheduler started (newsletter + weekly report refresh)")
    except Exception:
        logger.exception("Could not start scheduler")


def stop_scheduler() -> None:
    global scheduler
    if scheduler is None:
        return
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler = None
