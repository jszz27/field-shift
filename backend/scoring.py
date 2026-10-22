"""Score rotations on the plan §4.3 indicators and explain the result (§4.4).

Each crop is run through every year of the NOW period with the site's daily
POWER weather:
  water_demand  - irrigation gap (mm/yr): FAO-56 Kc curve x ET0 through a
                  daily root-zone water balance; water is added whenever
                  depletion passes p x TAW (FAO-56 Ch. 8, eq. 85)
  climate_risk  - FAO-33 water-limited yield loss, ky x (1 - ETa/ETc), with
                  rainfed ETa from the FAO-56 stress coefficient Ks (eq. 84),
                  plus days in the mid-season stage above the crop's heat limit
Rotation-level indicators:
  n_balance     - fertilizer N (kg/ha/yr): pack N rate plus the previous
                  crop's credit; legumes need none
  soil_cover    - % of the cycle covered: crop or cover crop = 1, leftover
                  residue = RESIDUE_WEIGHT (team assumption)
  diversity     - distinct crops + distinct families
  simplicity    - distinct crops, +1 if a perennial needs hay equipment
                  (team assumption)
Scores are 0-100 relative to the rotations being compared (100 = best of the
set). An indicator that needs a value no source gives is skipped, not guessed.
The final score uses the indicators scored for the farmer's baseline, so every
rotation is ranked on the same terms as current practice; a rotation missing
one of those indicators is listed as not comparable instead of ranked.
Assumptions: soil starts at field capacity at
planting; roots are at full depth all season; cover crops are not in the
water balance (no Kc for rye or clover).
"""
import numpy as np
import pandas as pd

from climate_shift import NOW, compare_periods, day_of_season_to_date, yearly_indicators
from crops import crops_for_pack
from et0 import daily_et0
from power_client import fetch_power_daily
import snapshots
from crops import load as load_crops
from rotations import check, cover_options, day_of_year, fall_planted, generate, typical_harvest
from soil_client import get_soil

RESIDUE_WEIGHT = {"high": 0.5, "medium": 0.25, "low": 0.0}  # team assumption: residue counts half at most
GROUPS = {
    "soil_health": ["n_balance", "soil_cover", "diversity"],
    "water": ["water_demand"],
    "stability": ["climate_risk"],
    "simplicity": ["simplicity"],
}
HIGHER_IS_BETTER = {"water_demand": False, "n_balance": False, "soil_cover": True, "yield_loss_pct": False,
                    "heat_days": False, "diversity": True, "simplicity": False}
STAGES = ("ini", "dev", "mid", "late")
# Pack used when the request names none and the point is not a demo site
ZONE_PACK = {"north_temperate": "us_midwest", "south_temperate": "south_temperate", "tropical": "semi_arid_tropics"}


def mid(value):
    """Midpoint of a [low, high] range; plain numbers pass through."""
    return sum(value) / len(value) if isinstance(value, list) else value


def kc_curve(kc, stage_days, season_days):
    """Daily Kc for season_days: flat initial, linear development, flat mid, linear late
    (FAO-56 Fig. 34). A perennial's longer season stretches the mid stage."""
    ini, dev, mid_days, late = (round(d) for d in stage_days)
    mid_days = max(mid_days, season_days - ini - dev - late)
    k_ini, k_mid, k_end = mid(kc["ini"]), mid(kc["mid"]), mid(kc["end"])
    curve = np.concatenate([
        np.full(ini, k_ini),
        np.linspace(k_ini, k_mid, dev, endpoint=False),
        np.full(mid_days, k_mid),
        np.linspace(k_mid, k_end, late),
    ])
    return curve[:season_days]


def water_balance(rain, etc, taw, p):
    """(irrigation gap, rainfed ETa) in mm for one season, starting at field capacity."""
    raw = p * taw
    depletion, gap = 0.0, 0.0
    for r, e in zip(rain, etc):
        depletion = max(0.0, depletion - r + e)
        if depletion > raw:          # irrigate back to the stress threshold
            gap += depletion - raw
            depletion = raw
    depletion, eta = 0.0, 0.0
    for r, e in zip(rain, etc):
        ks = 1.0 if depletion <= raw else (taw - depletion) / (taw - raw)
        actual = ks * e
        eta += actual
        depletion = min(taw, max(0.0, depletion - r + actual))
    return gap, eta


