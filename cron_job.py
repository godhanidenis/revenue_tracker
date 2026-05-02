"""
cron_job.py
Fetches previous day's AdMob and Google Ads data and stores in database.
Run by cron once a day — executes and exits.

Crontab:
    30 19 * * * cd /home/flyontech/revenue_tracker && /home/flyontech/revenue_tracker/venv/bin/python3 cron_job.py
"""

import argparse
import logging
from datetime import date, datetime, timedelta

import pytz

from config import TIMEZONE
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", nargs=2, metavar=("START", "END"))
    args = parser.parse_args()

    init_db()

    if args.backfill:
        start   = date.fromisoformat(args.backfill[0])
        end     = date.fromisoformat(args.backfill[1])
        current = start
        while current <= end:
            fetch_for_date(current)
            current += timedelta(days=1)
        logger.info("Backfill complete.")
    else:
        tz        = pytz.timezone(TIMEZONE)
        yesterday = datetime.now(tz).date() - timedelta(days=1)
        fetch_for_date(yesterday)
        logger.info("Done.")
