import os
from dotenv import load_dotenv

load_dotenv()

# ── AdMob ──────────────────────────────────────────────────────────────
ADMOB_CLIENT_ID = os.getenv("ADMOB_CLIENT_ID")
ADMOB_CLIENT_SECRET = os.getenv("ADMOB_CLIENT_SECRET")
ADMOB_REFRESH_TOKEN = os.getenv("ADMOB_REFRESH_TOKEN")
ADMOB_PUBLISHER_ID = os.getenv("ADMOB_PUBLISHER_ID")

# ── Google Ads ──────────────────────────────────────────────────────────
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID")

# ── Database ────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dashboard.db")

# ── App ─────────────────────────────────────────────────────────────────
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
FETCH_HOUR = int(os.getenv("FETCH_HOUR", 1))
FETCH_MINUTE = int(os.getenv("FETCH_MINUTE", 0))

CURRENCY_SYMBOL = "₹"   # Change to "$" if needed
