# AdMob + Google Ads Revenue Dashboard

## Project Structure
```
admob-dashboard/
├── app.py                  # Streamlit dashboard
├── config.py               # API credentials & settings
├── database.py             # DB setup & queries
├── fetchers/
│   ├── __init__.py
│   ├── admob_fetcher.py    # AdMob API integration
│   └── google_ads_fetcher.py # Google Ads API integration
├── cron_job.py             # Scheduled data fetcher
├── requirements.txt
└── .env.example
```

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill credentials
3. Run cron: `python cron_job.py &`
4. Run dashboard: `streamlit run app.py`
