"""Soil profile for a point: SSURGO (US), SoilGrids (global), or a manual texture fallback.

Texture and organic matter describe the topsoil (0–30 cm); available water
capacity (AWC) describes the root zone (0–100 cm), in mm of water per m of soil.
"""
import json
from pathlib import Path

import pandas as pd
import requests

import snapshots

SDA_URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
SOILGRIDS_PROPERTIES = ["clay", "sand", "silt", "soc", "wv0033", "wv1500"]
SOILGRIDS_DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm"]
OC_TO_OM = 1.724  # Van Bemmelen factor: organic matter = 1.724 x organic carbon
TOPSOIL_CM = 30
ROOT_ZONE_CM = 100
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

# FAO-56 Table 19: midpoint of the (θFC − θWP) range, in mm/m
FAO56_AWC_MM_PER_M = {
    "sand": 80, "loamy sand": 90, "sandy loam": 130, "loam": 155, "silt loam": 160,
    "silt": 180, "silty clay loam": 155, "silty clay": 160, "clay": 160,
}


def texture_class(sand, silt, clay):
    """USDA soil texture class from sand/silt/clay percentages (NRCS triangle rules)."""
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 2 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52) or (clay < 7 and silt < 50):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if silt >= 50 and clay < 27:
        return "silt loam"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if 27 <= clay < 40 and sand > 20:
        return "clay loam"
    if 27 <= clay < 40:
        return "silty clay loam"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


def depth_weighted(horizons, column, max_depth_cm):
    """Thickness-weighted mean of a column over 0..max_depth_cm, skipping empty values."""
    h = horizons[horizons[column].notna()]
    thickness = h["bottom_cm"].clip(upper=max_depth_cm) - h["top_cm"].clip(upper=max_depth_cm)
    return float((h[column] * thickness).sum() / thickness.sum())


