"""Crop knowledge base: a shared crop library plus region packs (data/crops.json).

validate() checks required fields, enums, value ranges and that every
non-null value names a known source. missing() lists the null fields still
to research. crops_for_pack() merges the library with one pack's local
timing, in the shape the rotation generator reads.
"""
import json
import re
from pathlib import Path

CROPS_FILE = Path(__file__).resolve().parent.parent / "data" / "crops.json"

FAMILIES = {"grass", "legume", "brassica", "aster", "spurge"}
TYPES = {"cash", "cover", "perennial"}
ZONES = {"north_temperate", "south_temperate", "tropical"}
ENUMS = {
    "n_effect": {"fixes", "neutral", "heavy_feeder"},
    "n_season": {"warm", "cool"},
    "residue_cover": {"low", "medium", "high"},
    "kind": {"failure", "yield_reduction"},
    "event": {"onset", "end"},
}

REQUIRED = ["name", "family", "type", "kc", "rooting_depth_m", "depletion_p", "n_effect", "residue_cover", "sources"]
REQUIRED_GROWN = ["ky", "drought_tolerance", "base_temp_c", "gdd_required", "heat", "n_season", "soil_preferences"]
REQUIRED_PACK = {"temperate": ["plant", "harvest", "stage_days"], "tropical": ["plant_after", "stage_days"]}

# Allowed range for every number inside a field (a [low, high] pair must also be ascending)
RANGES = {
    "kc": (0, 1.5), "rooting_depth_m": (0, 3), "depletion_p": (0, 1), "ky": (0, 2),
    "drought_tolerance": (1, 5), "base_temp_c": (-5, 20), "gdd_required": (0, 5000),
    "heat": (20, 50), "stand_years": (1, 10), "soil_preferences": (3, 10), "cover": (0, 120),
    "stage_days": (1, 400), "n_need_kg_ha": (0, 400), "next_crop_n_adjust_kg_ha": (-300, 300),
    "plant_after": (0, 120),
}
NOT_DATA = {"name", "type", "sources"}  # fields that need no source


def load(path=CROPS_FILE):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        raise ValueError("crops.json is invalid:\n  " + "\n  ".join(errors))
    return data


def numbers(value):
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, dict):
        return [n for v in value.values() for n in numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in numbers(v)]
    return []


def check_entry(where, entry, source_ids):
    """Source, range and enum checks shared by library crops and pack entries."""
    errors = []
    sources = entry.get("sources", {})
    for field, value in entry.items():
        if field in NOT_DATA or field.endswith("_note") or value is None:
            continue
        if sources.get(field) not in source_ids:
            errors.append(f"{where}.{field}: no valid source (got {sources.get(field)!r})")
        if field in RANGES:
            lo, hi = RANGES[field]
            errors += [f"{where}.{field}: {n} outside {lo}-{hi}" for n in numbers(value) if not lo <= n <= hi]
        for v in (value.values() if isinstance(value, dict) else [value]):
            if isinstance(v, list) and len(v) == 2 and len(numbers(v)) == 2 and v[0] > v[1]:
                errors.append(f"{where}.{field}: range {v} is not low-high")
        enum_values = {field: value} if not isinstance(value, dict) else value
        for key, v in enum_values.items():
            if key in ENUMS and v is not None and v not in ENUMS[key]:
                errors.append(f"{where}.{field}: {v!r} not in {sorted(ENUMS[key])}")
    return errors


def validate(data):
    """List of problems; empty means the file is valid."""
    errors = []
    source_ids = set(data.get("sources", {}))
    library = data.get("crops", {})

    for crop_id, crop in library.items():
        where = f"crops.{crop_id}"
        required = REQUIRED + (REQUIRED_GROWN if crop.get("type") != "cover" else ["cover"])
        if crop.get("type") == "perennial":
            required = required + ["stand_years"]
        errors += [f"{where}: missing field {f!r}" for f in required if f not in crop]
        if crop.get("family") not in FAMILIES:
            errors.append(f"{where}.family: {crop.get('family')!r} not in {sorted(FAMILIES)}")
        if crop.get("type") not in TYPES:
            errors.append(f"{where}.type: {crop.get('type')!r} not in {sorted(TYPES)}")
        errors += check_entry(where, crop, source_ids)

    for pack_id, pack in data.get("packs", {}).items():
        zone = pack.get("zone")
        if zone not in ZONES:
            errors.append(f"packs.{pack_id}.zone: {zone!r} not in {sorted(ZONES)}")
            continue
        required = REQUIRED_PACK["tropical" if zone == "tropical" else "temperate"]
        for crop_id, entry in pack.get("crops", {}).items():
            where = f"packs.{pack_id}.{crop_id}"
            if crop_id not in library:
                errors.append(f"{where}: crop not in library")
                continue
            if library[crop_id]["type"] != "cover":
                errors += [f"{where}: missing field {f!r}" for f in required if f not in entry]
            for field in ("plant", "harvest"):
                for mm_dd in entry.get(field) or []:
                    if not re.fullmatch(r"(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", mm_dd):
                        errors.append(f"{where}.{field}: {mm_dd!r} is not MM-DD")
            errors += check_entry(where, entry, source_ids)
    return errors


def missing(data):
    """Paths of every null value still to research (notes excluded)."""
    def walk(path, value):
        if value is None:
            return [path]
        if isinstance(value, dict):
            return [p for k, v in value.items() if not k.endswith("_note") for p in walk(f"{path}.{k}", v)]
        return []
    found = [p for crop_id, crop in data["crops"].items() for p in walk(f"crops.{crop_id}", crop)]
    for pack_id, pack in data["packs"].items():
        found += [p for crop_id, entry in pack["crops"].items()
                  for p in walk(f"packs.{pack_id}.{crop_id}", {k: v for k, v in entry.items() if k != "sources"})]
    return found


def crops_for_pack(pack_id, data=None):
    """Library crops in a pack, each with the pack's local entry and season_windows[pack_id]."""
    data = data or load()
    pack = data["packs"][pack_id]
    return {
        crop_id: {
            **data["crops"][crop_id], "id": crop_id, "pack": entry,
            "season_windows": {pack_id: {"plant": entry.get("plant"), "harvest": entry.get("harvest")}},
        }
        for crop_id, entry in pack["crops"].items()
    }


if __name__ == "__main__":
    data = load()
    print(f"crops.json v{data['version']}: valid, {len(data['crops'])} crops, {len(data['packs'])} packs")
    for pack_id, pack in data["packs"].items():
        print(f"\n{pack_id} ({pack['zone']})")
        print(f"  {'crop':<15}{'family':<10}{'n_effect':<14}{'drought':<9}{'kc_mid':<12}sources")
        for crop_id, crop in crops_for_pack(pack_id, data).items():
            used = sorted(set(crop["sources"].values()) | set(crop["pack"]["sources"].values()))
            kc_mid = crop["kc"]["mid"] if crop.get("kc") else None
            print(f"  {crop_id:<15}{crop['family']:<10}{str(crop['n_effect']):<14}"
                  f"{str(crop.get('drought_tolerance', '-')):<9}{str(kc_mid):<12}{', '.join(used)}")
    gaps = missing(data)
    print(f"\n{len(gaps)} null fields to research:")
    for path in gaps:
        print(f"  {path}")
