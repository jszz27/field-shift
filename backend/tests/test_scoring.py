import numpy as np
import pytest

from scoring import (
    GROUPS, evaluate, final_score, kc_curve, n_balance, relative, score_set, site_context, soil_cover,
    water_balance,
)


# Indicator functions on made-up inputs -------------------------------------

def test_kc_curve_follows_fao_stages():
    kc = {"ini": 0.3, "mid": 1.2, "end": [0.4, 0.6]}
    curve = kc_curve(kc, [10, 20, 30, 10], 70)
    assert len(curve) == 70
    assert curve[0] == curve[9] == 0.3          # flat initial stage
    assert 0.3 < curve[20] < 1.2                # rising development stage
    assert curve[30] == curve[59] == 1.2        # flat mid stage
    assert curve[-1] == pytest.approx(0.5)      # end value is the midpoint of the range


def test_kc_curve_stretches_mid_stage_for_longer_seasons():
    curve = kc_curve({"ini": 0.4, "mid": 0.95, "end": 0.9}, [10, 30, 25, 10], 150)
    assert len(curve) == 150
    assert (curve[40:140] == 0.95).all()         # mid stage grows from 25 to 100 days


def test_water_balance_without_rain():
    # TAW 100 mm, p 0.5: no stress until 50 mm used (day 10), then 5 mm/day must be added for 10 days
    gap, eta = water_balance(np.zeros(20), np.full(20, 5.0), taw=100, p=0.5)
    assert gap == pytest.approx(50)
    assert 50 < eta < 100                        # rainfed crop is stressed after day 10


def test_water_balance_with_enough_rain():
    gap, eta = water_balance(np.full(20, 6.0), np.full(20, 5.0), taw=100, p=0.5)
    assert gap == 0 and eta == pytest.approx(100)


def made_up_crops():
    def crop(name, n_effect, n_season, need, adjust, residue="high"):
        return {"name": name, "family": "legume" if n_effect == "fixes" else "grass", "type": "cash",
                "n_effect": n_effect, "n_season": n_season, "residue_cover": residue,
                "pack": {"n_need_kg_ha": need, "next_crop_n_adjust_kg_ha": adjust}}
    return {
        "maize": crop("Maize", "heavy_feeder", "warm", 200, {"warm": 0, "cool": 0}),
        "soybean": crop("Soybean", "fixes", None, None, {"warm": -60, "cool": 0}, residue="low"),
        "oats": crop("Oats", None, "cool", None, None),
    }


def test_n_balance_credits_legumes():
    crops = made_up_crops()
    assert n_balance(["maize"], crops) == (200, None)
    assert n_balance(["maize", "soybean"], crops) == (70, None)   # (200 - 60 + 0) / 2


def test_n_balance_skips_unsourced_rates():
    value, why = n_balance(["maize", "oats"], made_up_crops())
    assert value is None and "Oats" in why


def test_soil_cover_counts_crops_covers_and_residue():
    crops = made_up_crops()
    info = {"maize": {"plant_doy": 100, "plant_rel": 100, "total_days": 165},
            "soybean": {"plant_doy": 100, "plant_rel": 100, "total_days": 165}}
    # Continuous maize: 165 crop days + 200 fallow days at residue weight 0.5
    assert soil_cover(["maize"], [None], crops, info)[0] == pytest.approx((165 + 100) / 365 * 100)
    # A cover crop after soybean covers its whole fallow; soybean residue alone would count 0
    with_cover = soil_cover(["maize", "soybean"], [None, "rye"], crops, info)[0]
    without = soil_cover(["maize", "soybean"], [None, None], crops, info)[0]
    assert with_cover == pytest.approx((165 + 100 + 365) / 730 * 100)
    assert without == pytest.approx((165 + 100 + 165) / 730 * 100)


def test_relative_scores():
    assert relative([10, 20, None, 30], higher_is_better=True) == [0, 50, None, 100]
    assert relative([10, 20, 30], higher_is_better=False) == [100, 50, 0]
    assert relative([5, 5], higher_is_better=True) == [100, 100]


def test_final_score_uses_only_given_indicators_and_weights():
    scores = {"n_balance": 100, "soil_cover": 50, "diversity": 0, "water_demand": 80,
              "climate_risk": None, "simplicity": 20}
    weights = {group: 1.0 for group in GROUPS}
    assert final_score(scores, weights, {"n_balance", "soil_cover", "diversity", "water_demand", "simplicity"}) \
        == pytest.approx((50 + 80 + 20) / 3)
    assert final_score(scores, {"soil_health": 1.0}, {"n_balance", "soil_cover", "diversity"}) == 50


# Validation cases (plan §4.5), on the offline demo snapshots ---------------

@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")


def scored_pair(site, rotation, covers, baseline):
    pair = [evaluate(site, baseline, [None] * len(baseline)), evaluate(site, rotation, covers)]
    score_set(pair)
    return pair


def soil_health(r):
    return np.mean([r["scores"][k] for k in GROUPS["soil_health"]])


def test_ames_maize_soybean_rye_beats_continuous_maize_on_soil_health(offline):
    site = site_context(42.03, -93.62, "us_midwest")
    base, rotation = scored_pair(site, ["maize", "soybean"], [None, "cereal_rye"], ["maize"])
    assert rotation["metrics"]["n_balance"] < base["metrics"]["n_balance"]
    assert rotation["metrics"]["soil_cover"] > base["metrics"]["soil_cover"]
    assert soil_health(rotation) > soil_health(base)


def test_niamey_drought_tolerant_sequence_beats_maize_on_water(offline):
    site = site_context(13.51, 2.16, "semi_arid_tropics")
    base, rotation = scored_pair(site, ["pearl_millet", "cowpea"], [None, None], ["maize"])
    assert rotation["metrics"]["water_demand"] < base["metrics"]["water_demand"]
    assert rotation["scores"]["water_demand"] > base["scores"]["water_demand"]
