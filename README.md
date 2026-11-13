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
| [FuelCheck price history](https://data.nsw.gov.au/data/dataset/fuel-check) (NSW Fair Trading) | Historical prices back to 2016 | Monthly XLSX/CSV files |
| [FuelCheck API](https://api.nsw.gov.au/Product/Index/22) (API NSW) | Daily current prices | JSON API |

FuelCheck data is licensed under Creative Commons Attribution Share-Alike 3.0 Australia.

## Pipeline (planned)

| Stage | Tool |
|---|---|
| Extract | Python |
| Load | Google BigQuery (`raw` → `staging` → `reporting`) |
| Transform | dbt |
| Schedule | GitHub Actions (daily) |
| Visualise | Power BI |

## Status

🚧 In progress: project setup and data exploration.
