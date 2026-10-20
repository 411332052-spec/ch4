"""claude -p 回傳結果的格式定義與檢查。

AI 回來的東西一律當成「不可信的字串」，這裡逐欄檢查，通過才算數。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "is_food": {"type": "boolean"},
        "name": {"type": "string"},
        "ingredients": {"type": "array", "items": {"type": "string"}},
        "weight_g": {"type": "number"},
        "calories_kcal": {"type": "number"},
    },
    "required": ["is_food", "name", "ingredients", "weight_g", "calories_kcal"],
    "additionalProperties": False,
}

MAX_NAME_CHARS = 40
MAX_INGREDIENTS = 15
MAX_INGREDIENT_CHARS = 30
MAX_WEIGHT_G = 5000
MAX_CALORIES_KCAL = 5000


class AnalysisError(Exception):
    """分析失敗的共同父類別。"""


class AnalysisInvalid(AnalysisError):
    """AI 回來的內容不合格（可以重試一次）。"""


class AnalysisFailed(AnalysisError):
    """逾時、啟動失敗、額度用完等（不重試，省額度）。"""


@dataclass(frozen=True)
class Analysis:
    is_food: bool
    name: str  # 食物：這餐的名稱；不是食物：那到底是什麼
    ingredients: tuple[str, ...]
    weight_g: int
    calories_kcal: int


_NUMBER_TEXT = re.compile(r"\s*\d+(?:\.\d+)?\s*")


def _to_number(value: object, field: str) -> float:
    """數字，或「純數字的字串」（如 "350"）。"約350大卡"、NaN、負數都不收。"""
    if isinstance(value, bool):
        raise AnalysisInvalid(f"{field} 不是數字（是 true/false）")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and _NUMBER_TEXT.fullmatch(value):
        number = float(value)
    else:
        raise AnalysisInvalid(f"{field} 不是數字：{value!r}")
    if not math.isfinite(number) or number < 0:
        raise AnalysisInvalid(f"{field} 不是合理的數字：{value!r}")
    return number


def parse_analysis(payload: object) -> Analysis:
    if not isinstance(payload, dict):
        raise AnalysisInvalid("結果不是 JSON 物件")
    for key in JSON_SCHEMA["required"]:
        if key not in payload:
            raise AnalysisInvalid(f"缺少欄位 {key}")

    is_food = payload["is_food"]
    if not isinstance(is_food, bool):
        raise AnalysisInvalid(f"is_food 不是 true/false：{is_food!r}")

    name = payload["name"]
    if not isinstance(name, str):
        raise AnalysisInvalid("name 不是文字")
    name = " ".join(name.split())[:MAX_NAME_CHARS]
    if not name:
        raise AnalysisInvalid("name 是空的")

    raw_ingredients = payload["ingredients"]
    if not isinstance(raw_ingredients, list) or not all(isinstance(i, str) for i in raw_ingredients):
        raise AnalysisInvalid("ingredients 不是文字清單")
    ingredients = tuple(
        cleaned[:MAX_INGREDIENT_CHARS]
        for item in raw_ingredients[:MAX_INGREDIENTS]
        if (cleaned := " ".join(item.split()))
    )

    weight = _to_number(payload["weight_g"], "weight_g")
    calories = _to_number(payload["calories_kcal"], "calories_kcal")

    if not is_food:
        # 不是食物：不管 AI 回什麼數字，一律 0；成份欄之後會用 name 取代
        return Analysis(False, name, (), 0, 0)

    if weight <= 0:
        raise AnalysisInvalid("食物的重量不可能是 0")
    if weight > MAX_WEIGHT_G or calories > MAX_CALORIES_KCAL:
        raise AnalysisInvalid(f"數字超出單餐合理範圍：{weight} 公克、{calories} 大卡")
    return Analysis(True, name, ingredients, round(weight), round(calories))
