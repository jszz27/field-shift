"""Southern-Hemisphere crop calendars and places with no season (no frost, no rainy season)."""
import numpy as np
import pandas as pd

from climate_shift import compare_periods, takeaways
from crops import crops_for_pack
from rotations import check, day_of_season, fall_planted, generate, typical_harvest, window

SOUTH = crops_for_pack("south_temperate")
NORTH = crops_for_pack("us_midwest")


def test_northern_days_of_season_are_days_of_year():
    assert day_of_season("01-01", "us_midwest") == 1 and day_of_season("10-15", "us_midwest") == 288
    assert typical_harvest(NORTH["maize"], "us_midwest") == (278 + 313) // 2   # Oct 5-Nov 9, unchanged


def test_southern_season_year_starts_in_july():
    assert day_of_season("07-01", "south_temperate") == 1
    assert day_of_season("06-30", "south_temperate") == 365
    # Wheat harvest Oct 31-Jan 22 crosses New Year but stays inside one season year
    assert window(SOUTH["winter_wheat"]["pack"]["harvest"], "south_temperate") == (123, 206)
    # Wheat sowing May 7-Aug 21 crosses Jul 1: the end runs into the next season year
    assert window(SOUTH["winter_wheat"]["pack"]["plant"], "south_temperate") == (311, 417)


def test_southern_wheat_is_the_fall_planted_crop():
    assert fall_planted(SOUTH["winter_wheat"], "south_temperate")
    assert not fall_planted(SOUTH["maize"], "south_temperate")      # sown Sep-Dec, harvested Mar-May
    assert not fall_planted(SOUTH["soybean"], "south_temperate")


def test_southern_rotations_follow_the_timing_rule():
    # Maize and soybean are harvested by about May, before wheat sowing ends in August
    assert check(("maize", "winter_wheat"), SOUTH, "south_temperate") == []
    assert check(("soybean", "winter_wheat"), SOUTH, "south_temperate") == []
    valid = {r["rotation"] for r in generate("south_temperate", first_fall_frost=300)["valid"]}
    assert ("soybean", "winter_wheat") in valid and ("maize", "soybean") in valid


def test_desert_without_rainy_season_still_gets_climate_cards():
    years = range(1981, 2025)
    yearly = pd.DataFrame({"heat_stress_days": np.linspace(150, 170, len(years)),
                           "et0": np.full(len(years), 2600.0), "n_seasons": 0.0}, index=years)
    yearly.attrs = {"zone": "tropical", "year_start": 1}
    table = compare_periods(yearly)
    assert "season_rain_cv" not in table.index
    assert {r["indicator"] for r in takeaways(table)} == {"heat_stress_days", "et0", "n_seasons"}
