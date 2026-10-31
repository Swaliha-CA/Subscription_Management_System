"""APScheduler background job — runs billing engine daily at 00:05."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_scheduled_billing():
    try:
        from app.services.billing_engine import run_billing
        result = run_billing(run_type="scheduled")
        logger.info(
            "Scheduled billing complete: %d invoices generated, %d failed",
            result["invoices_generated"], result["invoices_failed"],
        )
    except Exception as exc:
        logger.error("Scheduled billing error: %s", exc, exc_info=True)


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(daemon=True, timezone="Asia/Kolkata")
    _scheduler.add_job(
        _run_scheduled_billing,
        trigger=CronTrigger(hour=0, minute=5),
        id="daily_billing",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Billing scheduler started (daily 00:05 IST)")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
