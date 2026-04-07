# get_refresh_token.py
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/admob.readonly",  # ← needed for apps list
    "https://www.googleapis.com/auth/admob.report",    # ← needed for reports
    "https://www.googleapis.com/auth/adwords",         # ← Google Ads
]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    scopes=SCOPES
)

creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\n✅ Copy these into your .env:\n")
print(f"ADMOB_CLIENT_ID={creds.client_id}")
print(f"ADMOB_CLIENT_SECRET={creds.client_secret}")
print(f"ADMOB_REFRESH_TOKEN={creds.refresh_token}")
print(f"\nGOOGLE_ADS_CLIENT_ID={creds.client_id}")
print(f"GOOGLE_ADS_CLIENT_SECRET={creds.client_secret}")
print(f"GOOGLE_ADS_REFRESH_TOKEN={creds.refresh_token}")