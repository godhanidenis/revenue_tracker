"""
cron_job.py

Runs as a background process. Every day at FETCH_HOUR:FETCH_MINUTE
it pulls the previous day's data from AdMob and Google Ads, then
stores it in the database.

Usage:
    python cron_job.py            # runs forever (use systemd / pm2 / nohup)
    python cron_job.py --backfill 2024-01-01 2024-03-31   # backfill a range
"""

import argparse
import logging
import sys
from datetime import date, datetime, timedelta

import pytz
import schedule
import time

from config import FETCH_HOUR, FETCH_MINUTE, TIMEZONE
from database import init_db, upsert_admob, upsert_google_ads, log_fetch
from fetchers import fetch_admob_day, fetch_google_ads_day

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("cron")


def fetch_for_date(target: date):
    logger.info(f"Fetching data for {target} …")

    # ── AdMob ──────────────────────────────────────────────────────────
    try:
        from database import get_currency_config
        cfg    = get_currency_config()
        app_id = cfg.get("admob_app_id", "ALL")
        admob_data = fetch_admob_day(target, app_id=app_id)
        upsert_admob(admob_data)
        log_fetch(target, "admob", "success")
        logger.info(f"  AdMob ✓  revenue={admob_data['estimated_earnings']:.4f} app={app_id}")
    except Exception as e:
        log_fetch(target, "admob", "error", str(e))
        logger.error(f"  AdMob ✗  {e}")

    # ── Google Ads ──────────────────────────────────────────────────────
    try:
        gads_data = fetch_google_ads_day(target)
        upsert_google_ads(gads_data)
        log_fetch(target, "google_ads", "success")
        logger.info(f"  Google Ads ✓  spend={gads_data['cost']:.4f}")
    except Exception as e:
        log_fetch(target, "google_ads", "error", str(e))
        logger.error(f"  Google Ads ✗  {e}")


def daily_job():
    tz = pytz.timezone(TIMEZONE)
    yesterday = datetime.now(tz).date() - timedelta(days=1)
    fetch_for_date(yesterday)


def backfill(start_str: str, end_str: str):
    start = date.fromisoformat(start_str)
    end   = date.fromisoformat(end_str)
    current = start
    while current <= end:
        fetch_for_date(current)
        current += timedelta(days=1)
    logger.info("Backfill complete.")


def main():
    parser = argparse.ArgumentParser(description="AdMob + Google Ads data fetcher")
    parser.add_argument("--backfill", nargs=2, metavar=("START", "END"),
                        help="Backfill date range YYYY-MM-DD YYYY-MM-DD")
    args = parser.parse_args()

    init_db()
    logger.info("Database initialised.")

    if args.backfill:
        backfill(*args.backfill)
        sys.exit(0)

    fetch_time = f"{FETCH_HOUR:02d}:{FETCH_MINUTE:02d}"
    logger.info(f"Scheduler started — will fetch daily at {fetch_time} ({TIMEZONE})")

    schedule.every().day.at(fetch_time).do(daily_job)

    # Also run once immediately if no data for yesterday
    daily_job()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()