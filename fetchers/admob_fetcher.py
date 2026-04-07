"""
fetchers/admob_fetcher.py

Key notes on AdMob API vs Dashboard discrepancies:
- The AdMob Dashboard shows TOTAL earnings including mediation partners.
- The Network Report API only returns AdMob Network earnings.
- To get totals matching the dashboard, use the Mediation Report or
  request both Network + Mediation reports and sum them.

Metrics mapping (confirmed from network tab analysis):
- ESTIMATED_EARNINGS → doubleValue (already in USD, not micros)
- AD_REQUESTS        → integerValue
- MATCHED_REQUESTS   → integerValue
- IMPRESSIONS        → integerValue  (ad impressions served)
- CLICKS             → integerValue
"""
import logging
from datetime import date, datetime
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from config import (
    ADMOB_CLIENT_ID, ADMOB_CLIENT_SECRET,
    ADMOB_REFRESH_TOKEN, ADMOB_PUBLISHER_ID,
)

logger = logging.getLogger(__name__)
ADMOB_SCOPES = [
    "https://www.googleapis.com/auth/admob.readonly",
    "https://www.googleapis.com/auth/admob.report",
]
ADMOB_BASE = "https://admob.googleapis.com/v1"


def _get_credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=ADMOB_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=ADMOB_CLIENT_ID,
        client_secret=ADMOB_CLIENT_SECRET,
        scopes=ADMOB_SCOPES,
    )
    creds.refresh(Request())
    return creds


def _parse_metric(metric: dict) -> float:
    """Handle microsValue / integerValue / doubleValue."""
    if not metric:
        return 0.0
    if "microsValue" in metric:
        return int(metric["microsValue"]) / 1_000_000
    if "integerValue" in metric:
        return float(metric["integerValue"])
    if "doubleValue" in metric:
        return float(metric["doubleValue"])
    return 0.0


def fetch_admob_apps() -> list:
    """Return all apps under the publisher account."""
    creds      = _get_credentials()
    headers    = {"Authorization": f"Bearer {creds.token}"}
    url        = f"{ADMOB_BASE}/accounts/{ADMOB_PUBLISHER_ID}/apps"
    apps       = []
    page_token = None

    while True:
        params = {"pageSize": 100}
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"AdMob apps API error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        for app in data.get("apps", []):
            linked = app.get("linkedAppInfo", {})
            manual = app.get("manualAppInfo", {})
            name   = linked.get("displayName") or manual.get("displayName") or app.get("appId", "Unknown")
            apps.append({
                "app_id":   app.get("appId"),
                "name":     name,
                "platform": app.get("platform", ""),
            })
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return apps


