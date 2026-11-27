"""Build the Greater Sydney postcode list (a dbt seed) from two ABS files.

The ABS doesn't publish a "postcode -> Greater Sydney" list, but two files
link through mesh blocks (the smallest ABS area, a few dozen homes each):
  MB_2021_AUST.xlsx   mesh block -> GCCSA (Greater Sydney or not) and SA4
  POA_2021_AUST.xlsx  mesh block -> postcode

Rule for postcodes on the boundary: a postcode counts as Greater Sydney if
most (50% or more) of its mesh blocks are inside Greater Sydney.

Run from the repo folder:  python scripts/build_sydney_postcodes.py
Output: dbt/seeds/greater_sydney_postcodes.csv
"""
from pathlib import Path

import pandas as pd

REF_DIR = Path("data/reference")
MB_FILE = REF_DIR / "MB_2021_AUST.xlsx"
POA_FILE = REF_DIR / "POA_2021_AUST.xlsx"
OUTPUT = Path("dbt/seeds/greater_sydney_postcodes.csv")

GREATER_SYDNEY = "1GSYD"  # ABS code for the Greater Sydney GCCSA
MIN_SHARE = 0.5           # share of a postcode's mesh blocks that must be inside


def check(passed, message):
    """Print the result of a check, and stop the script if it failed."""
    print(("PASS  " if passed else "FAIL  ") + message)
    if not passed:
        raise SystemExit("Stopped: a check failed. Nothing was saved.")


# 1. Read only the columns needed (codes as text, so leading zeros are kept)
print("Reading ABS files (this can take a minute or two)...")
mesh_blocks = pd.read_excel(MB_FILE, dtype=str,
                            usecols=["MB_CODE_2021", "GCCSA_CODE_2021", "SA4_NAME_2021"])
postcodes = pd.read_excel(POA_FILE, dtype=str, usecols=["MB_CODE_2021", "POA_CODE_2021"])
print(f"Mesh blocks: {len(mesh_blocks):,}   Postcode links: {len(postcodes):,}")

# 2. Join on mesh block, so every mesh block has a postcode and a GCCSA
joined = postcodes.merge(mesh_blocks, on="MB_CODE_2021", how="inner")
joined["in_greater_sydney"] = joined["GCCSA_CODE_2021"] == GREATER_SYDNEY

# 3. For each postcode, the share of its mesh blocks inside Greater Sydney
summary = (joined.groupby("POA_CODE_2021")["in_greater_sydney"]
           .agg(mesh_blocks="size", inside="sum")
           .reset_index())
summary["greater_sydney_share"] = (summary["inside"] / summary["mesh_blocks"]).round(3)

# 4. Keep postcodes that are mostly inside Greater Sydney
seed = summary[summary["greater_sydney_share"] >= MIN_SHARE].copy()

# 5. SA4 for each postcode: the SA4 most of its Greater Sydney mesh blocks are in
sa4 = (joined[joined["in_greater_sydney"]]
       .groupby("POA_CODE_2021")["SA4_NAME_2021"]
       .agg(lambda names: names.value_counts().index[0])
       .rename("sa4_name"))
seed = seed.merge(sa4, left_on="POA_CODE_2021", right_index=True, how="left")
seed = (seed.rename(columns={"POA_CODE_2021": "postcode"})
        [["postcode", "sa4_name", "greater_sydney_share"]]
        .sort_values("postcode"))

# 6. Report boundary postcodes, so the rule's effect is visible
partial = summary[(summary["greater_sydney_share"] > 0) & (summary["greater_sydney_share"] < 1)]
print(f"\nBoundary postcodes (partly inside): {len(partial)}")
print(partial.sort_values("greater_sydney_share", ascending=False)
      [["POA_CODE_2021", "mesh_blocks", "greater_sydney_share"]].to_string(index=False))

# 7. Sanity checks on well-known postcodes
codes = set(seed["postcode"])
print("\nChecks:")
check(len(seed) > 100, f"{len(seed)} Greater Sydney postcodes found")
check("2000" in codes, "2000 (Sydney CBD) included")
check("2150" in codes, "2150 (Parramatta) included")
check("2257" in codes, "2257 (Central Coast, Umina Beach) included")
check("2780" in codes, "2780 (Blue Mountains, Katoomba) included")
check("2300" not in codes, "2300 (Newcastle) excluded")
check("2500" not in codes, "2500 (Wollongong) excluded")
check(seed["sa4_name"].notna().all(), "Every postcode has an SA4 name")

# 8. Save as a dbt seed
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
seed.to_csv(OUTPUT, index=False)
print(f"\nSaved {len(seed)} postcodes to {OUTPUT}")
print("\nPostcodes per SA4:")
print(seed["sa4_name"].value_counts().to_string())
