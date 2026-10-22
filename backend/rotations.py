"""Generate every crop rotation and filter it with agronomic rules (plan §4.2).

A rotation is a repeating cycle of cash crops, one per harvest year, so the
last year is followed by the first. Each rejection names the rule it broke:
  repeat  - an annual crop grown two years in a row
  stand   - a perennial (alfalfa) stand shorter or longer than its stand_years
  timing  - a fall-planted crop (winter wheat) after a crop harvested too late
Two different crops from the same family in a row (e.g. oats -> corn) are
allowed here and penalized by the Diversity score instead (Step 8), since
small grain -> corn is a standard Corn Belt rotation. Crops and their
season windows come from the region pack (crops.py). Cover crops fill
the fall-to-spring gap when the previous crop is harvested at least
min_days_before_first_frost before the first fall frost. Soil suitability is
not checked yet.
"""
import itertools

import pandas as pd

from climate_shift import compare_periods, day_of_year_to_date, yearly_indicators
from crops import crops_for_pack
from power_client import fetch_power_daily

ROTATION_YEARS = (2, 3, 4, 5)  # 2 for corn-soybean, the plan's demo rotation


def day_of_year(mm_dd):
    return pd.Timestamp(f"2001-{mm_dd}").dayofyear


def typical_harvest(crop, region):
    """Day of year in the middle of the most-active harvest window."""
    start, end = crop["season_windows"][region]["harvest"]
    return (day_of_year(start) + day_of_year(end)) // 2


def fall_planted(crop, region):
    plant = crop["season_windows"][region]["plant"]
    return plant is not None and day_of_year(plant[0]) >= day_of_year("08-01")


def is_canonical(seq):
    """True for one representative per cycle; shifted copies and pure repeats return False."""
    return all(seq < seq[i:] + seq[:i] for i in range(1, len(seq)))


def runs(seq):
    """(crop, years) runs around the cycle, starting where the crop changes."""
    start = next((i for i in range(len(seq)) if seq[i] != seq[i - 1]), 0)
    return [(crop, len(list(g))) for crop, g in itertools.groupby(seq[start:] + seq[:start])]


def transitions(seq):
    return list(zip(seq, seq[1:] + seq[:1]))


def check(seq, crops, region):
    """Reasons the rotation breaks a rule; empty means it is valid."""
    reasons = []
    for crop_id, years in runs(seq):
        crop = crops[crop_id]
        if crop["type"] == "perennial":
            lo, hi = crop["stand_years"]
            if not lo <= years <= hi:
                reasons.append(f"stand: {crop['name']} for {years} yr (needs {lo}-{hi})")
        elif years > 1:
            reasons.append(f"repeat: {crop['name']} {years} years in a row")

    for a_id, b_id in transitions(seq):
        if a_id == b_id:
            continue
        a, b = crops[a_id], crops[b_id]
        if fall_planted(b, region):
            harvest = typical_harvest(a, region)
            plant_end = day_of_year(b["season_windows"][region]["plant"][1])
            if harvest > plant_end:
                reasons.append(f"timing: {a['name']} harvest ~{day_of_year_to_date(harvest)} is after "
                               f"{b['name']} planting ends {day_of_year_to_date(plant_end)}")
    return list(dict.fromkeys(reasons))  # a cycle can hit the same rule twice


def cover_options(a_id, b_id, crops, region, first_fall_frost):
    """Cover crops that fit the gap after crop a, when b is planted the next spring."""
    a, b = crops[a_id], crops[b_id]
    if a_id == b_id or first_fall_frost is None or fall_planted(b, region):
        return []  # inside a perennial stand, no frost (tropical pack), or no fall-to-spring gap
    harvest = typical_harvest(a, region)
    return [c["id"] for c in crops.values()
            if c["type"] == "cover" and c["cover"]["min_days_before_first_frost"] is not None
            and harvest <= first_fall_frost - c["cover"]["min_days_before_first_frost"]]


def generate(region, first_fall_frost):
    """All valid rotations (with cover options per gap) and all rejected ones with reasons."""
    crops = crops_for_pack(region)
    pool = sorted(c["id"] for c in crops.values() if c["type"] != "cover")
    valid, rejected = [], []
    for n in ROTATION_YEARS:
        for seq in itertools.product(pool, repeat=n):
            if not is_canonical(seq):
                continue
            reasons = check(seq, crops, region)
            if reasons:
                rejected.append({"rotation": seq, "reasons": reasons})
            else:
                covers = [cover_options(a, b, crops, region, first_fall_frost) for a, b in transitions(seq)]
                valid.append({"rotation": seq, "covers": covers})
    return {
        "pool": pool,
        "valid": valid,
        "rejected": rejected,
    }


if __name__ == "__main__":
    # Ames, Iowa: the primary demo location
    lat = 42.03
    table = compare_periods(yearly_indicators(fetch_power_daily(lat, -93.62), lat))
    frost_then, frost_now = (round(table.loc["first_fall_frost", p]) for p in ("then", "now"))
    result = generate("us_midwest", frost_now)

    print(f"\nCrops used: {result['pool']}")
    print(f"First fall frost: then {day_of_year_to_date(frost_then)}, now {day_of_year_to_date(frost_now)}")
    print(f"\n{len(result['valid'])} valid, {len(result['rejected'])} rejected")

    print("\nValid rotations (cover options after each year):")
    for r in result["valid"]:
        gaps = "  ".join(f"{crop}[{','.join(c) or '-'}]" for crop, c in zip(r["rotation"], r["covers"]))
        print(f"  {gaps}")

    print("\nRejections by rule (a rotation can break several):")
    counts = pd.Series([reason.split(":")[0] for r in result["rejected"] for reason in r["reasons"]]).value_counts()
    print(counts.to_string())
