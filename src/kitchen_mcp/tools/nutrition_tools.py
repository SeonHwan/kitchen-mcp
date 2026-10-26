"""nutrition 에이전트의 도구: nutrition_of, check_allergens, diet_rule_check.

알레르기는 '재료의 알레르기 분류와 가족 알레르기 목록이 겹치는가'만 대조한다. 건강·의료 판단은 하지 않는다.
영양 수치는 가상 값이다.
"""

from kitchen_mcp.tools import store

NUTRIENTS = ("kcal", "protein_g", "carb_g", "fat_g", "sodium_mg")


def _nutrition(recipe, servings=0):
    """nutrition_of와 diet_rule_check가 같이 쓰는 계산. 도구 객체가 아닌 일반 함수다."""
    r = store.recipe_by_name_or_id(recipe)
    if r is None:
        return {"error": f"레시피를 찾을 수 없음: {recipe}"}
    factor = (servings / r["servings"]) if servings else 1.0
    total = dict.fromkeys(NUTRIENTS, 0.0)
    for ing in r["ingredients"]:
        grams = store.grams_of(ing["name"], ing["amount"]) * factor
        per100 = store.ingredients()[ing["name"]]["nutrition_per_100g"]
        for n in NUTRIENTS:
            total[n] += per100[n] * grams / 100
    portions = servings or r["servings"]
    return {"recipe": r["name"], "servings": portions,
            "total": {n: round(v, 1) for n, v in total.items()},
            "per_serving": {n: round(v / portions, 1) for n, v in total.items()}}


def nutrition_of(recipe: str, servings: int = 0) -> dict:
    """레시피 전체 영양 합계와 1인분 영양을 계산한다. servings는 '먹는 인원'이 아니라 환산할 인분 수이며,
    0이면 레시피 기본 인분이다. total은 그 인분 전체의 합계, per_serving은 1인분 값이다."""
    return _nutrition(recipe, servings)


def check_allergens(recipe: str, allergies: list = None) -> dict:
    """레시피 재료의 알레르기 분류가 알레르기 목록과 겹치는지 대조한다.
    allergies를 비우면 우리 집 가족 전원의 알레르기 목록을 쓴다. conflicts는 겹친 (재료, 분류) 목록이다."""
    r = store.recipe_by_name_or_id(recipe)
    if r is None:
        return {"error": f"레시피를 찾을 수 없음: {recipe}"}
    if not allergies:
        allergies = sorted({a for m in store.household()["family"] for a in m["allergies"]})
    conflicts = []
    for ing in r["ingredients"]:
        hit = sorted(set(store.ingredients()[ing["name"]]["allergens"]) & set(allergies))
        if hit:
            conflicts.append({"ingredient": ing["name"], "allergens": hit})
    return {"recipe": r["name"], "checked_allergies": list(allergies), "conflicts": conflicts, "safe": not conflicts}


# 식이 규칙은 가상 기준이다 (의학적 근거 없음).
DIET_RULES = {
    "저염": ("sodium_mg", "max", 800.0),      # 1인분 나트륨 800mg 이하
    "저칼로리": ("kcal", "max", 500.0),        # 1인분 500kcal 이하
    "고단백": ("protein_g", "min", 20.0),      # 1인분 단백질 20g 이상
}


def diet_rule_check(recipe: str, rule: str) -> dict:
    """1인분 영양이 식이 규칙(저염 / 저칼로리 / 고단백)을 만족하는지 본다. 기준값은 학습용 가상 값이다."""
    if rule not in DIET_RULES:
        return {"error": f"알 수 없는 규칙: {rule}. 사용 가능: {sorted(DIET_RULES)}"}
    n = _nutrition(recipe)
    if "error" in n:
        return n
    key, kind, limit = DIET_RULES[rule]
    value = n["per_serving"][key]
    ok = value <= limit if kind == "max" else value >= limit
    return {"recipe": n["recipe"], "rule": rule, "nutrient": key, "per_serving": value,
            "limit": limit, "limit_kind": "이하" if kind == "max" else "이상", "pass": ok}
