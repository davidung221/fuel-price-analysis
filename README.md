# NSW Fuel Price Pipeline

An automated data pipeline that collects NSW fuel prices daily and answers a practical question:

> **When and where should NSW drivers and small fleet businesses buy fuel, and how much does it save?**

## Questions

- Which day of the week is cheapest, in Sydney and regional NSW?
- How long is the price cycle, and when does it hit its low point?
- Which suburbs and brands are consistently cheapest?
- Does diesel follow the same pattern as petrol?
- How much can a driver save per tank, and a small fleet per month?

## Data sources

| Source | Use | Format |
|---|---|---|
| [FuelCheck price history](https://data.nsw.gov.au/data/dataset/fuel-check) (NSW Fair Trading) | Every price change, Nov 2024 – Oct 2026 | Monthly XLSX/CSV files |
| [FuelCheck API](https://api.nsw.gov.au/Product/Index/22) (API NSW) | Current prices, collected daily | JSON API |

FuelCheck data is licensed under Creative Commons Attribution Share-Alike 3.0 Australia.

## Pipeline

```
Built:
  History files (XLSX/CSV) --> Python: profile, combine --> BigQuery raw.fuel_price_history
  FuelCheck API (daily)    --> Python: extract, check   --> BigQuery raw.api_stations, raw.api_prices

Planned:
  GitHub Actions (daily schedule) --> runs the extract
  BigQuery raw --> dbt --> staging --> reporting --> Power BI
```

| Stage | Tool | Status |
|---|---|---|
| Extract | Python (`requests`, `pandas`) | ✅ |
| Load | Google BigQuery (`raw` → `staging` → `reporting`) | ✅ raw · ⬜ staging, reporting |
| Schedule | GitHub Actions (daily) | ⬜ |
| Transform | dbt | ⬜ |
| Visualise | Power BI | ⬜ |

## BigQuery tables

All in `australia-southeast1` (Sydney).

| Table | One row = | Status |
|---|---|---|
| `raw.fuel_price_history` | A price change from the history files | ✅ Loaded |
| `raw.api_stations` | A station on a snapshot date | ✅ Loading daily (manual for now) |
| `raw.api_prices` | A station + fuel price on a snapshot date | ✅ Loading daily (manual for now) |

Column details, data quality results and time zone notes: [`docs/data_notes.md`](docs/data_notes.md).

## Repository structure

```
scripts/
  read_history.py        Read any history file (CSV/XLSX, either header layout)
  profile_history.py     Data quality profile of every history file
  combine_history.py     Combine 24 in-scope months into one Parquet file
  load_history_to_bq.py  Load the combined history into BigQuery
  fuel_api.py            Shared FuelCheck API functions (token, requests)
  test_api.py            First API connection test
  profile_api.py         Field-by-field profile of the API response
  extract_prices.py      Daily extract: API -> checks -> BigQuery
  test_bigquery.py       BigQuery connection test
docs/
  data_notes.md          Data dictionary, quality checks, decisions
  history_profile.csv    Profile results for the history files
data/                    Local data files (not committed)
```

## Key decisions

- **Scope: 24 months** (Nov 2024 – Oct 2026). The question is about buying fuel now, and older files use different layouts.
- **Raw stays as received.** Duplicates, outliers and text clean-up are handled in `staging`, so cleaning rules can change without reloading data.
- **Flag, don't delete.** Suspicious prices (e.g. under 100 c/L for petrol and diesel) are flagged, not removed.
- **Time zones:** history files use Sydney time, the API uses UTC. Both are converted to Sydney time in staging.
- **Checks before every load.** Scripts stop without loading if row counts, blanks or joins look wrong.

## Known limitations

- A daily API snapshot captures each station's latest price at that time. Multiple changes in one day are only in the monthly history files.
- Some API prices haven't been updated for years (oldest: June 2018). A staleness cutoff will be set during analysis.
- EV charging prices appear in the data but aren't fuel; they're excluded from the analysis.
