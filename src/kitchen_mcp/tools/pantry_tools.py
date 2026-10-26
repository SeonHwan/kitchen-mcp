"""pantry 에이전트의 도구: list_pantry, match_recipe_to_pantry, expiring_soon.

기준 날짜는 household.json의 base_date를 쓴다 (코드에 오늘 날짜를 박지 않는다).
"""
from datetime import date


from kitchen_mcp.tools import store


def _days_left(item):
    base = date.fromisoformat(store.household()["base_date"])
    return (date.fromisoformat(item["expires"]) - base).days


def list_pantry() -> dict:
    """냉장고 재고 전체를 돌려준다. [{name, amount, unit, expires, days_left}] 와 기준 날짜."""
    items = [dict(p, days_left=_days_left(p)) for p in store.household()["pantry"]]
    return {"base_date": store.household()["base_date"], "items": items}


def match_recipe_to_pantry(recipe: str, servings: int = 0) -> dict:
    """레시피 재료가 냉장고에 얼마나 있는지 대조한다. 유통기한이 지난 재고는 없는 것으로 본다.
    servings를 주면 그 인분으로 분량을 비례 환산한다 (0이면 레시피 기본 인분).
    돌려주는 값: have(충분), short(부족, 부족량 포함), missing(없음), expired(지난 재고), coverage(충분한 재료 비율)."""
    r = store.recipe_by_name_or_id(recipe)
    if r is None:
        return {"error": f"레시피를 찾을 수 없음: {recipe}"}
    factor = (servings / r["servings"]) if servings else 1.0
    stock = {p["name"]: p for p in store.household()["pantry"]}
    have, short, missing, expired = [], [], [], []
    for ing in r["ingredients"]:
        need = round(ing["amount"] * factor, 2)
        p = stock.get(ing["name"])
        if p is None:
            missing.append({"name": ing["name"], "need": need, "unit": ing["unit"]})
        elif _days_left(p) < 0:
            expired.append({"name": ing["name"], "need": need, "unit": ing["unit"], "expired_on": p["expires"]})
        elif p["amount"] >= need:
            have.append(ing["name"])
        else:
            short.append({"name": ing["name"], "need": need, "have": p["amount"],
                          "lack": round(need - p["amount"], 2), "unit": ing["unit"]})
    total = len(r["ingredients"])
    return {"recipe": r["name"], "servings": servings or r["servings"], "have": have, "short": short,
            "missing": missing, "expired": expired, "coverage": round(len(have) / total, 3)}


def expiring_soon(within_days: int = 3) -> list:
    """기준 날짜로부터 within_days일 이내에 유통기한이 끝나는 재고를 임박한 순으로 돌려준다.
    이미 지난 재고는 days_left가 음수로 함께 나온다."""
    items = [dict(p, days_left=_days_left(p)) for p in store.household()["pantry"]]
    return sorted((p for p in items if p["days_left"] <= within_days), key=lambda p: p["days_left"])
