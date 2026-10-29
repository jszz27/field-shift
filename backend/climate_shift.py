"""Climate shift indicators: compare 1981–2000 ("then") with 2005–2024 ("now").

Each indicator is computed once per season year, then averaged over each
period. The climate zone decides which indicators apply:
  north_temperate - calendar year, growing season May–Sep, frost split at Jul 1
  south_temperate - season year Jul–Jun labelled by its start year, growing
                    season Nov–Mar, frost split at Jan 1
  tropical        - frost-free in most years, at any latitude (the tropics,
                    but also e.g. Bangladesh or south Florida); the season is
                    the rainy season, found with the FAO rain-vs-ET0 rule. The
                    season year starts in the driest month so no rainy season
                    is cut by the calendar.
"""
import numpy as np
import pandas as pd

from et0 import daily_et0
from power_client import fetch_power_daily

THEN = (1981, 2000)
NOW = (2005, 2024)
GDD_BASE, GDD_CAP = 10.0, 30.0   # °C, the 86/50 °F corn method
HEAT_STRESS_TEMP = 35.0          # °C, daily max
FROST_TEMP = 0.0                 # °C, daily min
DRY_DAY_RAIN = 1.0               # mm/day

# Zone classification
FROST_YEAR_SHARE = 0.5    # temperate if frost occurs in at least half the years ("most years")

# Temperate zones: season-year start month, growing-season months, frost split month
TEMPERATE = {
    "north_temperate": {"year_start": 1, "season_months": [5, 6, 7, 8, 9], "frost_split": 7},
    "south_temperate": {"year_start": 7, "season_months": [11, 12, 1, 2, 3], "frost_split": 1},
}

# Rainy season (tropical)
DEKAD_DAYS = 10              # FAO growing-period method works on 10-day periods
RAINS_FRACTION_OF_ET0 = 0.5  # FAO (1978) General Method: season when rain >= half of ET0
                             # (FAO land evaluation guidelines, Annex A, fao.org/4/x5648e)
FALSE_START_WINDOW = 30      # Sivakumar (1988): no dry spell over 7 days in the 30 days after onset
FALSE_START_DRY_DAYS = 7
SOIL_STORE_MM = 100          # FAO WSRR 71/1: stored soil water used after the rains end


def growing_degree_days(df):
    """Daily GDD with both temperatures clipped to the 10–30 °C range."""
    tmax = df["T2M_MAX"].clip(GDD_BASE, GDD_CAP)
    tmin = df["T2M_MIN"].clip(GDD_BASE, GDD_CAP)
    return (tmax + tmin) / 2 - GDD_BASE


def classify_climate_zone(lat, df):
    """'tropical' (seasons set by rain) if frost-free in most years, else temperate by hemisphere.

    Latitude alone is not used: frost-free subtropics such as Bangladesh have no fall
    frost to plan around, so the rainy-season rules fit them better.
    """
    frost_years = (df["T2M_MIN"] <= FROST_TEMP).groupby(df.index.year).any()
    if frost_years.mean() < FROST_YEAR_SHARE:
        return "tropical"
    return "north_temperate" if lat >= 0 else "south_temperate"


def season_year(index, start_month):
    """Label each date with the year its season year started in."""
    return index.year - (index.month < start_month)


def day_of_season(index, start_month):
    """Days since the season year started (1 = first day); equals day of year when start_month is 1."""
    start = pd.to_datetime({"year": season_year(index, start_month), "month": start_month, "day": 1})
    return (index - pd.DatetimeIndex(start)).days + 1


def day_of_season_to_date(day, start_month=1):
    start = pd.Timestamp(2001, start_month, 1)
    return (start + pd.Timedelta(days=round(day) - 1)).strftime("%b %d")


def day_of_year_to_date(doy):
    return day_of_season_to_date(doy)