def default_pack(lat, lon, zone):
    """The demo site's pack if the point is one, else the zone's default pack."""
    site_id = snapshots.site_for(lat, lon)
    for site in snapshots.load_sites()["sites"]:
        if site["id"] == site_id:
            return site["crop_pack"]
    return ZONE_PACK[zone]


def site_context(lat, lon, pack_id=None, soil=None):
    df = fetch_power_daily(lat, lon)
    yearly = yearly_indicators(df, lat)
    table = compare_periods(yearly)
    pack_id = pack_id or default_pack(lat, lon, table.attrs["zone"])
    if pack_id not in load_crops()["packs"]:
        raise ValueError(f"Unknown crop pack {pack_id!r}")
    soil = soil or get_soil(lat, lon)
    if soil is None:
        raise ValueError("No soil data for this point: pass a manual soil profile")
    return {
        "df": df, "et0": daily_et0(df, lat), "yearly": yearly, "table": table, "soil": soil,
        "zone": table.attrs["zone"], "year_start": table.attrs["year_start"],
        "pack": pack_id, "crops": crops_for_pack(pack_id),
    }


def planting_dates(crop, site):
    """(planting date, season days) for each NOW year, and whether the timing is assumed."""
    entry, yearly = crop["pack"], site["yearly"]
    years = [y for y in range(NOW[0], NOW[1] + 1) if y in yearly.index]
    total = round(sum(mid(entry["stage_days"][s]) for s in STAGES))
    if site["zone"] != "tropical":
        if crop["type"] == "perennial":  # green from last spring frost to first fall frost
            rows = yearly.loc[years, ["last_spring_frost", "first_fall_frost"]].dropna()
            return [(pd.Timestamp(y, 1, 1) + pd.Timedelta(days=int(r.last_spring_frost)),
                     int(r.first_fall_frost - r.last_spring_frost)) for y, r in rows.iterrows()], False
        start, end = (day_of_year(d) for d in entry["plant"])
        doy = (start + end) // 2
        return [(pd.Timestamp(y, 1, 1) + pd.Timedelta(days=doy - 1), total) for y in years], False
    after = entry.get("plant_after")
    delay = mid(after["days"]) if after else 0
    mean_onset = site["table"].loc["rain_onset", "now"]
    dates = []
    for y in years:
        onset = yearly.loc[y, "rain_onset"]
        onset = mean_onset if pd.isna(onset) else onset
        dates.append((pd.Timestamp(y, site["year_start"], 1) + pd.Timedelta(days=round(onset + delay) - 1), total))
    return dates, after is None


