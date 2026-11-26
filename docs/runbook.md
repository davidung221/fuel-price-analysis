# Runbook: Daily Fuel Price Extract

What to check, and what to do when the daily extract fails.

## How it runs

| Item | Detail |
|---|---|
| Workflow | `.github/workflows/daily_extract.yml` ("Daily fuel price extract") |
| Schedule | 10:17 UTC daily = 9:17 pm Sydney (AEDT) / 8:17 pm (AEST). GitHub may start it 10–60 min late |
| Script | `scripts/extract_prices.py` |
| Loads | `raw.api_stations`, `raw.api_prices` (BigQuery, `australia-southeast1`) |
| Secrets | `FUEL_API_KEY`, `FUEL_API_SECRET`, `GCP_PROJECT_ID`, `GCP_SA_KEY` |
| Alerts | GitHub emails the repo owner when a run fails |

## Routine check (weekly, 2 minutes)

```bash
gh run list --workflow=daily_extract.yml --limit 7
```
All 7 runs should show a green tick and the `schedule` event.

```sql
SELECT snapshot_date, COUNT(*) AS price_rows
FROM `raw.api_prices`
WHERE snapshot_date >= DATE_SUB(CURRENT_DATE('Australia/Sydney'), INTERVAL 7 DAY)
GROUP BY snapshot_date
ORDER BY snapshot_date;
```
There should be one row per day, each with about 10,500 prices.

## When a run fails

1. Open the failed run: **Actions** tab, or `gh run list --workflow=daily_extract.yml --limit 3`.
2. Find the failing lines:
   ```bash
   gh run view <run-id> --log | grep -E "PASS|FAIL|removed|Done|Error"
   ```
3. Use the table below to find the cause.
4. Fix it, then re-run: `gh workflow run daily_extract.yml`. Re-running is safe: today's rows are replaced, never duplicated.

| Where it failed | Likely cause | Fix |
|---|---|---|
| **Install packages** | Package version problem | Check `requirements.txt` installs locally; update and push |
| **Log in to Google Cloud** | `GCP_SA_KEY` missing, wrong or deleted | Create a new key, update the secret (see below) |
| `401` / `403` from the API | API key or secret wrong or expired | Check the app on api.nsw.gov.au, update the secrets |
| `500` / `503` / timeout from the API | API outage | Wait, then re-run manually the same evening |
| `429` from the API | Too many calls | Check nothing else is using the key; re-run later |
| `FAIL` in pre-load checks | API returned unusual data | Read which check failed. **Nothing was loaded.** Investigate before re-running |
| `KeyError: 'GCP_PROJECT_ID'` | Secret missing or misnamed | `gh secret list`, then re-add it |
| `403 Access Denied` from BigQuery | Service account roles changed | Check it has BigQuery Data Editor and BigQuery Job User |

## Missed days

- The API only returns **current** prices, so a missed day can't be re-run later. Re-running the next day creates the next day's snapshot.
- Re-run **before midnight Sydney time** to keep the snapshot for that date.
- The monthly history files still contain every price change, so the gap only affects the daily snapshot table.
- Record missed days here:

| Date | Reason |
|---|---|
| | |

## Pause or resume the schedule

```bash
gh workflow disable daily_extract.yml   # pause
gh workflow enable daily_extract.yml    # resume
```
GitHub pauses schedules in public repos after **60 days with no commits** and emails first. Resume with the enable command, or push any commit.

## Update credentials

**API key or secret** (after regenerating on api.nsw.gov.au):
1. Update `.env`.
2. Re-run the matching `gh secret set` command, e.g.:
   ```bash
   gh secret set FUEL_API_KEY --body "$(grep '^FUEL_API_KEY=' .env | cut -d= -f2-)"
   ```

**Service account key:**
1. Google Cloud console → **IAM & Admin** → **Service Accounts** → `fuel-pipeline-loader` → **Keys** → create a new JSON key.
2. Move it to `~/.config/gcp/fuel-pipeline-key.json` and run `chmod 600` on it.
3. Update the secret:
   ```bash
   python -c "import json, sys; print(json.dumps(json.load(open(sys.argv[1]))))" ~/.config/gcp/fuel-pipeline-key.json | gh secret set GCP_SA_KEY
   ```
4. Run the workflow manually to test, then **delete the old key** in the console.

## Known behaviour

- **Daylight saving:** the run time moves between 9:17 pm (summer) and 8:17 pm (winter), because cron uses UTC.
- **Station count changes daily** (e.g. 3,282 → 3,290). This is normal: stations open, close or start or stop reporting.
- **Delete-then-append:** if a run fails after deleting today's rows but before loading, today has no rows until the next successful run. Re-run manually.
