"""
database.py — DB setup, schema, and query helpers.

Currency logic:
- AdMob stored in USD, Google Ads stored in INR
- Global USD→INR rate is the fallback
- MonthlyFxRate allows per-month override
- Effective rate = month override if set, else global rate
"""
from datetime import date, datetime
from calendar import monthrange
import pandas as pd
from sqlalchemy import (
    Column, Date, Float, Integer, String,
    create_engine, func,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ── ORM Models ──────────────────────────────────────────────────────────

class AdMobDaily(Base):
    __tablename__ = "admob_daily"
    id                 = Column(Integer, primary_key=True)
    date               = Column(Date, unique=True, nullable=False, index=True)
    estimated_earnings = Column(Float, default=0.0)   # always USD
    impressions        = Column(Integer, default=0)
    clicks             = Column(Integer, default=0)
    ecpm_usd           = Column(Float, default=0.0)   # always USD
    ad_requests        = Column(Integer, default=0)
    match_rate         = Column(Float, default=0.0)
    fetched_at         = Column(String)


class GoogleAdsDaily(Base):
    __tablename__ = "google_ads_daily"
    id           = Column(Integer, primary_key=True)
    date         = Column(Date, unique=True, nullable=False, index=True)
    cost         = Column(Float, default=0.0)   # always INR
    clicks       = Column(Integer, default=0)
    impressions  = Column(Integer, default=0)
    conversions  = Column(Float, default=0.0)
    ctr          = Column(Float, default=0.0)
    avg_cpc      = Column(Float, default=0.0)   # INR
    fetched_at   = Column(String)


class CurrencyConfig(Base):
    """Global currency settings + AdMob app filter."""
    __tablename__ = "currency_config"
    id               = Column(Integer, primary_key=True)
    usd_to_inr_rate  = Column(Float, default=90.0)
    display_currency = Column(String, default="INR")
    admob_app_id     = Column(String, default="ALL")   # "ALL" or specific app_id
    admob_app_name   = Column(String, default="All Apps")
    updated_at       = Column(String)


class MonthlyFxRate(Base):
    """
    Per-month USD→INR override.
    year_month format: "2025-01"
    If a row exists for a month, its rate overrides the global rate.
    """
    __tablename__ = "monthly_fx_rate"
    id           = Column(Integer, primary_key=True)
    year_month   = Column(String, unique=True, nullable=False, index=True)
    usd_to_inr   = Column(Float, nullable=False)
    updated_at   = Column(String)


class FetchLog(Base):
    __tablename__ = "fetch_log"
    id          = Column(Integer, primary_key=True)
    fetched_at  = Column(String)
    target_date = Column(Date)
    source      = Column(String)
    status      = Column(String)
    message     = Column(String, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_currency_config()


def _seed_currency_config():
    session = SessionLocal()
    try:
        if not session.query(CurrencyConfig).first():
            session.add(CurrencyConfig(
                usd_to_inr_rate=90.0,
                display_currency="INR",
                updated_at=datetime.utcnow().isoformat(),
            ))
            session.commit()
    finally:
        session.close()


# ── Currency config ──────────────────────────────────────────────────────

def get_currency_config() -> dict:
    session = SessionLocal()
    try:
        row = session.query(CurrencyConfig).first()
        return {
            "usd_to_inr_rate":  row.usd_to_inr_rate,
            "display_currency": row.display_currency,
            "admob_app_id":     row.admob_app_id   or "ALL",
            "admob_app_name":   row.admob_app_name or "All Apps",
            "updated_at":       row.updated_at,
        }
    finally:
        session.close()


def update_currency_config(usd_to_inr_rate: float, display_currency: str,
                            admob_app_id: str = "ALL", admob_app_name: str = "All Apps"):
    session = SessionLocal()
    try:
        row = session.query(CurrencyConfig).first()
        row.usd_to_inr_rate  = usd_to_inr_rate
        row.display_currency = display_currency
        row.admob_app_id     = admob_app_id
        row.admob_app_name   = admob_app_name
        row.updated_at       = datetime.utcnow().isoformat()
        session.commit()
    finally:
        session.close()


# ── Monthly FX rate overrides ────────────────────────────────────────────

def get_all_monthly_fx_rates() -> dict:
    """Returns {year_month: rate} for all months that have an override."""
    session = SessionLocal()
    try:
        rows = session.query(MonthlyFxRate).all()
        return {r.year_month: r.usd_to_inr for r in rows}
    finally:
        session.close()


def set_monthly_fx_rate(year_month: str, rate: float):
    """Upsert a monthly override rate. year_month e.g. '2025-01'."""
    session = SessionLocal()
    try:
        row = session.query(MonthlyFxRate).filter_by(year_month=year_month).first()
        if row:
            row.usd_to_inr = rate
            row.updated_at = datetime.utcnow().isoformat()
        else:
            session.add(MonthlyFxRate(
                year_month=year_month,
                usd_to_inr=rate,
                updated_at=datetime.utcnow().isoformat(),
            ))
        session.commit()
    finally:
        session.close()


def clear_monthly_fx_rate(year_month: str):
    """Remove a monthly override so the month falls back to global rate."""
    session = SessionLocal()
    try:
        session.query(MonthlyFxRate).filter_by(year_month=year_month).delete()
        session.commit()
    finally:
        session.close()


def effective_rate(year_month: str, global_rate: float,
                   monthly_overrides: dict) -> float:
    """Return the rate to use for a given month."""
    return monthly_overrides.get(year_month, global_rate)


# ── Conversion helpers ───────────────────────────────────────────────────

def _admob_to_display(usd_value: float, rate: float, display: str) -> float:
    return usd_value * rate if display == "INR" else usd_value


def _ads_to_display(inr_value: float, rate: float, display: str) -> float:
    return inr_value if display == "INR" else inr_value / rate


# ── Upsert ───────────────────────────────────────────────────────────────

def upsert_admob(data: dict):
    session = SessionLocal()
    try:
        row = session.query(AdMobDaily).filter_by(date=data["date"]).first()
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            session.add(AdMobDaily(**data))
        session.commit()
    finally:
        session.close()


def upsert_google_ads(data: dict):
    session = SessionLocal()
    try:
        row = session.query(GoogleAdsDaily).filter_by(date=data["date"]).first()
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            session.add(GoogleAdsDaily(**data))
        session.commit()
    finally:
        session.close()


def log_fetch(target_date: date, source: str, status: str, message: str = ""):
    session = SessionLocal()
    try:
        session.add(FetchLog(
            fetched_at=datetime.utcnow().isoformat(),
            target_date=target_date,
            source=source,
            status=status,
            message=message,
        ))
        session.commit()
    finally:
        session.close()


# ── Overall summary KPIs (aggregate query) ───────────────────────────────

def get_overall_summary(start: date, end: date,
                        global_rate: float, monthly_overrides: dict,
                        display: str) -> dict:
    """
    Aggregate KPIs for the full date range.
    Uses per-month rates when available, global rate otherwise.
    """
    session = SessionLocal()
    try:
        admob_rows = (
            session.query(AdMobDaily)
            .filter(AdMobDaily.date >= start, AdMobDaily.date <= end)
            .all()
        )
        gads_rows = (
            session.query(GoogleAdsDaily)
            .filter(GoogleAdsDaily.date >= start, GoogleAdsDaily.date <= end)
            .all()
        )
    finally:
        session.close()

    revenue = 0.0
    spend   = 0.0
    impressions  = 0
    clicks_admob = 0
    ecpm_sum     = 0.0
    ecpm_count   = 0
    conversions  = 0.0

    for r in admob_rows:
        ym   = r.date.strftime("%Y-%m")
        rate = effective_rate(ym, global_rate, monthly_overrides)
        revenue      += _admob_to_display(r.estimated_earnings, rate, display)
        impressions  += r.impressions
        clicks_admob += r.clicks
        if r.ecpm_usd:
            ecpm_sum   += _admob_to_display(r.ecpm_usd, rate, display)
            ecpm_count += 1

    for r in gads_rows:
        ym   = r.date.strftime("%Y-%m")
        rate = effective_rate(ym, global_rate, monthly_overrides)
        spend       += _ads_to_display(r.cost, rate, display)
        conversions += r.conversions

    return {
        "revenue":      revenue,
        "spend":        spend,
        "profit":       revenue - spend,
        "impressions":  impressions,
        "clicks_admob": clicks_admob,
        "ecpm":         ecpm_sum / ecpm_count if ecpm_count else 0.0,
        "conversions":  conversions,
    }


# ── Monthly summary ──────────────────────────────────────────────────────

def get_monthly_summary(start: date, end: date,
                        global_rate: float, monthly_overrides: dict,
                        display: str) -> pd.DataFrame:
    """
    One row per month. Each month uses its own effective rate.
    Includes the effective rate used so the UI can display it.
    """
    session = SessionLocal()
    try:
        admob_rows = (
            session.query(AdMobDaily)
            .filter(AdMobDaily.date >= start, AdMobDaily.date <= end)
            .all()
        )
        gads_rows = (
            session.query(GoogleAdsDaily)
            .filter(GoogleAdsDaily.date >= start, GoogleAdsDaily.date <= end)
            .all()
        )
    finally:
        session.close()

    # Aggregate per month
    months = {}  # year_month -> dict

    def _get_month(ym, label):
        if ym not in months:
            months[ym] = {
                "year_month": ym, "month_label": label,
                "revenue": 0.0, "spend": 0.0,
                "impressions": 0, "clicks_admob": 0,
                "clicks_gads": 0, "conversions": 0.0,
                "effective_rate": effective_rate(ym, global_rate, monthly_overrides),
                "rate_overridden": ym in monthly_overrides,
            }
        return months[ym]

    for r in admob_rows:
        ym    = r.date.strftime("%Y-%m")
        label = r.date.strftime("%b %Y")
        rate  = effective_rate(ym, global_rate, monthly_overrides)
        m = _get_month(ym, label)
        m["revenue"]      += _admob_to_display(r.estimated_earnings, rate, display)
        m["impressions"]  += r.impressions
        m["clicks_admob"] += r.clicks

    for r in gads_rows:
        ym    = r.date.strftime("%Y-%m")
        label = r.date.strftime("%b %Y")
        rate  = effective_rate(ym, global_rate, monthly_overrides)
        m = _get_month(ym, label)
        m["spend"]       += _ads_to_display(r.cost, rate, display)
        m["clicks_gads"] += r.clicks
        m["conversions"] += r.conversions

    if not months:
        return pd.DataFrame()

    df = pd.DataFrame(list(months.values()))
    df["profit"] = df["revenue"] - df["spend"]
    return df.sort_values("year_month").reset_index(drop=True)


# ── Day-wise for a single month (on-demand) ──────────────────────────────

def get_daywise_for_month(year: int, month: int,
                          rate: float, display: str) -> pd.DataFrame:
    """Fetches one month of day-wise data. rate is the effective rate for this month."""
    first_day = date(year, month, 1)
    last_day  = date(year, month, monthrange(year, month)[1])

    session = SessionLocal()
    try:
        admob_rows = (
            session.query(AdMobDaily)
            .filter(AdMobDaily.date >= first_day, AdMobDaily.date <= last_day)
            .all()
        )
        gads_rows = (
            session.query(GoogleAdsDaily)
            .filter(GoogleAdsDaily.date >= first_day, GoogleAdsDaily.date <= last_day)
            .all()
        )
    finally:
        session.close()

    all_dates = pd.date_range(first_day, last_day, freq="D").date
    df = pd.DataFrame({"date": all_dates})

    admob_df = pd.DataFrame([{
        "date":         r.date,
        "revenue":      _admob_to_display(r.estimated_earnings, rate, display),
        "ecpm":         _admob_to_display(r.ecpm_usd, rate, display),
        "impressions":  r.impressions,
        "clicks_admob": r.clicks,
        "ad_requests":  r.ad_requests,
        "match_rate":   r.match_rate,
    } for r in admob_rows]) if admob_rows else pd.DataFrame()

    gads_df = pd.DataFrame([{
        "date":        r.date,
        "spend":       _ads_to_display(r.cost, rate, display),
        "clicks_gads": r.clicks,
        "conversions": r.conversions,
        "ctr":         r.ctr,
        "avg_cpc":     _ads_to_display(r.avg_cpc, rate, display),
    } for r in gads_rows]) if gads_rows else pd.DataFrame()

    if not admob_df.empty:
        df = df.merge(admob_df, on="date", how="left")
    else:
        for col in ["revenue", "ecpm", "impressions", "clicks_admob", "ad_requests", "match_rate"]:
            df[col] = 0.0

    if not gads_df.empty:
        df = df.merge(gads_df, on="date", how="left")
    else:
        for col in ["spend", "clicks_gads", "conversions", "ctr", "avg_cpc"]:
            df[col] = 0.0

    df.fillna(0, inplace=True)
    df["profit"] = df["revenue"] - df["spend"]
    df["date"]   = pd.to_datetime(df["date"])
    return df.sort_values("date")


def get_last_fetch_logs(n: int = 10) -> pd.DataFrame:
    session = SessionLocal()
    try:
        rows = session.query(FetchLog).order_by(FetchLog.id.desc()).limit(n).all()
        return pd.DataFrame([{
            "fetched_at": r.fetched_at,
            "date":       r.target_date,
            "source":     r.source,
            "status":     r.status,
            "message":    r.message,
        } for r in rows])
    finally:
        session.close()