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

## Data quality checks (to complete)

- [ ] Rows per file
- [ ] Number of stations per file
- [ ] Min/max `PriceUpdatedDate` per file (each file covers only its month?)
- [ ] Blank values per column
- [ ] Duplicate rows
- [ ] Extreme prices (e.g. below 100 c/L or above 300 c/L)
- [ ] Same columns across all 34 files

## Implications for the pipeline

- To get a daily price, carry each station's last known price forward until it changes.
- Add a `source_file` column to every row so it can be traced back.
- Keep raw files out of Git (`data/` is in `.gitignore`).
