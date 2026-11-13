import pytest
from fastapi.testclient import TestClient

from main import app

AMES = {"lat": 42.03, "lon": -93.62}
NIAMEY = {"lat": 13.51, "lon": 2.16}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")  # demo snapshots only, no network
    return TestClient(app)


def test_climate_shift(client):
    body = client.get("/api/climate-shift", params=AMES).json()
    assert body["zone"] == "north_temperate" and body["offline"] is True
    rows = {r["indicator"]: r for r in body["indicators"]}
    assert rows["frost_free_days"]["then_display"] == "168" and rows["frost_free_days"]["now_display"] == "179"
    assert "Oct 19" in rows["first_fall_frost"]["text"]
    assert rows["first_fall_frost"]["direction"] == "up" and "cover crop" in rows["first_fall_frost"]["meaning"]


def test_climate_shift_tropical_has_rainy_season_not_frost(client):
    rows = {r["indicator"] for r in client.get("/api/climate-shift", params=NIAMEY).json()["indicators"]}
    assert {"rain_onset", "rain_end", "season_length"} <= rows
    assert "first_fall_frost" not in rows and "gdd" not in rows


def test_small_changes_read_as_little_change(client):
    rows = {r["indicator"]: r for r in client.get("/api/climate-shift", params=NIAMEY).json()["indicators"]}
    assert rows["heat_stress_days"]["direction"] == "same"      # 202 -> 198 days
    assert rows["heat_stress_days"]["meaning"] == "Little change."


def test_soil(client):
    body = client.get("/api/soil", params=NIAMEY).json()
    assert body["source"] == "SoilGrids 2.0" and body["profile"]["texture_class"] == "sandy loam"
    assert "loam" in body["manual_textures"]


def test_hazards_is_geojson(client):
    body = client.get("/api/hazards", params=AMES).json()
    assert body["type"] == "FeatureCollection" and len(body["features"]) == 12


def test_crops_for_point(client):
    body = client.get("/api/crops", params=NIAMEY).json()
    assert body["zone"] == "tropical" and body["pack"] == "semi_arid_tropics"
    assert {"id": "pearl_millet", "name": "Pearl millet", "family": "grass", "type": "cash"} in body["crops"]
    assert client.get("/api/crops", params={**AMES, "pack": "mars"}).status_code == 422


def test_demo_sites(client):
    body = client.get("/api/demo-sites").json()
    assert body["offline"] is True
    assert {"id": "niamey_ne", "name": "Niamey area, Niger", "lat": 13.51, "lon": 2.16} in body["sites"]


def test_crops_prefill_demo_baseline(client):
    assert client.get("/api/crops", params=NIAMEY).json()["baseline"] == ["pearl_millet"]
    assert client.get("/api/crops", params=AMES).json()["baseline"] == ["maize"]


def test_offline_error_names_the_fix(client):
    body = client.get("/api/climate-shift", params={"lat": 10.0, "lon": 10.0})
    assert body.status_code == 503 and "Pick a demo field" in body.json()["detail"]


def test_methodology_lists_formulas_inputs_and_sources(client):
    body = client.get("/api/methodology", params={"pack": "us_midwest"}).json()
    assert set(body["indicators"]) == {"n_balance", "soil_cover", "diversity", "water_demand", "climate_risk", "simplicity"}
    assert all(i["formula"] for i in body["indicators"].values()) and "100 x" in body["final"]
    maize = body["crops"]["maize"]
    assert maize["library"]["kc"] == {"value": {"ini": 0.3, "mid": 1.2, "end": [0.35, 0.6]}, "source": "fao56_t12"}
    assert maize["pack"]["n_need_kg_ha"]["source"] == "isu_n_2008"
    used = {f["source"] for c in body["crops"].values() for f in [*c["library"].values(), *c["pack"].values()]
            if f["value"] is not None}
    assert used <= set(body["sources"])          # every value used names a listed source
    assert "power" in body["sources"]
    assert client.get("/api/methodology", params={"pack": "mars"}).status_code == 422


def test_recommend(client):
    body = client.post("/api/recommend", json={**AMES, "baseline": ["maize"]}).json()
    assert body["pack"] == "us_midwest"
    finals = [r["final"] for r in body["rotations"]]
    assert 2 <= len(finals) <= 5 and finals == sorted(finals, reverse=True)
    assert all(2 <= len(r["reasons"]) <= 4 for r in body["rotations"])
    assert body["baseline"]["label"] == "continuous maize" and body["baseline"]["final"] == 46.1


def test_recommendations_show_one_rotation_per_crop_set(client):
    body = client.post("/api/recommend", json={**AMES, "baseline": ["maize"]}).json()
    crop_sets = [frozenset(r["rotation"]) for r in body["rotations"]]
    assert len(crop_sets) == len(set(crop_sets))                  # no 2-year vs 3-year alfalfa twins
    assert ["maize", "soybean"] in [r["rotation"] for r in body["rotations"]]   # corn-soybean now surfaces


