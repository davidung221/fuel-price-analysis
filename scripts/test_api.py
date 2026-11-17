"""Test the NSW FuelCheck API: get an access token, then fetch current prices.

Uses 2 of the free plan's 2,500 monthly calls each time it runs.
"""
import os
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.onegov.nsw.gov.au"

# Read the API key and secret from the .env file (never hard-code them)
load_dotenv()
api_key = os.getenv("FUEL_API_KEY")
api_secret = os.getenv("FUEL_API_SECRET")
if not api_key or not api_secret:
    raise SystemExit("Missing FUEL_API_KEY or FUEL_API_SECRET in .env")

# 1. Get an access token using the key + secret (like a username + password)
token_resp = requests.get(
    f"{BASE_URL}/oauth/client_credential/accesstoken",
    params={"grant_type": "client_credentials"},
    auth=(api_key, api_secret),  # requests builds the Basic auth header for us
    timeout=30,
)
token_resp.raise_for_status()  # stops with an error if the request failed
token = token_resp.json()["access_token"]
print("Token received")

# 2. Get all current NSW fuel prices using the token + key
headers = {
    "Authorization": f"Bearer {token}",
    "apikey": api_key,
    "Content-Type": "application/json; charset=utf-8",
    "transactionid": str(uuid.uuid4()),  # unique ID for this request
    "requesttimestamp": datetime.now(timezone.utc).strftime("%d/%m/%Y %I:%M:%S %p"),
}
prices_resp = requests.get(
    f"{BASE_URL}/FuelPriceCheck/v1/fuel/prices",
    headers=headers,
    timeout=60,
)
prices_resp.raise_for_status()
data = prices_resp.json()

# 3. Print a quick summary (not the token or key)
stations = data.get("stations", [])
prices = data.get("prices", [])
print(f"Stations: {len(stations)}")
print(f"Prices:   {len(prices)}")
if stations:
    print("Example station:", stations[0])
if prices:
    print("Example price:  ", prices[0])
