import numpy as np
import pandas as pd
import pytest

from climate_shift import (
    classify_climate_zone, day_of_season, frost_dates, rainy_seasons, season_year,
)


def daily(start, end, tmin):
    index = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"T2M_MIN": tmin(index)}, index=index)


# Zone classification ------------------------------------------------------

def frost_every_winter(index):
    return np.where(index.month.isin([1, 7]), -5.0, 10.0)  # frost in Jan and Jul, every year


def frost_free(index):
    return np.full(len(index), 12.0)


@pytest.mark.parametrize("lat, tmin, zone", [
    (42.0, frost_every_winter, "north_temperate"),
    (-34.0, frost_every_winter, "south_temperate"),
    (-1.3, frost_free, "tropical"),
    (14.7, frost_free, "tropical"),
    (10.0, frost_every_winter, "north_temperate"),  # frosty tropical highland: frost rules apply
    (30.0, frost_free, "north_temperate"),          # outside the tropics stays temperate
])
def test_classify_climate_zone(lat, tmin, zone):
    assert classify_climate_zone(lat, daily("2001-01-01", "2010-12-31", tmin)) == zone


def test_frost_in_only_a_few_years_is_still_tropical():
    def rare_frost(index):
        return np.where((index.year < 2003) & (index.month == 7), -1.0, 12.0)  # 2 of 10 years
    assert classify_climate_zone(-5.0, daily("2001-01-01", "2010-12-31", rare_frost)) == "tropical"


# Southern season year crossing Dec -> Jan ---------------------------------

def test_season_year_labels_by_start_year():
    index = pd.DatetimeIndex(["2001-06-30", "2001-07-01", "2001-12-31", "2002-01-01", "2002-06-30"])
    assert list(season_year(index, 7)) == [2000, 2001, 2001, 2001, 2001]
    assert list(day_of_season(index, 7)) == [365, 1, 184, 185, 365]


def test_southern_frost_dates_span_new_year():
    # Last spring frost Aug 20 2001, first fall frost May 10 2002: both belong to season 2001
    frosts = pd.DatetimeIndex(["2001-08-20", "2002-05-10"])
    df = daily("2001-07-01", "2002-06-30", lambda index: np.where(index.isin(frosts), -2.0, 8.0))
    dates = frost_dates(df["T2M_MIN"], year_start=7, split_month=1)
    assert list(dates.index) == [2001]
    spring, fall = dates.loc[2001, ["last_spring_frost", "first_fall_frost"]]
    assert spring == 51                           # Aug 20 is day 51 from Jul 1
    assert fall == 314                            # May 10 2002 is day 314
    assert fall - spring - 1 == (pd.Timestamp("2002-05-10") - pd.Timestamp("2001-08-20")).days - 1


def test_northern_frost_dates_unchanged():
    frosts = pd.DatetimeIndex(["2001-04-25", "2001-10-10"])
    df = daily("2001-01-01", "2001-12-31", lambda index: np.where(index.isin(frosts), -2.0, 8.0))
    dates = frost_dates(df["T2M_MIN"])
    assert dates.loc[2001, "last_spring_frost"] == 115
    assert dates.loc[2001, "first_fall_frost"] == 283


# Rainy season onset and end ----------------------------------------------

ET0 = 4.0  # mm/day, so a 10-day period needs 20 mm to count as rainy and 40 mm to be humid


def test_onset_and_end_after_soil_store_runs_dry():
    rain = np.zeros(120)
    rain[30:70] = 10.0                # 40 wet days starting day 30
    seasons = rainy_seasons(rain, np.full(120, ET0))
    # Store fills to 100 mm during the rains, then drains 4 mm/day: empty 25 days after day 69
    assert seasons == [(30, 94)]


def test_false_start_is_skipped():
    rain = np.zeros(120)
    rain[10:12] = 15.0                # 30 mm burst, then 18 dry days: a false start
    rain[30:70] = 10.0
    assert rainy_seasons(rain, np.full(120, ET0))[0][0] == 30


def test_light_steady_rain_without_humid_period_is_not_a_season():
    rain = np.full(120, 2.5)          # 25 mm per 10 days: rainy (>= 20) but never humid (> 40)
    assert rainy_seasons(rain, np.full(120, ET0)) == []


def test_two_separate_seasons():
    rain = np.zeros(360)
    rain[30:70] = 10.0
    rain[200:240] = 10.0
    assert rainy_seasons(rain, np.full(360, ET0)) == [(30, 94), (200, 264)]
