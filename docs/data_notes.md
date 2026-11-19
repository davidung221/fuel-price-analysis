# Data Notes: FuelCheck Price History

_Last updated: 17 Nov 2026_

## Source

| Item | Detail |
|---|---|
| Dataset | [FuelCheck price history](https://data.nsw.gov.au/data/dataset/fuel-check) (NSW Fair Trading, via Data.NSW) |
| Licence | Creative Commons Attribution Share-Alike 3.0 Australia |
| Coverage | Aug 2016 onwards, one file per month |
| Published | Monthly, usually early the following month |
| Downloaded | 34 files, Jan 2024 – Oct 2026 (via the Data.NSW CKAN API) |

## Scope decision

- **Using:** Nov 2024 – Oct 2026 (24 months). Jan–Oct 2024 files are kept but filtered out at load.
- **Why:** the project asks when and where to buy fuel *now*. 24 months covers every season twice and many price cycles.
- **Excluded:** 2016–2023. Older files use different layouts and add cleaning effort without much value for current buying decisions.

## Structure

One row = one price change at one station for one fuel type. It is **not** a daily price per station.

| Column | Meaning | Notes |
|---|---|---|
| `ServiceStationName` | Station name | |
| `Address` | Street address | |
| `Suburb` | Suburb | Check for inconsistent case or spelling |
| `Postcode` | Postcode | Store as text, not number |
| `Brand` | Fuel brand | |
| `FuelCode` | Fuel type code | See fuel codes below |
| `PriceUpdatedDate` | When the price changed | Parse as date-time |
| `Price` | Price | Cents per litre |

> To verify: column names and order match the files. Update this table if any differ.

## Fuel codes

| Code | Fuel | In scope? |
|---|---|---|
| E10 | Ethanol 94 | Yes |
| U91 | Unleaded 91 | Yes |
| P95 | Premium 95 | Yes |
| P98 | Premium 98 | Yes |
| DL | Diesel | Yes (fleets) |
| PDL | Premium diesel | Yes (fleets) |
| LPG | LPG | Optional |
| E85, B20, EV | Other | No |

> To verify: full list of codes present in the files.

## Format issues found

| # | Issue | Handling |
|---|---|---|
| 1 | **Mixed file types:** 26 XLSX, 8 CSV | Choose the reader by file extension |
| 2 | **Different header rows:** older files have a title in row 1 and headers in row 3; newer files start at row 1 | Detect the header row by finding the first column name |
| 3 | **Inconsistent file names** (e.g. `mar25`, `july2025`, `october2026`; Oct 2026 is XLSX despite the `price_history_checks` name) | Take the month from `PriceUpdatedDate`, not the file name |

## Data quality checks

Profiled 19 Nov 2026 with `scripts/profile_history.py`. Full results: `docs/history_profile.csv`.

| Check | Result |
|---|---|
| Files | 34 (Jan 2024 – Oct 2026), 2,897,626 rows |
| Rows per file | 55k – 155k. Roughly double from Mar 2026 onwards (investigate in analysis) |
| Same columns in all files | Yes |
| Each file covers one month | Yes, after fixing date parsing |
| Bad dates | 0 |
| Blank cells | 0 |
| Duplicate rows | 33 across 5 files. Remove in cleaning |
| Prices over 300 c/L | 0 |
| Prices under 100 c/L | 1,696. Mostly LPG (1,477), which is realistic. 219 in other fuels are likely errors |

**Date formats:** Excel files hold real dates. CSVs use either `2024-07-01 00:04:36` (ISO) or `1/06/2025 0:08` (day-first). `parse_dates` detects which.

**Low price rule:** for E10, U91, P95, P98, DL and PDL, prices under 100 c/L are flagged as outliers. They stay in `raw`, are flagged in `staging` and are excluded from `reporting`. LPG is not flagged.

## FuelCheck API (current prices)

First test on 17 Nov 2026: **3,287 stations, 10,557 prices** in one call to `/FuelPriceCheck/v1/fuel/prices`.

The response has two lists, joined on `prices.stationcode` = `stations.code`.

**`stations`**

| Field | Example | Notes |
|---|---|---|
| `code` | `972` | Join key. Text, not number |
| `name` | United Petroleum Umina | |
| `brand` | United | |
| `address` | 307-313 Ocean Beach Road, UMINA BEACH NSW 2257 | Suburb and postcode are inside the address, not separate fields |
| `location` | latitude, longitude | Not in the history files. Useful for maps |
| `stationid`, `brandid` | | Internal IDs, not needed |
| `isAdBlueAvailable` | False | Useful for diesel fleets |

**`prices`**

| Field | Example | Notes |
|---|---|---|
| `stationcode` | `1` | Join key |
| `fueltype` | `DL` | Same codes as history `FuelCode` |
| `price` | 269.9 | Cents per litre |
| `lastupdated` | 15/11/2026 19:00:27 | Day-first date format |

**API vs history files**

| | History files | API |
|---|---|---|
| One row = | A price change | Current price per station per fuel |
| Suburb / postcode | Separate columns | Inside `address` |
| Coordinates | No | Yes |

Each daily API snapshot repeats prices that haven't changed. Keeping only rows where `lastupdated` is new turns snapshots into price changes, matching the history files.

## Implications for the pipeline

- To get a daily price, carry each station's last known price forward until it changes.
- Add a `source_file` column to every row so it can be traced back.
- Keep raw files out of Git (`data/` is in `.gitignore`).
