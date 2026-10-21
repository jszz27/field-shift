"""Daily reference evapotranspiration (ET0) with FAO-56 Penman-Monteith.

Allen et al. (1998), FAO Irrigation and Drainage Paper 56, Chapter 3.
Equation numbers below refer to that paper. Inputs are NASA POWER daily
values; vapor pressure uses mean relative humidity (eq. 19) because POWER
does not provide daily RH max/min.
"""
import numpy as np
import pandas as pd

from power_client import fetch_power_daily

SOLAR_CONSTANT = 0.0820   # MJ/m²/min
STEFAN_BOLTZMANN = 4.903e-9  # MJ/K⁴/m²/day
ALBEDO = 0.23             # reference grass


def saturation_vapor_pressure(t):
    """kPa at air temperature t (°C). Eq. 11."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def extraterrestrial_radiation(lat_deg, day_of_year):
    """Ra, solar radiation at the top of the atmosphere (MJ/m²/day). Eqs. 21–25."""
    phi = np.radians(lat_deg)
    angle = 2 * np.pi * day_of_year / 365
    dr = 1 + 0.033 * np.cos(angle)              # inverse Earth–Sun distance
    decl = 0.409 * np.sin(angle - 1.39)         # solar declination
    ws = np.arccos(-np.tan(phi) * np.tan(decl))  # sunset hour angle
    return (24 * 60 / np.pi) * SOLAR_CONSTANT * dr * (
        ws * np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.sin(ws)
    )


def et0_penman_monteith(tmax, tmin, rh_mean, wind_2m, solar, lat_deg, elevation_m, day_of_year):
    """ET0 in mm/day. Soil heat flux is taken as 0 for daily steps (eq. 42)."""
    tmean = (tmax + tmin) / 2
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26   # eq. 7
    gamma = 0.000665 * pressure                                       # eq. 8

    es = (saturation_vapor_pressure(tmax) + saturation_vapor_pressure(tmin)) / 2  # eq. 12
    ea = rh_mean / 100 * es                                                       # eq. 19
    delta = 4098 * saturation_vapor_pressure(tmean) / (tmean + 237.3) ** 2        # eq. 13

    ra = extraterrestrial_radiation(lat_deg, day_of_year)
    rso = (0.75 + 2e-5 * elevation_m) * ra                       # clear-sky radiation, eq. 37
    rns = (1 - ALBEDO) * solar                                   # net shortwave, eq. 38
    cloudiness = 1.35 * np.minimum(solar / rso, 1.0) - 0.35
    rnl = (STEFAN_BOLTZMANN * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2
           * (0.34 - 0.14 * np.sqrt(ea)) * cloudiness)           # net longwave, eq. 39
    rn = rns - rnl

    return (0.408 * delta * rn + gamma * 900 / (tmean + 273) * wind_2m * (es - ea)) / (
        delta + gamma * (1 + 0.34 * wind_2m)
    )                                                            # eq. 6


def daily_et0(df, lat_deg):
    """ET0 series (mm/day) for a POWER DataFrame."""
    return pd.Series(et0_penman_monteith(
        df["T2M_MAX"], df["T2M_MIN"], df["RH2M"], df["WS2M"], df["ALLSKY_SFC_SW_DWN"],
        lat_deg, df.attrs["elevation_m"], df.index.dayofyear,
    ), index=df.index, name="et0")


if __name__ == "__main__":
    # Ames, Iowa: the primary demo location
    lat = 42.03
    df = fetch_power_daily(lat, -93.62)
    et0 = daily_et0(df, lat)
    print(f"\nElevation: {df.attrs['elevation_m']} m")
    print(f"Days without ET0 (missing solar): {et0.isna().sum():,}, "
          f"{et0[et0.isna()].index.min().date()} to {et0[et0.isna()].index.max().date()}")
    print("\nMean daily ET0 by month (mm/day):")
    print(et0.groupby(et0.index.month).mean().round(2).to_string())
    annual = et0.dropna().groupby(et0.dropna().index.year).sum()
    print(f"\nAnnual ET0: mean {annual.mean():.0f} mm, range {annual.min():.0f}-{annual.max():.0f} mm")
