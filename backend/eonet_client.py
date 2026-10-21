"""NASA EONET natural hazard events around a farm, as GeoJSON.

Context only: EONET coverage is sparse, so these events are never used in scoring.
"""
import json
from datetime import date
from pathlib import Path

import requests

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events/geojson"
CATEGORIES = ["drought", "floods", "severeStorms", "tempExtremes", "wildfires"]
BOX_DEGREES = 3.0
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def fetch_hazards(lat, lon, start="2015-01-01", end=None):
    """FeatureCollection of hazard events within ±BOX_DEGREES of the point."""
    lat, lon = round(lat, 2), round(lon, 2)
    end = end or date.today().isoformat()
    cache_file = CACHE_DIR / f"eonet_{lat}_{lon}_{start}_{end}.json"

    if cache_file.exists():
        data = json.loads(cache_file.read_text())
    else:
        resp = requests.get(EONET_URL, timeout=60, params={
            "category": ",".join(CATEGORIES),
            "status": "all",  # default returns only currently open events
            "start": start,
            "end": end,
            # upper-left (lon, lat), then lower-right (lon, lat)
            "bbox": f"{lon - BOX_DEGREES},{lat + BOX_DEGREES},{lon + BOX_DEGREES},{lat - BOX_DEGREES}",
        })
        resp.raise_for_status()
        data = resp.json()
        cache_file.write_text(json.dumps(data))

    # Prescribed burns are planned land management, not hazards
    features = [f for f in data["features"] if "prescribed" not in f["properties"]["title"].lower()]
    return {"type": "FeatureCollection", "features": sorted(features, key=lambda f: f["properties"]["date"])}


if __name__ == "__main__":
    # Ames, Iowa: the primary demo location
    hazards = fetch_hazards(42.03, -93.62)
    print(f"{len(hazards['features'])} hazard events:")
    for f in hazards["features"]:
        p = f["properties"]
        print(f"  {p['date'][:10]}  {p['categories'][0]['id']:<10} {p['title']}")
