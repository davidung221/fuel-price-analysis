"""Combine the in-scope FuelCheck history files into one Parquet file.

Scope: Nov 2024 - Oct 2026 (24 months).
Run from the repo folder:  python scripts/combine_history.py
Output: data/processed/fuel_history.parquet (not committed to Git)

No cleaning happens here (duplicates, outliers, suburbs). That belongs in
staging, so the raw data stays a faithful copy of the source files.
"""
from pathlib import Path

import pandas as pd

from read_history import parse_dates, read_file

RAW_DIR = Path("data/raw")
PROFILE = Path("docs/history_profile.csv")
OUTPUT = Path("data/processed/fuel_history.parquet")

START = pd.Timestamp("2024-11-01")  # first day in scope
END = pd.Timestamp("2026-11-01")    # first day OUT of scope

SOURCE_COLUMNS = ["ServiceStationName", "Address", "Suburb", "Postcode",
                  "Brand", "FuelCode", "PriceUpdatedDate", "Price"]
TEXT_COLUMNS = ["ServiceStationName", "Address", "Suburb", "Postcode",
                "Brand", "FuelCode", "source_file"]


def check(passed, message):
    """Print the result of a check, and stop the script if it failed."""
    print(("PASS  " if passed else "FAIL  ") + message)
    if not passed:
        raise SystemExit("Stopped: fix the failed check before saving.")


# 1. Pick the in-scope files using the profile results (each file = one month)
profile = pd.read_csv(PROFILE, parse_dates=["min_date"])
in_scope = profile[(profile["min_date"] >= START) & (profile["min_date"] < END)]
expected_rows = int(in_scope["rows"].sum())
print(f"In-scope files: {len(in_scope)}   Expected rows: {expected_rows:,}\n")

# 2. Read each file and convert its dates
frames = []
for file_name in in_scope["file"]:
    df = read_file(RAW_DIR / file_name)
    df["PriceUpdatedDate"] = parse_dates(df["PriceUpdatedDate"])
    frames.append(df)
    print(f"Read {file_name}: {len(df):,} rows")

history = pd.concat(frames, ignore_index=True)

# 3. Make data types consistent across all files
history["Postcode"] = (history["Postcode"].astype(str).str.strip()
                       .str.replace(r"\.0$", "", regex=True))  # 2257.0 -> 2257
for col in TEXT_COLUMNS:
    history[col] = history[col].astype("string")
history["Price"] = pd.to_numeric(history["Price"], errors="coerce")
# Microsecond precision, which BigQuery supports
history["PriceUpdatedDate"] = history["PriceUpdatedDate"].astype("datetime64[us]")

# 4. Keep only rows inside the scope dates (a safety net: should remove 0)
before = len(history)
history = history[(history["PriceUpdatedDate"] >= START) &
                  (history["PriceUpdatedDate"] < END)]
print(f"\nRows outside scope removed: {before - len(history):,}")

# 5. Record when this combine was run
history["loaded_at"] = pd.Timestamp.now(tz="UTC").floor("s")
history["loaded_at"] = history["loaded_at"].astype("datetime64[us, UTC]")

# 6. Check everything before saving
print("\nChecks:")
check(len(history) == expected_rows,
      f"Row count {len(history):,} matches expected {expected_rows:,}")
check(history["PriceUpdatedDate"].min() >= START,
      f"Earliest date {history['PriceUpdatedDate'].min()} is in scope")
check(history["PriceUpdatedDate"].max() < END,
      f"Latest date {history['PriceUpdatedDate'].max()} is in scope")
check(list(history.columns) == SOURCE_COLUMNS + ["source_file", "loaded_at"],
      "Columns are as expected")
check(int(history.isna().sum().sum()) == 0,
      "No blank values (all conversions worked)")

# 7. Save
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
history.to_parquet(OUTPUT, index=False)
size_mb = OUTPUT.stat().st_size / 1_000_000
print(f"\nSaved {len(history):,} rows to {OUTPUT} ({size_mb:.1f} MB)")
