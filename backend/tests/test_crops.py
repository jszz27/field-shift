import copy
import json

import pytest

from crops import crops_for_pack, load, missing, validate


@pytest.fixture(scope="module")
def data():
    return load()


@pytest.fixture
def bad(data):
    return copy.deepcopy(data)


def test_real_file_is_valid(data):
    assert validate(data) == []


@pytest.mark.parametrize("pack, expected", [
    ("us_midwest", {"maize", "soybean", "winter_wheat", "oats", "alfalfa", "cereal_rye", "crimson_clover", "radish"}),
    ("semi_arid_tropics", {"sorghum", "pearl_millet", "chickpea", "pigeon_pea", "groundnut", "cowpea"}),
    ("humid_tropics", {"rice", "maize", "cassava", "cowpea"}),
    ("south_temperate", {"soybean", "maize", "winter_wheat"}),
])
def test_pack_crops(data, pack, expected):
    assert set(crops_for_pack(pack, data)) == expected


def test_pack_merges_library_and_local_timing(data):
    maize = crops_for_pack("us_midwest", data)["maize"]
    assert maize["family"] == "grass"                      # from the library
    assert maize["season_windows"]["us_midwest"]["plant"] == ["04-25", "05-18"]  # from the pack
    assert maize["pack"]["stage_days"]["mid"] == 50


def test_missing_field_is_reported(bad):
    del bad["crops"]["maize"]["ky"]
    assert "crops.maize: missing field 'ky'" in validate(bad)


def test_value_without_source_is_reported(bad):
    del bad["crops"]["maize"]["sources"]["ky"]
    assert any(e.startswith("crops.maize.ky: no valid source") for e in validate(bad))


def test_unknown_source_id_is_reported(bad):
    bad["packs"]["us_midwest"]["crops"]["maize"]["sources"]["stage_days"] = "made_up"
    assert any("us_midwest.maize.stage_days: no valid source" in e for e in validate(bad))


def test_out_of_range_value_is_reported(bad):
    bad["crops"]["maize"]["kc"]["mid"] = 3.0
    assert "crops.maize.kc: 3.0 outside 0-1.5" in validate(bad)


def test_reversed_range_is_reported(bad):
    bad["crops"]["maize"]["rooting_depth_m"] = [1.7, 1.0]
    assert any("rooting_depth_m: range [1.7, 1.0]" in e for e in validate(bad))


def test_bad_enum_is_reported(bad):
    bad["crops"]["maize"]["n_effect"] = "hungry"
    assert any("crops.maize.n_effect: 'hungry'" in e for e in validate(bad))


def test_pack_crop_must_exist_in_library(bad):
    bad["packs"]["humid_tropics"]["crops"]["yam"] = {"sources": {}}
    assert "packs.humid_tropics.yam: crop not in library" in validate(bad)


def test_bad_date_is_reported(bad):
    bad["packs"]["us_midwest"]["crops"]["maize"]["plant"] = ["04-31x", "05-18"]
    assert any("is not MM-DD" in e for e in validate(bad))


def test_missing_lists_nested_nulls(data):
    gaps = missing(data)
    assert "crops.oats.ky" in gaps
    assert "packs.us_midwest.soybean.next_crop_n_adjust_kg_ha.cool" in gaps
    assert not any(p.endswith("_note") for p in gaps)


def test_load_rejects_invalid_file(bad, tmp_path):
    bad["crops"]["maize"]["kc"]["mid"] = 3.0
    path = tmp_path / "crops.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="kc: 3.0"):
        load(path)