def fetch_ssurgo_raw(lat, lon):
    """Soil Data Access JSON for the dominant soil component, or None outside SSURGO coverage."""
    lat, lon = round(float(lat), 4), round(float(lon), 4)
    if snapshots.offline():
        return snapshots.read("ssurgo", lat, lon)
    cache_file = CACHE_DIR / f"soil_ssurgo_{lat}_{lon}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    query = f"""
        SELECT c.compname, c.drainagecl, h.hzdept_r, h.hzdepb_r,
               h.sandtotal_r, h.silttotal_r, h.claytotal_r, h.awc_r, h.om_r
        FROM component c JOIN chorizon h ON h.cokey = c.cokey
        WHERE c.cokey = (
            SELECT TOP 1 c2.cokey FROM component c2
            WHERE c2.mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({lon} {lat})'))
            ORDER BY c2.comppct_r DESC)
        ORDER BY h.hzdept_r"""
    resp = requests.post(SDA_URL, timeout=60, json={"format": "JSON+COLUMNNAME", "query": query})
    resp.raise_for_status()
    data = resp.json()
    if not data.get("Table"):
        return None
    cache_file.write_text(json.dumps(data))
    return data


def ssurgo_profile(lat, lon):
    data = fetch_ssurgo_raw(lat, lon)
    if data is None:
        return None
    header, *rows = data["Table"]
    layers = pd.DataFrame(rows, columns=header)
    numeric = ["hzdept_r", "hzdepb_r", "sandtotal_r", "silttotal_r", "claytotal_r", "awc_r", "om_r"]
    layers[numeric] = layers[numeric].apply(pd.to_numeric)
    layers = layers.rename(columns={"hzdept_r": "top_cm", "hzdepb_r": "bottom_cm"})
    sand, silt, clay = (depth_weighted(layers, c, TOPSOIL_CM)
                        for c in ("sandtotal_r", "silttotal_r", "claytotal_r"))
    return {
        "source": "SSURGO",
        "name": layers["compname"].iloc[0],
        "texture_class": texture_class(sand, silt, clay),
        "sand_pct": round(sand, 1), "silt_pct": round(silt, 1), "clay_pct": round(clay, 1),
        "organic_matter_pct": round(depth_weighted(layers, "om_r", TOPSOIL_CM), 2),
        "awc_mm_per_m": round(depth_weighted(layers, "awc_r", ROOT_ZONE_CM) * 1000),  # cm/cm -> mm/m
        "drainage": layers["drainagecl"].iloc[0],
    }


def fetch_soilgrids_raw(lat, lon):
    """SoilGrids 2.0 point query JSON (mean predictions, 0–100 cm)."""
    lat, lon = round(float(lat), 4), round(float(lon), 4)
    if snapshots.offline():
        return snapshots.read("soilgrids", lat, lon)
    cache_file = CACHE_DIR / f"soil_soilgrids_{lat}_{lon}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    resp = requests.get(SOILGRIDS_URL, timeout=60, params={
        "lat": lat, "lon": lon, "property": SOILGRIDS_PROPERTIES, "depth": SOILGRIDS_DEPTHS, "value": "mean",
    })
    resp.raise_for_status()
    data = resp.json()
    cache_file.write_text(json.dumps(data))
    return data


def soilgrids_profile(lat, lon):
    """Profile from SoilGrids, or None where the pixel is masked (towns, water)."""
    data = fetch_soilgrids_raw(lat, lon)
    rows = {}
    for layer in data["properties"]["layers"]:
        for depth in layer["depths"]:
            key = (depth["range"]["top_depth"], depth["range"]["bottom_depth"])
            mean = depth["values"]["mean"]
            rows.setdefault(key, {})[layer["name"]] = None if mean is None else mean / layer["unit_measure"]["d_factor"]
    layers = pd.DataFrame([{"top_cm": t, "bottom_cm": b, **v} for (t, b), v in sorted(rows.items())])
    if layers[SOILGRIDS_PROPERTIES].isna().all().all():
        return None
    # After d_factor: clay/sand/silt in %, soc in g/kg, wv0033/wv1500 in volume %
    layers["awc_mm_per_m"] = (layers["wv0033"] - layers["wv1500"]) * 10
    sand, silt, clay = (depth_weighted(layers, c, TOPSOIL_CM) for c in ("sand", "silt", "clay"))
    return {
        "source": "SoilGrids 2.0",
        "name": None,
        "texture_class": texture_class(sand, silt, clay),
        "sand_pct": round(sand, 1), "silt_pct": round(silt, 1), "clay_pct": round(clay, 1),
        "organic_matter_pct": round(depth_weighted(layers, "soc", TOPSOIL_CM) / 10 * OC_TO_OM, 2),
        "awc_mm_per_m": round(depth_weighted(layers, "awc_mm_per_m", ROOT_ZONE_CM)),
        "drainage": None,
    }


def manual_profile(texture, organic_matter_pct=None):
    """Fallback when no soil service covers the point: the user picks a texture class."""
    return {
        "source": "manual (FAO-56 Table 19)",
        "texture_class": texture,
        "organic_matter_pct": organic_matter_pct,
        "awc_mm_per_m": FAO56_AWC_MM_PER_M[texture],
        "drainage": None,
    }


def get_soil(lat, lon):
    """Best available profile (SSURGO, then SoilGrids), or None so the UI can ask for manual input."""
    for source in (ssurgo_profile, soilgrids_profile):
        try:
            profile = source(lat, lon)
        except (requests.RequestException, FileNotFoundError) as err:
            print(f"Soil source failed: {err}")
            continue
        if profile:
            return profile
    return None


if __name__ == "__main__":
    for name, lat, lon in [("Ames, IA", 42.03, -93.62), ("Western Kansas", 38.87, -101.0),
                           ("Machakos, Kenya", -1.52, 37.26), ("Niamey area, Niger", 13.51, 2.16)]:
        print(f"{name}: {get_soil(lat, lon)}")
    print(f"Manual fallback: {manual_profile('silt loam')}")
