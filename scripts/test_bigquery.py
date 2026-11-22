"""Test the BigQuery connection: log in, create a 1-row table, read it, delete it.

Run from the repo folder:  python scripts/test_bigquery.py
Uses GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS from .env
"""
import os

from dotenv import load_dotenv
from google.cloud import bigquery

LOCATION = "australia-southeast1"
EXPECTED_DATASETS = {"raw", "staging", "reporting"}

# 1. Read settings from .env (this also tells Google where the key file is)
load_dotenv()
project_id = os.environ["GCP_PROJECT_ID"]
table_id = f"{project_id}.raw.connection_test"

# 2. Log in as the service account
client = bigquery.Client(project=project_id, location=LOCATION)
print(f"Connected to project: {project_id}")

# 3. Check the 3 datasets exist and are in Sydney
found = {d.dataset_id for d in client.list_datasets()}
print(f"Datasets found: {sorted(found)}")
missing = EXPECTED_DATASETS - found
if missing:
    raise SystemExit(f"Missing datasets: {sorted(missing)}")
for name in sorted(EXPECTED_DATASETS):
    location = client.get_dataset(name).location
    print(f"  {name}: {location}")
    if location != LOCATION:
        raise SystemExit(f"{name} is in {location}, expected {LOCATION}")

try:
    # 4. Create a 1-row test table (tests the Data Editor and Job User roles)
    client.query(f"""
        CREATE OR REPLACE TABLE `{table_id}` AS
        SELECT 1 AS id, 'hello from python' AS message, CURRENT_TIMESTAMP() AS created_at
    """).result()
    print(f"Created test table: {table_id}")

    # 5. Read the row back
    rows = list(client.query(f"SELECT * FROM `{table_id}`").result())
    print(f"Read back {len(rows)} row: {dict(rows[0])}")

finally:
    # 6. Always delete the test table, even if a step above failed
    client.delete_table(table_id, not_found_ok=True)
    print("Deleted test table")

print("\nConnection test passed")