def _fetch_network_report(target_date: date, headers: dict, app_id: str = None) -> dict:
    """Fetch AdMob Network report for one day."""
    report_spec = {
        "dateRange": {
            "startDate": {"year": target_date.year, "month": target_date.month, "day": target_date.day},
            "endDate":   {"year": target_date.year, "month": target_date.month, "day": target_date.day},
        },
        "dimensions": ["DATE"],
        "metrics": [
            "ESTIMATED_EARNINGS",
            "IMPRESSIONS",
            "CLICKS",
            "AD_REQUESTS",
            "MATCHED_REQUESTS",
        ],
    }
    if app_id and app_id != "ALL":
        report_spec["dimensionFilters"] = [{
            "dimension": "APP",
            "matchesAny": {"values": [app_id]},
        }]

    resp = requests.post(
        f"{ADMOB_BASE}/accounts/{ADMOB_PUBLISHER_ID}/networkReport:generate",
        json={"reportSpec": report_spec},
        headers=headers, timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Network report error {resp.status_code}: {resp.text[:400]}")

    totals = {"revenue": 0.0, "impressions": 0.0, "clicks": 0.0,
              "ad_requests": 0.0, "matched_requests": 0.0}
    for item in resp.json():
        if "row" not in item:
            continue
        m = item["row"].get("metricValues", {})
        totals["revenue"]          += _parse_metric(m.get("ESTIMATED_EARNINGS", {}))
        totals["impressions"]      += _parse_metric(m.get("IMPRESSIONS",        {}))
        totals["clicks"]           += _parse_metric(m.get("CLICKS",             {}))
        totals["ad_requests"]      += _parse_metric(m.get("AD_REQUESTS",        {}))
        totals["matched_requests"] += _parse_metric(m.get("MATCHED_REQUESTS",   {}))
    return totals


def _fetch_mediation_report(target_date: date, headers: dict, app_id: str = None) -> dict:
    """
    Fetch AdMob Mediation report for one day.
    This captures earnings from third-party ad networks shown in the dashboard.
    """
    report_spec = {
        "dateRange": {
            "startDate": {"year": target_date.year, "month": target_date.month, "day": target_date.day},
            "endDate":   {"year": target_date.year, "month": target_date.month, "day": target_date.day},
        },
        "dimensions": ["DATE"],
        "metrics": [
            "ESTIMATED_EARNINGS",
            "IMPRESSIONS",
            "CLICKS",
            "AD_REQUESTS",
            "MATCHED_REQUESTS",
        ],
    }
    if app_id and app_id != "ALL":
        report_spec["dimensionFilters"] = [{
            "dimension": "APP",
            "matchesAny": {"values": [app_id]},
        }]

    resp = requests.post(
        f"{ADMOB_BASE}/accounts/{ADMOB_PUBLISHER_ID}/mediationReport:generate",
        json={"reportSpec": report_spec},
        headers=headers, timeout=30,
    )
    if resp.status_code != 200:
        # Mediation report may not be available on all accounts — fail gracefully
        logger.warning(f"Mediation report unavailable: {resp.status_code} — using network only")
        return {"revenue": 0.0, "impressions": 0.0, "clicks": 0.0,
                "ad_requests": 0.0, "matched_requests": 0.0}

    totals = {"revenue": 0.0, "impressions": 0.0, "clicks": 0.0,
              "ad_requests": 0.0, "matched_requests": 0.0}
    for item in resp.json():
        if "row" not in item:
            continue
        m = item["row"].get("metricValues", {})
        totals["revenue"]          += _parse_metric(m.get("ESTIMATED_EARNINGS", {}))
        totals["impressions"]      += _parse_metric(m.get("IMPRESSIONS",        {}))
        totals["clicks"]           += _parse_metric(m.get("CLICKS",             {}))
        totals["ad_requests"]      += _parse_metric(m.get("AD_REQUESTS",        {}))
        totals["matched_requests"] += _parse_metric(m.get("MATCHED_REQUESTS",   {}))
    return totals


def fetch_admob_day(target_date: date, app_id: str = None) -> dict:
    """
    Fetch AdMob total earnings matching the dashboard.
    Uses Mediation Report only — it already includes AdMob network + all mediation partners,
    which is exactly what the AdMob dashboard 'Estimated earnings' shows.
    """
    creds   = _get_credentials()
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }

    data = _fetch_mediation_report(target_date, headers, app_id)

    # Fall back to network-only if mediation report is unavailable
    if data["revenue"] == 0.0:
        logger.warning(f"Mediation report returned 0 for {target_date}, falling back to network report")
        data = _fetch_network_report(target_date, headers, app_id)

    revenue          = data["revenue"]
    impressions      = int(data["impressions"])
    clicks           = int(data["clicks"])
    ad_requests      = int(data["ad_requests"])
    matched_requests = int(data["matched_requests"])

    ecpm_usd   = (revenue / impressions * 1000) if impressions > 0 else 0.0
    match_rate = (matched_requests / ad_requests * 100) if ad_requests > 0 else 0.0

    logger.info(
        f"AdMob {target_date} [app={app_id or 'ALL'}]: "
        f"revenue=${revenue:.6f} impressions={impressions} clicks={clicks}"
    )

    return {
        "date":               target_date,
        "estimated_earnings": round(revenue, 6),
        "impressions":        impressions,
        "clicks":             clicks,
        "ecpm_usd":           round(ecpm_usd, 6),
        "ad_requests":        ad_requests,
        "match_rate":         round(match_rate, 2),
        "fetched_at":         datetime.utcnow().isoformat(),
    }