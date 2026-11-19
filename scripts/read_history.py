"""Read one FuelCheck price history file (CSV or XLSX) into a DataFrame.

Handles the two layouts in the history files:
- newer files: column names in the first row
- older files: a title row first, column names a few rows down
"""
from pathlib import Path

import pandas as pd

HEADER_MARKER = "FuelCode"  # a column name every file has
MAX_HEADER_SEARCH = 10      # the header row is within the first 10 rows


def find_header_row(path):
    """Return the row number (counting from 0) that holds the column names."""
    if path.suffix.lower() == ".csv":
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            lines = [next(f, "") for _ in range(MAX_HEADER_SEARCH)]
    else:
        preview = pd.read_excel(path, header=None, nrows=MAX_HEADER_SEARCH)
        lines = [" ".join(str(v) for v in row) for row in preview.values]

    for i, line in enumerate(lines):
        if HEADER_MARKER in line:
            return i
    raise ValueError(f"No row containing '{HEADER_MARKER}' found in {path.name}")


def parse_dates(column):
    """Convert a date column to datetimes, handling both formats in the files.

    - ISO format (2024-07-01 00:04:36): read year-month-day
    - Australian format (1/06/2025 0:08): read day first
    Excel files usually arrive as datetimes already and are left as they are.
    """
    if pd.api.types.is_datetime64_any_dtype(column):
        return column

    text = column.astype(str).str.strip()
    is_iso = text.str.match(r"^\d{4}-\d{2}-\d{2}")

    parsed = pd.Series(pd.NaT, index=column.index, dtype="datetime64[ns]")
    parsed[is_iso] = pd.to_datetime(text[is_iso], format="ISO8601", errors="coerce")
    parsed[~is_iso] = pd.to_datetime(text[~is_iso], format="mixed", dayfirst=True, errors="coerce")
    return parsed


def read_file(path):
    """Read a history file, whatever its type or layout, into a clean DataFrame."""
    path = Path(path)
    header_row = find_header_row(path)

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, skiprows=header_row,
                         encoding="utf-8-sig", encoding_errors="replace")
    elif path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, header=header_row)
    else:
        raise ValueError(f"Unsupported file type: {path.name}")

    df.columns = df.columns.astype(str).str.strip()  # remove stray spaces in names
    df = df.dropna(how="all")                        # drop fully empty rows
    df = df.dropna(axis=1, how="all")                # drop fully empty columns
    df["source_file"] = path.name                    # trace every row to its file
    return df