def test_alfalfa_is_excluded_on_poorly_drained_soil(client):
    soil = {"texture_class": "silty clay loam", "awc_mm_per_m": 141, "drainage": "Poorly drained"}
    body = client.post("/api/recommend", json={**AMES, "baseline": ["maize"], "soil": soil}).json()
    assert body["rotations"] and not any("alfalfa" in r["rotation"] for r in body["rotations"])
    swap = client.post("/api/score", json={**AMES, "baseline": ["maize"], "soil": soil,
                                           "rotation": ["alfalfa", "alfalfa", "maize"]}).json()
    assert swap["rank"] is None
    assert swap["rotation"]["rule_breaks"] == ["soil: Alfalfa (hay) does not suit poorly drained soil"]


def test_adding_hay_to_a_grain_farm_costs_simplicity(client):
    body = client.post("/api/recommend", json={**AMES, "baseline": ["maize"]}).json()
    hay = next(r for r in body["rotations"] if "alfalfa" in r["rotation"])
    assert hay["metrics"]["simplicity"] == len(set(hay["rotation"])) + 1 + 2   # +1 equipment, +2 new to the farm
    with_hay = client.post("/api/recommend", json={**AMES, "baseline": ["alfalfa", "alfalfa", "maize"]}).json()
    hay = next(r for r in with_hay["rotations"] if "alfalfa" in r["rotation"])
    assert hay["metrics"]["simplicity"] == len(set(hay["rotation"])) + 1        # already grows hay: no transition cost


def test_reasons_skip_et0_change_the_climate_card_calls_small(client):
    # Niamey ET0 2585 -> 2512 mm (-2.8%) reads "no clear change" on the Climate shift card
    body = client.post("/api/recommend", json={**NIAMEY, "baseline": ["pearl_millet"]}).json()
    reasons = [text for r in body["rotations"] for text in r["reasons"]]
    assert any("Irrigation gap" in t for t in reasons) and not any("ET0" in t for t in reasons)
    ames = client.post("/api/recommend", json={**AMES, "baseline": ["maize"]}).json()
    assert any("yearly ET0 has risen 46 mm" in t for r in ames["rotations"] for t in r["reasons"])


def test_data_gaps_drop_a_measure_instead_of_leaving_one_rotation(client):
    # Sorghum has a sourced residue class but most partner crops do not: soil cover would leave 1 rotation
    body = client.post("/api/recommend", json={**NIAMEY, "baseline": ["sorghum"]}).json()
    assert body["n_comparable"] >= 5 and len(body["rotations"]) >= 2 and "soil_cover" not in body["ranked_on"]
    assert "water_demand" in body["ranked_on"]


def test_recommend_weights_and_years(client):
    req = {**AMES, "baseline": ["maize"], "years": [2], "weights": {"soil_health": 1, "water": 0, "stability": 0, "simplicity": 0}}
    body = client.post("/api/recommend", json=req).json()
    assert all(len(r["rotation"]) == 2 for r in body["rotations"])
    assert body["rotations"][0]["final"] > body["baseline"]["final"]


def test_recommend_uses_manual_soil_texture(client):
    body = client.post("/api/recommend", json={**AMES, "baseline": ["maize"], "soil": {"texture_class": "sand"}}).json()
    assert body["soil"]["awc_mm_per_m"] == 80


def test_score_user_rotation(client):
    body = client.post("/api/score", json={**AMES, "baseline": ["maize"], "rotation": ["maize", "soybean"]}).json()
    rotation = body["rotation"]
    assert rotation["covers"] == [None, "cereal_rye"]  # cover crop picked automatically
    assert rotation["rule_breaks"] == [] and body["rank"] == body["n_comparable"] == 11


def test_score_reports_rule_breaks(client):
    body = client.post("/api/score", json={**AMES, "baseline": ["maize"], "rotation": ["maize", "maize", "soybean"]}).json()
    assert any(b.startswith("repeat") for b in body["rotation"]["rule_breaks"])
    assert body["rank"] is None and body["rotation"]["final"] is not None   # scored, but not ranked


@pytest.mark.parametrize("path, req, status", [
    ("/api/recommend", {**AMES, "baseline": ["cassava"]}, 422),       # crop not in the pack
    ("/api/recommend", {**AMES, "baseline": ["maize"], "pack": "mars"}, 422),
    ("/api/recommend", {**AMES, "baseline": ["maize"], "soil": {"texture_class": "gravel"}}, 422),
    ("/api/recommend", {"lat": 10.0, "lon": 10.0, "baseline": ["maize"]}, 503),  # offline, no snapshot
    ("/api/recommend", {"lat": 95, "lon": 0, "baseline": ["maize"]}, 422),
])
def test_bad_requests(client, path, req, status):
    assert client.post(path, json=req).status_code == status


def test_bad_query(client):
    assert client.get("/api/soil", params={"lat": 42}).status_code == 422
