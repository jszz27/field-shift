"""Pre-baked API responses for the demo sites, so the demo runs offline (plan §3.3).

build_snapshots.py saves each raw response to snapshots/<site>/<kind>.json.
With the environment variable OFFLINE=1, the clients read those files instead
of calling the network.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITES_FILE = ROOT / "data" / "demo_sites.json"
SNAPSHOT_DIR = ROOT / "snapshots"
MATCH_DEGREES = 0.005  # a point within this distance of a demo site uses its snapshot


def offline():
    return os.environ.get("OFFLINE") == "1"


def load_sites():
    return json.loads(SITES_FILE.read_text(encoding="utf-8"))


def site_for(lat, lon):
    for site in load_sites()["sites"]:
        if abs(site["lat"] - lat) < MATCH_DEGREES and abs(site["lon"] - lon) < MATCH_DEGREES:
            return site["id"]
    return None


def read(kind, lat, lon):
    """The saved response for a demo site; FileNotFoundError if there is none."""
    site = site_for(lat, lon)
    path = SNAPSHOT_DIR / str(site) / f"{kind}.json"
    if site is None or not path.exists():
        raise FileNotFoundError(f"Offline demo mode: only the demo fields have saved data "
                                f"(no '{kind}' snapshot for {lat}, {lon}). Pick a demo field.")
    return json.loads(path.read_text(encoding="utf-8"))


def write(site_id, kind, data):
    path = SNAPSHOT_DIR / site_id / f"{kind}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path
