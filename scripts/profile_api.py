"""Profile the FuelCheck API response: fields, blanks, fuel types, reference data.

Run from the repo folder:  python scripts/profile_api.py
Uses 4 API calls (2 tokens + prices + reference data). Saves nothing.
"""
import pandas as pd
import requests

import fuel_api

HISTORY_FUEL_CODES = {"E10", "U91", "P95", "P98", "DL", "PDL", "LPG", "E85", "B20", "EV"}


def profile_records(name, records):
    """Print one line per field: how often it appears, blanks, unique values, example."""
    print(f"\n=== {name}: {len(records):,} records ===")
    all_fields = sorted({key for rec in records for key in rec})
    rows = []
    for field in all_fields:
        values = [rec[field] for rec in records if field in rec]
        blanks = sum(v is None or (isinstance(v, str) and v.strip() == "") for v in values)
        example = next((v for v in values if v not in (None, "")), None)
        rows.append({
            "field": field,
            "present_in": len(values),
            "missing": len(records) - len(values),
            "blank": blanks,
            "unique": len({str(v) for v in values}),
            "example": str(example)[:60],
        })
    print(pd.DataFrame(rows).to_string(index=False))


def describe_lovs(data):
    """Print the sections of the reference data and a few examples from each."""
    print("\n=== Reference data (lovs) ===")
    if not isinstance(data, dict):
        print(f"Unexpected format: {type(data).__name__}")
        return
    for section, content in data.items():
        items = content.get("items", content) if isinstance(content, dict) else content
        if isinstance(items, list):
            print(f"\n{section}: {len(items)} items")
            for item in items[:5]:
                print("   ", item)
        else:
            print(f"\n{section}: {str(items)[:200]}")


# 1. Log in and get current prices
api_key, api_secret = fuel_api.load_credentials()
token = fuel_api.get_token(api_key, api_secret)
data = fuel_api.get_json(fuel_api.PRICES_PATH, token, api_key)
stations = data.get("stations", [])
prices = data.get("prices", [])
print("Top-level keys in /fuel/prices:", list(data.keys()))

# 2. Field-by-field profile of stations and prices
profile_records("stations", stations)
profile_records("prices", prices)

# 3. Fuel types, and how they compare with the history file codes
price_df = pd.DataFrame(prices)
print("\n=== Fuel types ===")
summary = price_df.groupby("fueltype")["price"].agg(["count", "min", "max"])
print(summary.to_string())
api_codes = set(price_df["fueltype"].dropna())
print("In API but not in history:", sorted(api_codes - HISTORY_FUEL_CODES) or "none")
print("In history but not in API:", sorted(HISTORY_FUEL_CODES - api_codes) or "none")

# 4. Relationship and date checks
station_codes = {str(s.get("code")) for s in stations}
price_codes = set(price_df["stationcode"].astype(str))
print("\n=== Checks ===")
print("Prices with no matching station:", len(price_codes - station_codes))
print("Stations with no prices:", len(station_codes - price_codes))
print("Duplicate station + fuel pairs:",
      int(price_df.duplicated(subset=["stationcode", "fueltype"]).sum()))
updated = pd.to_datetime(price_df["lastupdated"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
print("lastupdated that failed to parse:", int(updated.isna().sum()))
print("lastupdated range:", updated.min(), "to", updated.max())

# 5. Reference data (a fresh token, in case the first is close to expiry)
try:
    token = fuel_api.get_token(api_key, api_secret)
    describe_lovs(fuel_api.get_json(fuel_api.LOVS_PATH, token, api_key))
except requests.HTTPError as err:
    print(f"\nReference data request failed: {err}")