def crop_metrics(crop, site):
    """Per-crop averages over NOW years; None where a needed value is unsourced."""
    entry = crop["pack"]
    out = {"gap_mm": None, "yield_loss_pct": None, "heat_days": None, "plant_doy": None, "plant_rel": None,
           "total_days": None, "assumed_timing": False}
    if not entry.get("stage_days"):
        return out
    seasons, out["assumed_timing"] = planting_dates(crop, site)
    df, et0 = site["df"], site["et0"]
    seasons = [(s, n) for s, n in seasons if s + pd.Timedelta(days=n) <= df.index[-1]]
    stage_days = [mid(entry["stage_days"][s]) for s in STAGES]
    out["plant_doy"] = round(np.mean([s.dayofyear for s, _ in seasons]))
    out["plant_rel"] = out["plant_doy"] - (365 if fall_planted(crop, site["pack"]) else 0)
    out["total_days"] = round(np.mean([n for _, n in seasons]))

    can_water = crop["kc"] and crop["rooting_depth_m"] and crop["depletion_p"] is not None
    heat = crop.get("heat")
    gaps, losses, hot = [], [], []
    for start, n in seasons:
        days = pd.date_range(start, periods=n, freq="D")
        if can_water:
            etc = kc_curve(crop["kc"], stage_days, n) * et0.loc[days].to_numpy()
            taw = site["soil"]["awc_mm_per_m"] * mid(crop["rooting_depth_m"])
            gap, eta = water_balance(df.loc[days, "PRECTOTCORR"].to_numpy(), etc, taw, crop["depletion_p"])
            gaps.append(gap)
            if crop.get("ky") is not None:
                losses.append(min(1.0, crop["ky"] * (1 - eta / etc.sum())) * 100)
        if heat:
            ini_dev = round(stage_days[0] + stage_days[1])
            mid_stage = days[ini_dev:ini_dev + round(stage_days[2])]
            hot.append(int((df.loc[mid_stage, "T2M"] > mid(heat["threshold_c"])).sum()))
    out["gap_mm"] = float(np.mean(gaps)) if gaps else None
    out["yield_loss_pct"] = float(np.mean(losses)) if losses else None
    if heat:
        out["heat_days"] = float(np.mean(hot))
    elif "heat_note" in crop:  # e.g. hay crop: a grain-set heat limit does not apply
        out["heat_days"] = 0.0
    return out


def n_balance(seq, crops):
    """(fertilizer N kg/ha/yr, reason if skipped)."""
    total = 0.0
    for i, crop_id in enumerate(seq):
        crop = crops[crop_id]
        if crop["n_effect"] == "fixes":
            continue
        need = crop["pack"].get("n_need_kg_ha")
        if need is None:
            return None, f"no sourced N rate for {crop['name']} in this region"
        prev = crops[seq[i - 1]]
        adjust = (prev["pack"].get("next_crop_n_adjust_kg_ha") or {}).get(crop["n_season"])
        if adjust is None:
            return None, f"no sourced N credit from {prev['name']} to {crop['name']}"
        total += max(0.0, need + adjust)
    return total / len(seq), None


def soil_cover(seq, covers, crops, info):
    """(% of the cycle covered, reason if skipped). covers[i] is the cover crop after seq[i]."""
    n, cycle = len(seq), 365 * len(seq)
    spans = []
    for i, crop_id in enumerate(seq):
        crop, crop_info = crops[crop_id], info[crop_id]
        if crop_info["plant_doy"] is None:
            return None, f"no planting calendar for {crop['name']}"
        prev, nxt = seq[i - 1], seq[(i + 1) % n]
        if crop["type"] == "perennial":
            start = 365 * i + (0 if prev == crop_id else crop_info["plant_doy"])
            end = 365 * i + (365 if nxt == crop_id else day_of_year(crop["pack"]["harvest"][1]))
        else:
            start = 365 * i + crop_info["plant_rel"]
            end = start + crop_info["total_days"]
        spans.append((start, end))
    weight = np.zeros(cycle)
    for start, end in spans:
        weight[np.arange(start, end) % cycle] = 1.0
    for i, crop_id in enumerate(seq):
        start, end = spans[i][1], spans[(i + 1) % n][0] + (cycle if i == n - 1 else 0)
        if end <= start:
            continue
        if covers[i]:
            w = 1.0
        elif crops[crop_id]["residue_cover"] is None:
            return None, f"no sourced residue class for {crops[crop_id]['name']}"
        else:
            w = RESIDUE_WEIGHT[crops[crop_id]["residue_cover"]]
        days = np.arange(start, end) % cycle
        weight[days] = np.maximum(weight[days], w)
    return float(weight.mean() * 100), None


