"""Shared functions for calling the NSW FuelCheck API.

Used by profile_api.py now, and by the daily extract script later.
Credentials come from .env (locally) or environment variables (GitHub Actions).
"""
import os
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.onegov.nsw.gov.au"
PRICES_PATH = "/FuelPriceCheck/v1/fuel/prices"
LOVS_PATH = "/FuelCheckRefData/v1/fuel/lovs"


def load_credentials():
    """Return the API key and secret, stopping with a clear message if missing."""
    load_dotenv()
    api_key = os.getenv("FUEL_API_KEY")
    api_secret = os.getenv("FUEL_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("Missing FUEL_API_KEY or FUEL_API_SECRET in .env")
    return api_key, api_secret


def get_token(api_key, api_secret):
    """Swap the key + secret for a temporary access token (1 API call)."""
    resp = requests.get(
        f"{BASE_URL}/oauth/client_credential/accesstoken",
        params={"grant_type": "client_credentials"},
        auth=(api_key, api_secret),  # requests builds the Basic auth header
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_json(path, token, api_key):
    """Call one API endpoint and return its JSON response (1 API call)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": api_key,
        "Content-Type": "application/json; charset=utf-8",
        "transactionid": str(uuid.uuid4()),
        "requesttimestamp": datetime.now(timezone.utc).strftime("%d/%m/%Y %I:%M:%S %p"),
    }
    resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()