def frost_dates(tmin, year_start=1, split_month=7):
    """Per season year: day of season of last spring frost and first fall frost."""
    frost = tmin[tmin <= FROST_TEMP]
    days = pd.Series(day_of_season(frost.index, year_start), index=frost.index)
    label = season_year(frost.index, year_start)
    spring_side = (frost.index.month - year_start) % 12 < (split_month - year_start) % 12
    spring, fall = days[spring_side], days[~spring_side]
    return pd.DataFrame({
        "last_spring_frost": spring.groupby(label[spring_side]).max(),
        "first_fall_frost": fall.groupby(label[~spring_side]).min(),
    })


def longest_dry_spell(precip):
    """Longest run of consecutive days with rain below DRY_DAY_RAIN."""
    dry = precip < DRY_DAY_RAIN
    run_id = (~dry).cumsum()  # increments on each wet day, so dry runs share an id
    return int(dry.groupby(run_id).sum().max())


def rainy_seasons(rain, et0):
    """(onset, end) day positions of every rainy season in one season year (0-based, end inclusive).

    Onset: first day of a 10-day period with rain >= half ET0 and no false start.
    End: after the rains stop, the day the soil store (filled by rain minus ET0,
    capped at SOIL_STORE_MM) runs dry. A season needs one humid period (rain > ET0).
    """
    rain, et0 = np.asarray(rain, float), np.asarray(et0, float)
    block = np.arange(len(rain)) // DEKAD_DAYS
    p_b, e_b = np.bincount(block, rain), np.bincount(block, et0)
    rains = p_b >= RAINS_FRACTION_OF_ET0 * e_b
    humid = p_b > e_b

    seasons, b = [], 0
    while b < len(p_b):
        start = b * DEKAD_DAYS
        window = pd.Series(rain[start:start + FALSE_START_WINDOW])
        if not rains[b] or longest_dry_spell(window) > FALSE_START_DRY_DAYS:
            b += 1
            continue
        store, d = 0.0, start
        while d < len(rain) - 1:
            store = min(SOIL_STORE_MM, max(0.0, store + rain[d] - et0[d]))
            if store == 0 and not rains[block[d]]:
                break
            d += 1
        if humid[block[start]:block[d] + 1].any():
            seasons.append((start, d))
        b = block[d] + 1
    return seasons


def tropical_season_indicators(rain, et0):
    """Indicators for the longest rainy season of one season year, plus how many seasons there were."""
    if et0.isna().any():
        return {}  # ET0 missing (no solar data before 1984)
    seasons = rainy_seasons(rain, et0)
    if not seasons:
        return {"n_seasons": 0}
    onset, end = max(seasons, key=lambda s: s[1] - s[0])
    in_season = rain.iloc[onset:end + 1]
    return {
        "rain_onset": onset + 1, "rain_end": end + 1, "season_length": end - onset + 1,
        "season_rain": in_season.sum(), "longest_dry_spell": longest_dry_spell(in_season),
        "n_seasons": len(seasons),
    }


def driest_month(precip):
    return int(precip.groupby(precip.index.month).mean().idxmin())


