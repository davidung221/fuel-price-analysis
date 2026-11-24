"""Daily extract: today's NSW fuel prices from the FuelCheck API into BigQuery.

Run from the repo folder:  python scripts/extract_prices.py
Uses 2 API calls (token + prices).

Loads two tables, as received from the API (no cleaning):
- raw.api_stations: one row per station per day
- raw.api_prices:   one row per station per fuel type per day

Safe to re-run: today's rows are deleted before the new ones are added.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

import fuel_api

LOCATION = "australia-southeast1"
SYDNEY = ZoneInfo("Australia/Sydney")
STATIONS_TABLE = "raw.api_stations"
PRICES_TABLE = "raw.api_prices"

# Pre-load checks: a normal day has about 3,300 stations and 10,500 prices
MIN_STATIONS = 3000
MIN_PRICES = 9000

STATION_SCHEMA = [
    bigquery.SchemaField("code", "STRING", description="Station code, joins to api_prices.stationcode"),
    bigquery.SchemaField("stationid", "STRING"),
    bigquery.SchemaField("brandid", "STRING"),
    bigquery.SchemaField("brand", "STRING"),
    bigquery.SchemaField("name", "STRING"),
    bigquery.SchemaField("address", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT64"),
    bigquery.SchemaField("longitude", "FLOAT64"),
    bigquery.SchemaField("isAdBlueAvailable", "BOOL"),
    bigquery.SchemaField("snapshot_date", "DATE", description="Day of the extract, Sydney time"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", description="When the extract ran (UTC)"),
]

PRICE_SCHEMA = [
    bigquery.SchemaField("stationcode", "STRING", description="Joins to api_stations.code"),
    bigquery.SchemaField("fueltype", "STRING"),
    bigquery.SchemaField("price", "FLOAT64", description="Cents per litre (EV: charging price)"),
    bigquery.SchemaField("lastupdated", "TIMESTAMP", description="When the price last changed (UTC)"),
    bigquery.SchemaField("snapshot_date", "DATE", description="Day of the extract, Sydney time"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", description="When the extract ran (UTC)"),
]

DESCRIPTIONS = {
    STATIONS_TABLE: "Daily snapshot of NSW FuelCheck stations from the Fuel API, as received.",
    PRICES_TABLE: "Daily snapshot of current NSW FuelCheck prices from the Fuel API, as received. "
                  "Unchanged prices repeat each day.",
}


def check(passed, message):
    """Print the result of a check, and stop the script if it failed."""
    print(("PASS  " if passed else "FAIL  ") + message)
    if not passed:
        raise SystemExit("Stopped: a check failed. Nothing was loaded.")


def to_tables(data, snapshot_date, loaded_at):
    """Turn the API's JSON into a stations table and a prices table."""
    # Stations: json_normalize splits location into location.latitude / location.longitude
    stations = pd.json_normalize(data["stations"])
    stations = stations.rename(columns={"location.latitude": "latitude",
                                        "location.longitude": "longitude"})

    # Warn about any new fields the API has started sending (they are not loaded)
    station_cols = [f.name for f in STATION_SCHEMA if f.name not in ("snapshot_date", "loaded_at")]
    extra = sorted(set(stations.columns) - set(station_cols))
    if extra:
        print(f"Note: new station fields not loaded: {extra}")
    missing = sorted(set(station_cols) - set(stations.columns))
    check(not missing, f"All expected station fields present {missing if missing else ''}")
    stations = stations[station_cols].copy()

    for col in ["code", "stationid", "brandid", "brand", "name", "address"]:
        stations[col] = stations[col].astype("string")
    stations["latitude"] = pd.to_numeric(stations["latitude"], errors="coerce")
    stations["longitude"] = pd.to_numeric(stations["longitude"], errors="coerce")
    stations["isAdBlueAvailable"] = stations["isAdBlueAvailable"].astype("boolean")

    # Prices
    prices = pd.DataFrame(data["prices"])
    price_cols = ["stationcode", "fueltype", "price", "lastupdated"]
    missing = sorted(set(price_cols) - set(prices.columns))
    check(not missing, f"All expected price fields present {missing if missing else ''}")
    prices = prices[price_cols].copy()

    prices["stationcode"] = prices["stationcode"].astype("string")
    prices["fueltype"] = prices["fueltype"].astype("string")
    prices["price"] = pd.to_numeric(prices["price"], errors="coerce")
    # The API sends day-first text in UTC, e.g. 22/11/2026 23:50:21
    prices["lastupdated"] = pd.to_datetime(prices["lastupdated"], format="%d/%m/%Y %H:%M:%S",
                                           errors="coerce", utc=True).astype("datetime64[us, UTC]")

    # Tracking columns, the same value on every row
    for table in (stations, prices):
        table["snapshot_date"] = snapshot_date
        table["loaded_at"] = loaded_at

    return stations, prices