def rotation_metrics(seq, covers, crops, info):
    """Raw indicator values for one rotation, plus why any were skipped."""
    metrics, skipped = {}, {}
    metrics["n_balance"], why = n_balance(seq, crops)
    if why:
        skipped["n_balance"] = why
    metrics["soil_cover"], why = soil_cover(seq, covers, crops, info)
    if why:
        skipped["soil_cover"] = why
    for key, indicator, group in (("gap_mm", "water_demand", "water_demand"),
                                  ("yield_loss_pct", "yield_loss_pct", "climate_risk"),
                                  ("heat_days", "heat_days", "climate_risk")):
        missing = list(dict.fromkeys(crops[c]["name"] for c in seq if info[c][key] is None))
        metrics[indicator] = None if missing else float(np.mean([info[c][key] for c in seq]))
        if missing:
            skipped[group] = f"no sourced {key.replace('_', ' ')} inputs for {', '.join(missing)}"
    metrics["diversity"] = len(set(seq)) + len({crops[c]["family"] for c in seq})
    metrics["simplicity"] = len(set(seq)) + any(crops[c]["type"] == "perennial" for c in seq)
    return metrics, skipped


def relative(values, higher_is_better):
    """0-100 within the set: 100 = best value, 0 = worst; None stays None."""
    known = [v for v in values if v is not None]
    if not known:
        return values
    lo, hi = min(known), max(known)
    if hi == lo:
        return [None if v is None else 100.0 for v in values]
    return [None if v is None else 100 * ((v - lo) if higher_is_better else (hi - v)) / (hi - lo) for v in values]


def score_set(rotations):
    """Fill 'scores' (0-100 per indicator, relative to the set) for every rotation."""
    parts = {key: relative([r["metrics"][key] for r in rotations], better)
             for key, better in HIGHER_IS_BETTER.items()}
    for i, r in enumerate(rotations):
        scores = {key: parts[key][i] for key in ("n_balance", "soil_cover", "water_demand", "diversity", "simplicity")}
        risk = (parts["yield_loss_pct"][i], parts["heat_days"][i])
        scores["climate_risk"] = None if None in risk else sum(risk) / 2
        r["scores"] = scores


def final_score(scores, weights, indicators):
    """Slider-weighted mean of the group scores, using only the given indicators."""
    total, weight_sum = 0.0, 0.0
    for group, keys in GROUPS.items():
        known = [scores[k] for k in keys if k in indicators]
        if known and weights.get(group, 0) > 0:
            total += weights[group] * np.mean(known)
            weight_sum += weights[group]
    return float(round(total / weight_sum, 1)) if weight_sum else None


def describe(seq, crops):
    names = [crops[c]["name"].split(" (")[0].lower() for c in seq]
    return f"continuous {names[0]}" if len(set(seq)) == 1 else "-".join(names)


def cover_story(r, site):
    """How the later fall frost makes room for a cover crop: the tightest fit, where the shift matters most."""
    crops, table = site["crops"], site["table"]
    if "first_fall_frost" not in table.index:
        return ""
    fits = []
    for a, cover in zip(r["rotation"], r["covers"]):
        if cover:
            harvest = typical_harvest(crops[a], site["pack"])
            need = crops[cover]["cover"]["min_days_before_first_frost"]
            then, now = (table.loc["first_fall_frost", p] - harvest - need for p in ("then", "now"))
            fits.append((now, then, a, cover))
    if not fits:
        return ""
    now, then, a, cover = min(fits)
    return (f"; {crops[cover]['name'].lower()} fits after {crops[a]['name'].split(' (')[0].lower()} because the "
            f"first fall frost now comes {day_of_season_to_date(table.loc['first_fall_frost', 'now'])} instead of "
            f"{day_of_season_to_date(table.loc['first_fall_frost', 'then'])}, "
            f"leaving {now:.0f} days to establish it instead of {then:.0f}")


