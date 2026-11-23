"""Load the combined FuelCheck history into BigQuery: raw.fuel_price_history

Run from the repo folder:  python scripts/load_history_to_bq.py
Uses GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS from .env

Replaces the table on every run, so re-running never duplicates rows.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

LOCATION = "australia-southeast1"
SOURCE = Path("data/processed/fuel_history.parquet")
TABLE_NAME = "raw.fuel_price_history"

# Column types written down explicitly, so BigQuery doesn't have to guess
SCHEMA = [
    bigquery.SchemaField("ServiceStationName", "STRING"),
    bigquery.SchemaField("Address", "STRING"),
    bigquery.SchemaField("Suburb", "STRING"),
    bigquery.SchemaField("Postcode", "STRING"),
    bigquery.SchemaField("Brand", "STRING"),
    bigquery.SchemaField("FuelCode", "STRING"),
    bigquery.SchemaField("PriceUpdatedDate", "DATETIME",
                         description="When the price changed, NSW local time"),
    bigquery.SchemaField("Price", "FLOAT64", description="Cents per litre"),
    bigquery.SchemaField("source_file", "STRING",
                         description="History file the row came from"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP",
                         description="When the files were combined (UTC)"),
]

DESCRIPTION = (
    "NSW FuelCheck price history, Nov 2024 - Oct 2026. One row per price change. "
    "Source: NSW Fair Trading via Data.NSW, CC BY-SA 3.0 AU. "
    "Loaded as-is: no cleaning (that happens in staging)."
)


def check(passed, message):
    """Print the result of a check, and stop the script if it failed."""
    print(("PASS  " if passed else "FAIL  ") + message)
    if not passed:
        raise SystemExit("Stopped: a check failed.")


# 1. Settings and login
load_dotenv()
project_id = os.environ["GCP_PROJECT_ID"]
table_id = f"{project_id}.{TABLE_NAME}"
client = bigquery.Client(project=project_id, location=LOCATION)

# 2. Read the combined file
df = pd.read_parquet(SOURCE)
print(f"Read {len(df):,} rows from {SOURCE}")

# 3. Load it, replacing the table if it already exists
job_config = bigquery.LoadJobConfig(
    schema=SCHEMA,
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    destination_table_description=DESCRIPTION,
)
print(f"Loading into {table_id} ...")
job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
job.result()  # waits until the load finishes (raises an error if it failed)
print(f"Load finished: {job.output_rows:,} rows written\n")

# 4. Check the table matches the file
result = list(client.query(f"""
    SELECT
        COUNT(*) AS row_count,
        MIN(PriceUpdatedDate) AS earliest,
        MAX(PriceUpdatedDate) AS latest,
        COUNT(DISTINCT source_file) AS files
    FROM `{table_id}`
""").result())[0]

print("Checks:")
check(result.row_count == len(df),
      f"Row count {result.row_count:,} matches file ({len(df):,})")
check(pd.Timestamp(result.earliest) == df["PriceUpdatedDate"].min(),
      f"Earliest date {result.earliest} matches file")
check(pd.Timestamp(result.latest) == df["PriceUpdatedDate"].max(),
      f"Latest date {result.latest} matches file")
check(result.files == df["source_file"].nunique(),
      f"{result.files} source files, matches file")

print(f"\nDone: {table_id} is ready")
