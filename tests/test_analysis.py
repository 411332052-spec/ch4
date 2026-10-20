import json

import pytest

from foodlog.analysis import AnalysisFailed, AnalysisInvalid, parse_analysis
from foodlog.analyzer import extract_payload


def good(**over):
    base = {
        "is_food": True,
        "name": "雞腿便當",
        "ingredients": ["白飯", "炸雞腿"],
        "weight_g": 650,
        "calories_kcal": 920,
    }
    return {**base, **over}


def test_valid_food():
    a = parse_analysis(good())
    assert (a.is_food, a.name, a.weight_g, a.calories_kcal) == (True, "雞腿便當", 650, 920)
    assert a.ingredients == ("白飯", "炸雞腿")


def test_numeric_strings_are_accepted_but_decorated_ones_are_not():
    assert parse_analysis(good(weight_g="650", calories_kcal=" 920.4 ")).calories_kcal == 920
    for bad in ("約350大卡", "很多", "", "NaN", "1e3"):
        with pytest.raises(AnalysisInvalid):
            parse_analysis(good(calories_kcal=bad))


@pytest.mark.parametrize("bad", [True, None, [], {}, -5, float("nan"), float("inf")])
def test_bad_numbers(bad):
    with pytest.raises(AnalysisInvalid):
        parse_analysis(good(weight_g=bad))
    with pytest.raises(AnalysisInvalid):
        parse_analysis(good(calories_kcal=bad))


def test_out_of_range_and_zero_weight_food():
    with pytest.raises(AnalysisInvalid):
        parse_analysis(good(calories_kcal=99999))
    with pytest.raises(AnalysisInvalid):
        parse_analysis(good(weight_g=0))


@pytest.mark.parametrize("payload", [None, [], "text", 5, {}])
def test_not_an_object(payload):
    with pytest.raises(AnalysisInvalid):
        parse_analysis(payload)


def test_missing_field_and_wrong_types():
    p = good()
    del p["ingredients"]
    with pytest.raises(AnalysisInvalid):
        parse_analysis(p)
    with pytest.raises(AnalysisInvalid):
        parse_analysis(good(is_food="yes"))
    with pytest.raises(AnalysisInvalid):
        parse_analysis(good(name="   "))
    with pytest.raises(AnalysisInvalid):
        parse_analysis(good(ingredients="白飯"))


def test_not_food_forces_zero_and_drops_ingredients():
    a = parse_analysis(good(is_food=False, name="馬克杯", weight_g=300, calories_kcal=500))
    assert (a.is_food, a.name, a.weight_g, a.calories_kcal, a.ingredients) == (False, "馬克杯", 0, 0, ())


def test_long_text_is_truncated():
    a = parse_analysis(good(name="x" * 100, ingredients=["y" * 100] * 30))
    assert len(a.name) == 40
    assert len(a.ingredients) == 15 and all(len(i) == 30 for i in a.ingredients)


def test_extract_payload_prefers_structured_output():
    outer = {"structured_output": good(), "result": "ignored"}
    assert extract_payload(json.dumps(outer)) == good()


def test_extract_payload_falls_back_to_result_text_and_code_fences():
    outer = {"result": "```json\n" + json.dumps(good()) + "\n```"}
    assert extract_payload(json.dumps(outer)) == good()


def test_extract_payload_garbage():
    for stdout in ("", "not json", "[]", json.dumps({"result": "hello"}), json.dumps({"result": 5})):
        with pytest.raises(AnalysisInvalid):
            extract_payload(stdout)


def test_extract_payload_claude_error():
    with pytest.raises(AnalysisFailed):
        extract_payload(json.dumps({"is_error": True, "result": "quota exceeded"}))