def explain(r, base, site):
    """2-4 plain-language reasons: the indicators where this rotation gains most on the baseline."""
    m, b, crops, table = r["metrics"], base["metrics"], site["crops"], site["table"]
    name = describe(base["rotation"], crops)
    candidates = []
    if m["n_balance"] is not None and b["n_balance"] is not None:
        legumes = sorted({crops[c]["name"] for c in r["rotation"] if crops[c]["n_effect"] == "fixes"})
        text = f"Needs about {m['n_balance']:.0f} kg N/ha of fertilizer a year, vs {b['n_balance']:.0f} for {name}"
        if legumes:
            one = len(legumes) == 1
            text += (f": {' and '.join(legumes)} {'fixes' if one else 'fix'} nitrogen and "
                     f"{'cuts' if one else 'cut'} the next crop's rate")
        candidates.append(("n_balance", text + "."))
    if m["soil_cover"] is not None and b["soil_cover"] is not None:
        candidates.append(("soil_cover", f"Soil is covered {m['soil_cover']:.0f}% of the year, vs "
                                         f"{b['soil_cover']:.0f}% for {name}{cover_story(r, site)}."))
    if m["water_demand"] is not None and b["water_demand"] is not None:
        change = table.loc["et0", "change"]
        candidates.append(("water_demand",
            f"Irrigation gap of about {m['water_demand']:.0f} mm a year, vs {b['water_demand']:.0f} mm for {name}; "
            f"yearly ET0 has {'risen' if change > 0 else 'fallen'} {abs(change):.0f} mm since 1981-2000."))
    if m["yield_loss_pct"] is not None and b["yield_loss_pct"] is not None:
        spell = table.loc["longest_dry_spell"]
        candidates.append(("climate_risk",
            f"Expected water-limited yield loss {m['yield_loss_pct']:.0f}% vs {b['yield_loss_pct']:.0f}% for {name}, "
            f"as the longest dry spell went from {spell['then']:.1f} to {spell['now']:.1f} days."))
    count = lambda seq: (len(set(seq)), len({crops[c]["family"] for c in seq}))
    (n_crops, n_families), (b_crops, b_families) = count(r["rotation"]), count(base["rotation"])
    text = f"{n_crops} crops from {n_families} plant {'family' if n_families == 1 else 'families'}, vs {b_crops} from {b_families} for {name}"
    if n_families > b_families:
        text += ": switching families breaks pest and disease cycles"
    candidates.append(("diversity", text + "."))

    gains = sorted((((r["scores"][k] or 0) - (base["scores"][k] or 0)), text) for k, text in candidates)[::-1]
    reasons = [text for gain, text in gains if gain > 0][:4]
    if len(reasons) < 2:
        reasons += [f"Trade-off: {text}" for gain, text in gains if gain <= 0][:2 - len(reasons)]
    return reasons


def evaluate(site, rotation, covers):
    if "info" not in site:  # per-crop metrics, computed once per site
        site["info"] = {c: crop_metrics(crop, site) for c, crop in site["crops"].items() if crop["type"] != "cover"}
    info = site["info"]
    metrics, skipped = rotation_metrics(list(rotation), list(covers), site["crops"], info)
    assumed = sorted({site["crops"][c]["name"] for c in rotation if info[c]["assumed_timing"]})
    return {"rotation": list(rotation), "covers": list(covers), "metrics": metrics, "skipped": skipped,
            "assumed_timing": assumed}


def first_fall_frost(site):
    return None if site["zone"] == "tropical" else round(site["table"].loc["first_fall_frost", "now"])


def candidates(site, years=None):
    """Valid rotations for the site's pack as (rotation, covers), using the first cover crop that fits."""
    return [(list(c["rotation"]), [opts[0] if opts else None for opts in c["covers"]])
            for c in generate(site["pack"], first_fall_frost(site))["valid"]
            if not years or len(c["rotation"]) in years]


def check_crops(site, seq):
    unknown = [c for c in seq if c not in site["crops"] or site["crops"][c]["type"] == "cover"]
    if unknown:
        raise ValueError(f"Not cash crops in pack {site['pack']}: {', '.join(unknown)}")


def score_against_baseline(site, baseline, weights, rotations):
    """Score the baseline and [(rotation, covers)] as one set. Final scores use only the
    indicators scored for the baseline; rotations missing one of them get final None."""
    check_crops(site, baseline)
    base = evaluate(site, baseline, [None] * len(baseline))
    scored = [evaluate(site, rotation, covers) for rotation, covers in rotations]
    score_set([base] + scored)
    indicators = {k for k, v in base["scores"].items() if v is not None}
    for r in [base] + scored:
        comparable = all(r["scores"][k] is not None for k in indicators)
        r["final"] = final_score(r["scores"], weights, indicators) if comparable else None
    return base, scored, sorted(indicators)


