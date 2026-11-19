"""Profile every FuelCheck history file: rows, dates and data quality checks.

Run from the repo folder:  python scripts/profile_history.py
Saves the results to docs/history_profile.csv
"""
from pathlib import Path

import pandas as pd

from read_history import parse_dates, read_file

RAW_DIR = Path("data/raw")
OUTPUT = Path("docs/history_profile.csv")
DATE_COL = "PriceUpdatedDate"
PRICE_COL = "Price"

results = []
low_prices = []  # rows under 100 c/L, to check by fuel type
expected_cols = None

for path in sorted(RAW_DIR.iterdir()):
    if path.suffix.lower() not in (".csv", ".xlsx"):
        continue

    df = read_file(path)
    cols = [c for c in df.columns if c != "source_file"]

    # Use the first file's columns as the standard to compare against
    if expected_cols is None:
        expected_cols = cols
        print("Columns in first file:", expected_cols, "\n")
    if cols != expected_cols:
        print(f"Different columns in {path.name}: {cols}")

    if DATE_COL not in df.columns or PRICE_COL not in df.columns:
        print(f"Skipping checks for {path.name}: missing {DATE_COL} or {PRICE_COL}")
        continue

    dates = parse_dates(df[DATE_COL])
    prices = pd.to_numeric(df[PRICE_COL], errors="coerce")

    results.append({
        "file": path.name,
        "rows": len(df),
        "min_date": dates.min(),
        "max_date": dates.max(),
        "months_covered": dates.dt.to_period("M").nunique(),
        "bad_dates": int(dates.isna().sum()),
        "blank_cells": int(df[cols].isna().sum().sum()),
        "duplicate_rows": int(df.duplicated(subset=cols).sum()),
        "price_under_100": int((prices < 100).sum()),
        "price_over_300": int((prices > 300).sum()),
        "same_columns": cols == expected_cols,
    })
    low_prices.append(df.loc[prices < 100, ["FuelCode", PRICE_COL]])

summary = pd.DataFrame(results).sort_values("min_date")
print(summary.to_string(index=False))
print(f"\nFiles: {len(summary)}   Total rows: {summary['rows'].sum():,}")

# Files should each cover exactly one month
multi_month = summary[summary["months_covered"] != 1]
print(f"Files covering more than one month: {len(multi_month)}")

# Which fuel types have prices under 100 c/L?
low = pd.concat(low_prices)
print("\nPrices under 100 c/L by fuel type:")
print(low.groupby("FuelCode")[PRICE_COL].agg(["count", "min", "max"]).to_string())

OUTPUT.parent.mkdir(exist_ok=True)
summary.to_csv(OUTPUT, index=False)
print(f"Saved to {OUTPUT}")