def run_checks(stations, prices):
    """Check the data before loading. Any failure stops the script."""
    print("\nPre-load checks:")
    check(len(stations) >= MIN_STATIONS, f"{len(stations):,} stations (minimum {MIN_STATIONS:,})")
    check(len(prices) >= MIN_PRICES, f"{len(prices):,} prices (minimum {MIN_PRICES:,})")
    check(not stations["code"].duplicated().any(), "Station codes are unique")
    check(int(stations[["code", "name", "brand", "address"]].isna().sum().sum()) == 0,
          "No blank station codes, names, brands or addresses")
    check(int(prices.isna().sum().sum()) == 0,
          "No blank price values (all prices and dates converted)")
    unmatched = (~prices["stationcode"].isin(stations["code"])).sum()
    check(unmatched == 0, f"Every price has a matching station ({unmatched} unmatched)")
    dupes = prices.duplicated(subset=["stationcode", "fueltype"]).sum()
    check(dupes == 0, f"No duplicate station + fuel pairs ({dupes} found)")


def load(client, df, table_name, schema, snapshot_date):
    """Delete any rows already loaded today, then append today's rows."""
    table_id = f"{client.project}.{table_name}"
    today = [bigquery.ScalarQueryParameter("d", "DATE", snapshot_date)]

    try:
        client.get_table(table_id)
        deleted = client.query(
            f"DELETE FROM `{table_id}` WHERE snapshot_date = @d",
            job_config=bigquery.QueryJobConfig(query_parameters=today),
        )
        deleted.result()
        print(f"{table_name}: removed {deleted.num_dml_affected_rows or 0:,} rows already loaded today")
    except NotFound:
        print(f"{table_name}: table doesn't exist yet, it will be created")

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        destination_table_description=DESCRIPTIONS[table_name],
    )
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()

    # Check today's row count in BigQuery matches what was loaded
    count = list(client.query(
        f"SELECT COUNT(*) AS n FROM `{table_id}` WHERE snapshot_date = @d",
        job_config=bigquery.QueryJobConfig(query_parameters=today),
    ).result())[0].n
    check(count == len(df), f"{table_name}: {count:,} rows for {snapshot_date} in BigQuery")


def main():
    # 1. Dates for this run
    snapshot_date = datetime.now(SYDNEY).date()
    loaded_at = pd.Timestamp.now(tz="UTC").floor("s")
    print(f"Snapshot date (Sydney): {snapshot_date}\n")

    # 2. Get today's prices from the API
    api_key, api_secret = fuel_api.load_credentials()
    token = fuel_api.get_token(api_key, api_secret)
    data = fuel_api.get_json(fuel_api.PRICES_PATH, token, api_key)
    print(f"API returned {len(data['stations']):,} stations and {len(data['prices']):,} prices\n")

    # 3. Shape into tables and check them before loading
    stations, prices = to_tables(data, snapshot_date, loaded_at)
    run_checks(stations, prices)

    # 4. Load into BigQuery
    load_dotenv()
    client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"], location=LOCATION)
    print("\nLoading:")
    load(client, stations, STATIONS_TABLE, STATION_SCHEMA, snapshot_date)
    load(client, prices, PRICES_TABLE, PRICE_SCHEMA, snapshot_date)

    print(f"\nDone: snapshot for {snapshot_date} loaded")


if __name__ == "__main__":
    main()