def recommend(lat, lon, pack_id, baseline, weights=None, soil=None, top=5, years=None):
    """Rank every valid rotation for the site against the farmer's baseline."""
    weights = weights or {group: 1.0 for group in GROUPS}
    site = site_context(lat, lon, pack_id, soil)
    base, scored, indicators = score_against_baseline(site, baseline, weights, candidates(site, years))
    comparable = [r for r in scored if r["final"] is not None]
    ranked = sorted(comparable, key=lambda r: r["final"], reverse=True)[:top]
    for r in ranked:
        r["reasons"] = explain(r, base, site)
    return {"zone": site["zone"], "pack": site["pack"], "soil": site["soil"], "baseline": base,
            "ranked_on": indicators, "n_valid": len(scored), "n_comparable": len(comparable),
            "rotations": ranked, "site": site}


def score_rotation(lat, lon, pack_id, baseline, rotation, covers=None, weights=None, soil=None, years=None):
    """Score a user-edited rotation within the same set as recommend(), so the numbers compare."""
    weights = weights or {group: 1.0 for group in GROUPS}
    site = site_context(lat, lon, pack_id, soil)
    check_crops(site, rotation)
    if covers is None:
        frost, crops = first_fall_frost(site), site["crops"]
        covers = [next(iter(cover_options(a, b, crops, site["pack"], frost)), None)
                  for a, b in zip(rotation, rotation[1:] + rotation[:1])]
    valid = candidates(site, years)
    base, scored, indicators = score_against_baseline(site, baseline, weights, valid + [(rotation, covers)])
    r = scored[-1]
    r["rule_breaks"] = check(tuple(rotation), site["crops"], site["pack"])
    r["reasons"] = explain(r, base, site)
    better = [x for x in scored[:-1] if x["final"] is not None and r["final"] is not None and x["final"] > r["final"]]
    ranked = r["final"] is not None and not r["rule_breaks"]  # a rotation that breaks a rule is scored, not ranked
    return {"zone": site["zone"], "pack": site["pack"], "soil": site["soil"], "baseline": base,
            "ranked_on": indicators, "rotation": r,
            "rank": len(better) + 1 if ranked else None,
            "n_comparable": sum(x["final"] is not None for x in scored[:-1]), "site": site}


def show(title, result):
    print(f"\n=== {title}: zone {result['zone']}, pack {result['pack']}, soil {result['soil']['texture_class']}")
    print(f"Ranked on {', '.join(result['ranked_on'])}: {result['n_comparable']} of {result['n_valid']} "
          f"valid rotations are comparable with the baseline")
    rows = [("BASELINE", result["baseline"])] + [(str(i + 1), r) for i, r in enumerate(result["rotations"])]
    for label, r in rows:
        covers = ", ".join(f"{c}->{cv}" for c, cv in zip(r["rotation"], r["covers"]) if cv) or "no covers"
        scores = " ".join(f"{k}={'-' if v is None else round(v)}" for k, v in r["scores"].items())
        print(f"{label:>8} {describe(r['rotation'], result['site']['crops'])}  final={r['final']}  ({covers})")
        print(" " * 9 + scores)
        print(" " * 9 + "  ".join(f"{k}={'-' if v is None else round(v, 1)}" for k, v in r["metrics"].items()))
        for reason in r.get("reasons", []):
            print(" " * 11 + "- " + reason)
        if r["skipped"]:
            print(" " * 11 + "skipped: " + "; ".join(f"{k}: {v}" for k, v in r["skipped"].items()))
        if r["assumed_timing"]:
            print(" " * 11 + "assumed timing (planted at onset): " + ", ".join(r["assumed_timing"]))


if __name__ == "__main__":
    show("Ames, IA", recommend(42.03, -93.62, "us_midwest", ["maize"]))
    show("Niamey area, Niger", recommend(13.51, 2.16, "semi_arid_tropics", ["pearl_millet"]))