def yearly_indicators(df, lat_deg):
    """One row per complete season year with the indicators that apply to the climate zone."""
    zone = classify_climate_zone(lat_deg, df)
    et0 = daily_et0(df, lat_deg)
    year_start = TEMPERATE[zone]["year_start"] if zone in TEMPERATE else driest_month(df["PRECTOTCORR"])
    label = season_year(df.index, year_start)

    yearly = pd.DataFrame({
        "heat_stress_days": (df["T2M_MAX"] > HEAT_STRESS_TEMP).groupby(label).sum(),
        # Annual total; years with missing days (solar data starts 1984) stay empty
        "et0": et0.groupby(label).sum(min_count=365),
    })

    if zone in TEMPERATE:
        cfg = TEMPERATE[zone]
        season = df[df.index.month.isin(cfg["season_months"])]
        season_label = season_year(season.index, year_start)
        yearly["gdd"] = growing_degree_days(df).groupby(label).sum()
        yearly["season_rain"] = season["PRECTOTCORR"].groupby(season_label).sum()
        yearly["longest_dry_spell"] = season["PRECTOTCORR"].groupby(season_label).apply(longest_dry_spell)
        yearly["gwetroot"] = season["GWETROOT"].groupby(season_label).mean()
        yearly = yearly.join(frost_dates(df["T2M_MIN"], year_start, cfg["frost_split"]))
        yearly["frost_free_days"] = yearly["first_fall_frost"] - yearly["last_spring_frost"] - 1
    else:
        seasons = pd.DataFrame({
            year: tropical_season_indicators(g["PRECTOTCORR"], et0.loc[g.index])
            for year, g in df.groupby(label)
        }).T
        yearly = yearly.join(seasons)
        yearly["gwetroot"] = df["GWETROOT"].groupby(label).mean()

    complete = df.groupby(label).size() >= 365  # drop part-years at the ends of the record
    yearly = yearly[complete.reindex(yearly.index, fill_value=False)]
    yearly.attrs = {"zone": zone, "year_start": year_start}
    return yearly


def compare_periods(yearly):
    """Average each indicator over THEN and NOW; add rainfall variability."""
    then = yearly.loc[THEN[0]:THEN[1]]
    now = yearly.loc[NOW[0]:NOW[1]]
    table = pd.DataFrame({"then": then.mean(), "now": now.mean()})
    if "season_rain" in yearly:  # absent where no rainy season was ever found (true deserts)
        table.loc["season_rain_cv"] = [
            period["season_rain"].std() / period["season_rain"].mean() * 100
            for period in (then, now)
        ]
    table["change"] = table["now"] - table["then"]
    table.attrs = dict(yearly.attrs)
    return table


DATE_ROWS = ["last_spring_frost", "first_fall_frost", "rain_onset", "rain_end"]

# Unit and plain-language label per indicator, for the takeaways
LABELS = {
    "gdd": ("°C-days", "Growing heat (GDD) per year"),
    "heat_stress_days": ("days", "Days above 35 °C per year"),
    "season_rain": ("mm", "Rain in the growing season"),
    "season_rain_cv": ("%", "Year-to-year variability of that rain"),
    "longest_dry_spell": ("days", "Longest dry spell in the season"),
    "et0": ("mm", "Water demand from the air (ET0) per year"),
    "gwetroot": ("0-1", "Root-zone soil wetness (0 dry, 1 saturated)"),
    "last_spring_frost": ("date", "Last spring frost"),
    "first_fall_frost": ("date", "First fall frost"),
    "frost_free_days": ("days", "Frost-free season"),
    "rain_onset": ("date", "Rainy season starts"),
    "rain_end": ("date", "Rainy season ends"),
    "season_length": ("days", "Rainy season length"),
    "n_seasons": ("seasons", "Rainy seasons per year"),
}


# What a rise / fall means for a farmer (neutral: whether it helps depends on the crop)
MEANINGS = {
    "gdd": ("More heat to ripen crops; longer-season varieties may fit.", "Less heat to ripen crops."),
    "heat_stress_days": ("More days hot enough to hurt flowering and grain fill.", "Fewer extreme-heat days."),
    "season_rain": ("Wetter growing seasons.", "Drier growing seasons: less water for crops without irrigation."),
    "season_rain_cv": ("Rain is less predictable from one year to the next.", "Rain is more predictable from one year to the next."),
    "longest_dry_spell": ("Longer dry breaks during the season raise drought stress.", "Shorter dry breaks during the season."),
    "et0": ("The air pulls more water from crops and soil, so crops need more water.", "The air pulls less water from crops and soil."),
    "gwetroot": ("Root zones are wetter.", "Root zones are drier."),
    "last_spring_frost": ("Spring frost risk lasts longer, delaying planting.", "Planting can start earlier."),
    "first_fall_frost": ("More time after harvest to establish a cover crop.", "Less time after harvest before frost."),
    "frost_free_days": ("A longer growing season.", "A shorter growing season."),
    "rain_onset": ("The rains start later, pushing planting back.", "The rains start earlier, so planting can start earlier."),
    "rain_end": ("The rains last longer into the season.", "The rains end sooner."),
    "season_length": ("A longer rainy season: more time for crops to finish.", "A shorter rainy season: crops have less time to finish."),
    "n_seasons": ("Usable rainy seasons happen more often.", "Usable rainy seasons happen less often."),
}


