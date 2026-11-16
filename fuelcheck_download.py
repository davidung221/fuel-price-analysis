import requests
from pathlib import Path

url = "https://data.nsw.gov.au/data/api/3/action/package_show"
resources = requests.get(url, params={"id": "fuel-check"}, timeout=30).json()["result"]["resources"]

out = Path("data/raw")
out.mkdir(parents=True, exist_ok=True)

for r in resources:
    if any(year in r["name"] for year in ["2024", "2025", "2026"]):
        file = out / Path(r["url"]).name
        if not file.exists():
            file.write_bytes(requests.get(r["url"], timeout=60).content)
            print("Downloaded", file.name)

