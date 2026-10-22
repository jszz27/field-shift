"""Pre-bake JSON snapshots for every demo site so the demo runs offline (plan §3.3).

For each site in data/demo_sites.json, saves to snapshots/<site>/:
  power.json, ssurgo.json or soilgrids.json, eonet.json - raw API responses,
      read back by the clients when OFFLINE=1
  climate_shift.json - zone, then-vs-now table and per-year indicators
  et0.json           - annual ET0 totals and mean daily ET0 by month, then vs now
  soil.json          - soil profile used by the recommender
  hazards.json       - EONET events after filtering (context only)
EONET uses the fixed snapshot_end date so rebuilding gives the same files.
"""
import json
import sys

import snapshots
from climate_shift import NOW, THEN, compare_periods, yearly_indicators
from eonet_client import fetch_hazards, fetch_hazards_raw
from et0 import daily_et0
from power_client import fetch_power_daily, fetch_power_raw
from soil_client import fetch_soilgrids_raw, fetch_ssurgo_raw, get_soil

SOIL_RAW = {"ssurgo": fetch_ssurgo_raw, "soilgrids": fetch_soilgrids_raw}


def frame_to_json(df):
    return json.loads(df.to_json(orient="index"))  # NaN -> null


def et0_summary(df, lat):
    et0 = daily_et0(df, lat)
    by_period = {
        name: et0.loc[str(start):str(end)].groupby(lambda d: d.month).mean().round(2).tolist()
        for name, (start, end) in (("then", THEN), ("now", NOW))
    }
    return {
        "annual_mm": frame_to_json(et0.groupby(et0.index.year).sum(min_count=365).round(1).to_frame("et0")),
        "monthly_mean_mm_per_day": by_period,
    }


def build(site, snapshot_end):
    lat, lon, site_id = site["lat"], site["lon"], site["id"]
    snapshots.write(site_id, "power", fetch_power_raw(lat, lon))
    df = fetch_power_daily(lat, lon)

    yearly = yearly_indicators(df, lat)
    table = compare_periods(yearly)
    if table.attrs["zone"] != site["zone"]:
        print(f"  WARNING: {site_id} classified as {table.attrs['zone']}, config says {site['zone']}")
    snapshots.write(site_id, "climate_shift", {
        **table.attrs, "then": THEN, "now": NOW,
        "indicators": frame_to_json(table.round(2)), "yearly": frame_to_json(yearly.round(2)),
    })
    snapshots.write(site_id, "et0", et0_summary(df, lat))

    soil_raw = SOIL_RAW[site["soil_source"]](lat, lon)
    if soil_raw is None:
        sys.exit(f"{site_id}: {site['soil_source']} has no data for this point")
    snapshots.write(site_id, site["soil_source"], soil_raw)
    snapshots.write(site_id, "soil", get_soil(lat, lon))

    snapshots.write(site_id, "eonet", fetch_hazards_raw(lat, lon, end=snapshot_end))
    hazards = fetch_hazards(lat, lon, end=snapshot_end)
    snapshots.write(site_id, "hazards", hazards)
    print(f"  {site_id}: zone {table.attrs['zone']}, soil {site['soil_source']}, "
          f"{len(hazards['features'])} hazard events")


if __name__ == "__main__":
    if snapshots.offline():
        sys.exit("Unset OFFLINE to build snapshots: they must come from the live APIs.")
    config = snapshots.load_sites()
    print(f"Building snapshots (EONET end date {config['snapshot_end']}):")
    for site in config["sites"]:
        build(site, config["snapshot_end"])