def is_small(unit, then, change):
    """Changes too small to call a shift."""
    if unit == "date":
        return abs(change) <= 2
    if unit == "%":
        return abs(change) < 2       # percentage points of rainfall variability
    if unit == "0-1":
        return abs(change) < 0.02
    return not then or abs(change / then) < 0.03


def takeaways(table):
    """One record per indicator: then, now, change, a sentence with the numbers and what it means."""
    year_start = table.attrs["year_start"]
    period = f"{THEN[0]}-{THEN[1]} vs {NOW[0]}-{NOW[1]}"
    records = []
    for name, (unit, label) in LABELS.items():
        if name not in table.index or table.loc[name, ["then", "now"]].isna().any():
            continue  # not measurable here in one of the periods (e.g. no rainy season in a desert)
        then, now, change = (float(v) for v in table.loc[name, ["then", "now", "change"]])
        if unit == "date":
            shown = (day_of_season_to_date(then, year_start), day_of_season_to_date(now, year_start))
            days = round(now) - round(then)  # matches the dates shown
            direction = "earlier" if days < 0 else "later"
            text = f"{label}: {shown[0]} -> {shown[1]} ({abs(days)} days {direction}, {period})."
        else:
            digits = 2 if unit == "0-1" else 1 if abs(now) < 20 else 0
            shown = (f"{then:.{digits}f}", f"{now:.{digits}f}")
            if unit == "%":
                text = f"{label}: {shown[0]}% -> {shown[1]}% ({period})."
            else:
                suffix = "" if unit == "0-1" else f" {unit}"
                pct = f", {change / then * 100:+.0f}%" if then and unit != "0-1" else ""
                text = f"{label}: {shown[0]} -> {shown[1]}{suffix}{pct} ({period})."
        direction = "same" if is_small(unit, then, change) else "up" if change > 0 else "down"
        meaning = "Little change." if direction == "same" else MEANINGS[name][0 if direction == "up" else 1]
        records.append({"indicator": name, "label": label, "unit": unit, "then": then, "now": now, "change": change,
                        "then_display": shown[0], "now_display": shown[1], "direction": direction,
                        "text": text, "meaning": meaning})
    return records

if __name__ == "__main__":
    sites = [
        ("Ames, IA", 42.03, -93.62),
        ("Pergamino, Argentina", -33.89, -60.57),
        ("Nairobi, Kenya", -1.29, 36.82),
        ("Anantapur, India", 14.68, 77.60),
    ]
    for name, lat, lon in sites:
        yearly = yearly_indicators(fetch_power_daily(lat, lon), lat)
        table = compare_periods(yearly)
        then_years, now_years = yearly.loc[THEN[0]:THEN[1]].index, yearly.loc[NOW[0]:NOW[1]].index
        print(f"\n{name}: zone {table.attrs['zone']}, season year starts in month {table.attrs['year_start']}")
        print(f"Season years: then {then_years.min()}-{then_years.max()}, now {now_years.min()}-{now_years.max()}")
        print(table.round(2).to_string())
        for row in DATE_ROWS:
            if row in table.index:
                then, now = table.loc[row, ["then", "now"]]
                print(f"{row}: {day_of_season_to_date(then, table.attrs['year_start'])} -> "
                      f"{day_of_season_to_date(now, table.attrs['year_start'])}")
