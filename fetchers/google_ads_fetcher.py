"""
fetchers/google_ads_fetcher.py

Uses the Google Ads API via google-ads SDK.

IMPORTANT: google-ads==24.0.0 uses v16 which is SUNSET.
Upgrade to latest: pip install --upgrade google-ads
The latest library (25.x+) uses v19 which is current and supported.

Docs: https://developers.google.com/google-ads/api/docs/get-started/introduction
"""
import logging
from datetime import date, datetime

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from config import (
    GOOGLE_ADS_DEVELOPER_TOKEN,
    GOOGLE_ADS_CLIENT_ID,
    GOOGLE_ADS_CLIENT_SECRET,
    GOOGLE_ADS_REFRESH_TOKEN,
    GOOGLE_ADS_CUSTOMER_ID,
)

logger = logging.getLogger(__name__)


def _build_client() -> GoogleAdsClient:
    config = {
        "developer_token":    GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id":          GOOGLE_ADS_CLIENT_ID,
        "client_secret":      GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token":      GOOGLE_ADS_REFRESH_TOKEN,
        "login_customer_id":  GOOGLE_ADS_CUSTOMER_ID,
        "use_proto_plus":     True,
    }
    return GoogleAdsClient.load_from_dict(config)


def fetch_google_ads_day(target_date: date) -> dict:
    """
    Fetch Google Ads spend + metrics for a single day.
    Returns a dict ready to pass to database.upsert_google_ads().
    Raises RuntimeError on API failure.
    """
    client     = _build_client()
    ga_service = client.get_service("GoogleAdsService")
    date_str   = target_date.strftime("%Y-%m-%d")

    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros,
            metrics.clicks,
            metrics.impressions,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM customer
        WHERE segments.date = '{date_str}'
    """

    try:
        response = ga_service.search(
            customer_id=GOOGLE_ADS_CUSTOMER_ID,
            query=query,
        )
    except GoogleAdsException as ex:
        error_msgs = "; ".join(e.message for e in ex.failure.errors)
        raise RuntimeError(
            f"Google Ads API error: {ex.error.code().name} — {error_msgs}"
        )

    cost        = 0.0
    clicks      = 0
    impressions = 0
    conversions = 0.0
    ctr         = 0.0
    avg_cpc     = 0.0

    for row in response:
        m = row.metrics
        cost        += m.cost_micros / 1_000_000
        clicks      += m.clicks
        impressions += m.impressions
        conversions += m.conversions
        ctr          = m.ctr * 100
        avg_cpc      = m.average_cpc / 1_000_000

    return {
        "date":        target_date,
        "cost":        round(cost, 4),
        "clicks":      clicks,
        "impressions": impressions,
        "conversions": round(conversions, 2),
        "ctr":         round(ctr, 4),
        "avg_cpc":     round(avg_cpc, 4),
        "fetched_at":  datetime.utcnow().isoformat(),
    }