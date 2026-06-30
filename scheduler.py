"""
APScheduler-based scheduler for the Regulatory Arbitrage Scanner.

Schedule:
  - Scrape + analyze: every 12 hours
  - Regenerate dashboard: every 6 hours
  - Send email digest: every Monday at 07:00 local time
"""

import logging
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def job_scrape_and_analyze():
    log.info("=== Scheduled: scrape + analyze ===")
    try:
        from db.database import init_db
        from main import run_scrapers, run_analyzer
        init_db()
        run_scrapers()
        run_analyzer()
    except Exception as e:
        log.error(f"scrape+analyze job failed: {e}", exc_info=True)


def job_dashboard():
    log.info("=== Scheduled: dashboard regeneration ===")
    try:
        from delivery.dashboard import generate_dashboard
        generate_dashboard()
    except Exception as e:
        log.error(f"dashboard job failed: {e}", exc_info=True)


def job_email_digest():
    log.info("=== Scheduled: weekly email digest ===")
    try:
        from db.database import get_processed
        from delivery.email import send_digest
        processed = get_processed(limit=50)
        send_digest(processed, top_n=5)
    except Exception as e:
        log.error(f"email digest job failed: {e}", exc_info=True)


def start():
    scheduler = BlockingScheduler(timezone="America/New_York")

    # Scrape + analyze every 12 hours
    scheduler.add_job(
        job_scrape_and_analyze,
        trigger=IntervalTrigger(hours=12),
        id="scrape_analyze",
        name="Scrape and Analyze",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Regenerate dashboard every 6 hours
    scheduler.add_job(
        job_dashboard,
        trigger=IntervalTrigger(hours=6),
        id="dashboard",
        name="Dashboard Regeneration",
        replace_existing=True,
        misfire_grace_time=1800,
    )

    # Email digest every Monday at 07:00
    scheduler.add_job(
        job_email_digest,
        trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="email_digest",
        name="Weekly Email Digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    log.info("Scheduler started.")
    log.info("  - Scrape + Analyze: every 12 hours")
    log.info("  - Dashboard: every 6 hours")
    log.info("  - Email Digest: Mondays at 07:00")

    # Run scrape+analyze immediately on startup
    log.info("Running initial scrape + analyze on startup...")
    job_scrape_and_analyze()
    job_dashboard()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    start()