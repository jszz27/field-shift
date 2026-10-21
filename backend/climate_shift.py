"""Climate shift indicators: compare 1981–2000 ("then") with 2005–2024 ("now").

Each indicator is computed once per year, then averaged over each period.
Assumes the Northern Hemisphere: growing season is May–Sep and frost dates
are split at July 1.
"""
import pandas as pd

from power_client import fetch_power_daily

THEN = (1981, 2000)
NOW = (2005, 2024)
GROWING_SEASON_MONTHS = [5, 6, 7, 8, 9]
GDD_BASE, GDD_CAP = 10.0, 30.0   # °C, the 86/50 °F corn method
HEAT_STRESS_TEMP = 35.0          # °C, daily max
FROST_TEMP = 0.0                 # °C, daily min
DRY_DAY_RAIN = 1.0               # mm/day


def growing_degree_days(df):
    """Daily GDD with both temperatures clipped to the 10–30 °C range."""
    tmax = df["T2M_MAX"].clip(GDD_BASE, GDD_CAP)
    tmin = df["T2M_MIN"].clip(GDD_BASE, GDD_CAP)
    return (tmax + tmin) / 2 - GDD_BASE


def frost_dates(tmin):
    """Per year: day-of-year of last spring frost and first fall frost."""
    frost = tmin[tmin <= FROST_TEMP]
    days = pd.Series(frost.index.dayofyear, index=frost.index)
    spring = days[days.index.month < 7]
    fall = days[days.index.month >= 7]
    return pd.DataFrame({
        "last_spring_frost": spring.groupby(spring.index.year).max(),
        "first_fall_frost": fall.groupby(fall.index.year).min(),
    })


def longest_dry_spell(precip):
    """Longest run of consecutive days with rain below DRY_DAY_RAIN."""
    dry = precip < DRY_DAY_RAIN
    run_id = (~dry).cumsum()  # increments on each wet day, so dry runs share an id
    return int(dry.groupby(run_id).sum().max())


def yearly_indicators(df):
    """One row per year with every indicator."""
    year = df.index.year
    season = df[df.index.month.isin(GROWING_SEASON_MONTHS)]
    season_year = season.index.year

    yearly = pd.DataFrame({
        "gdd": growing_degree_days(df).groupby(year).sum(),
        "heat_stress_days": (df["T2M_MAX"] > HEAT_STRESS_TEMP).groupby(year).sum(),
        "season_rain": season["PRECTOTCORR"].groupby(season_year).sum(),
        "longest_dry_spell": season["PRECTOTCORR"].groupby(season_year).apply(longest_dry_spell),
    })
    yearly = yearly.join(frost_dates(df["T2M_MIN"]))
    yearly["frost_free_days"] = yearly["first_fall_frost"] - yearly["last_spring_frost"] - 1
    return yearly


def compare_periods(yearly):
    """Average each indicator over THEN and NOW; add rainfall variability."""
    then = yearly.loc[THEN[0]:THEN[1]]
    now = yearly.loc[NOW[0]:NOW[1]]
    table = pd.DataFrame({"then": then.mean(), "now": now.mean()})
    table.loc["season_rain_cv"] = [
        period["season_rain"].std() / period["season_rain"].mean() * 100
        for period in (then, now)
    ]
    table["change"] = table["now"] - table["then"]
    return table


def day_of_year_to_date(doy):
    return (pd.Timestamp("2001-01-01") + pd.Timedelta(days=round(doy) - 1)).strftime("%b %d")


if __name__ == "__main__":
    # Ames, Iowa: the primary demo location
    df = fetch_power_daily(42.03, -93.62)
    table = compare_periods(yearly_indicators(df))
    print(f"\nClimate shift, Ames IA: {THEN[0]}-{THEN[1]} vs {NOW[0]}-{NOW[1]}\n")
    print(table.round(1).to_string())
    for col in ("last_spring_frost", "first_fall_frost"):
        then, now = table.loc[col, ["then", "now"]]
        print(f"{col}: {day_of_year_to_date(then)} -> {day_of_year_to_date(now)}")
