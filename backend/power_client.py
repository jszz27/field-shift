"""Fetch NASA POWER daily point data, with a local file cache.

POWER asks users not to repeat requests for the same location, so every
response is saved in cache/ keyed by rounded coordinates and date range.
"""
import json
from pathlib import Path

import pandas as pd
import requests

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = [
    "T2M", "T2M_MAX", "T2M_MIN",  # air temperature at 2 m (°C)
    "PRECTOTCORR",                 # precipitation (mm/day)
    "RH2M", "WS2M",                # relative humidity (%), wind speed (m/s)
    "ALLSKY_SFC_SW_DWN",           # solar radiation (MJ/m²/day)
    "GWETTOP", "GWETROOT",         # soil wetness 0–1 (surface, root zone)
]
FILL_VALUE = -999.0
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def fetch_power_daily(lat, lon, start="19810101", end="20241231"):
    """Return a DataFrame of daily POWER values, one row per date."""
    lat, lon = round(lat, 2), round(lon, 2)
    cache_file = CACHE_DIR / f"power_{lat}_{lon}_{start}_{end}.json"

    if cache_file.exists():
        print(f"Cache hit: {cache_file.name}")
        data = json.loads(cache_file.read_text())
    else:
        print("Fetching from NASA POWER...")
        resp = requests.get(POWER_URL, timeout=120, params={
            "parameters": ",".join(PARAMETERS),
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "start": start,
            "end": end,
            "format": "JSON",
        })
        resp.raise_for_status()
        data = resp.json()
        cache_file.write_text(json.dumps(data))

    df = pd.DataFrame(data["properties"]["parameter"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.replace(FILL_VALUE, float("nan"))
    df.attrs["elevation_m"] = data["geometry"]["coordinates"][2]
    return df


if __name__ == "__main__":
    # Ames, Iowa: the primary demo location
    df = fetch_power_daily(42.03, -93.62)
    print(f"\n{len(df):,} days, {df.index.min().date()} to {df.index.max().date()}")
    print("\nMissing values per parameter:")
    print(df.isna().sum().to_string())
    print("\nSummary:")
    print(df.describe().round(2).to_string())
