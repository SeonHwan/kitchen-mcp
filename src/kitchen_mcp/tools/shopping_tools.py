"""shopping 에이전트의 도구: price_of, build_shopping_list, budget_check.

가격은 '단위당 가격 × 필요한 분량'으로 계산한다 (구매 단위 올림 없음).
"""
from datetime import date


from kitchen_mcp.tools import store


def _price(ingredient, amount):
    """price_of와 build_shopping_list가 같이 쓰는 계산. 도구 객체가 아닌 일반 함수다."""
    ing = store.ingredients().get(ingredient)
    if ing is None:
        return {"error": f"재료 사전에 없음: {ingredient}"}
    return {"ingredient": ingredient, "amount": amount, "unit": ing["unit"],
            "unit_price": ing["price_per_unit"], "price": round(ing["price_per_unit"] * amount)}


def price_of(ingredient: str, amount: float) -> dict:
    """재료 분량의 가격을 계산한다. amount는 재료 사전 단위(g, ml, 개)다. 원 단위로 반올림한다."""
    return _price(ingredient, amount)


def build_shopping_list(recipes: list, servings: int = 0) -> dict:
    """레시피 여러 개를 만들 때 냉장고에서 모자라거나 없는 재료를 모아 장보기 목록과 금액을 만든다.
    같은 재료는 레시피 사이에서 합산한 뒤 재고와 한 번만 비교한다. 유통기한이 지난 재고는 없는 것으로 본다.
    servings는 각 레시피에 적용할 인분 수 (0이면 레시피 기본 인분)."""
    need = {}  # 재료 → 필요 총량
    for key in recipes:
        r = store.recipe_by_name_or_id(key)
        if r is None:
            return {"error": f"레시피를 찾을 수 없음: {key}"}
        factor = (servings / r["servings"]) if servings else 1.0
        for ing in r["ingredients"]:
            need[ing["name"]] = need.get(ing["name"], 0) + ing["amount"] * factor
    valid_stock = {}
    base = date.fromisoformat(store.household()["base_date"])
    for p in store.household()["pantry"]:
        if date.fromisoformat(p["expires"]) >= base:
            valid_stock[p["name"]] = p["amount"]
    items, total = [], 0
    for name in sorted(need):
        lack = round(need[name] - valid_stock.get(name, 0), 2)
        if lack > 0:
            cost = _price(name, lack)["price"]
            items.append({"name": name, "buy": lack, "unit": store.ingredients()[name]["unit"], "price": cost})
            total += cost
    return {"recipes": list(recipes), "items": items, "total_price": total}


def budget_check(total_price: int, budget: int = 0) -> dict:
    """장보기 금액이 예산 안인지 본다. budget이 0이면 이번 주 남은 예산(주간 예산 - 이미 쓴 금액)을 쓴다."""
    h = store.household()
    remaining = h["weekly_budget_won"] - h["spent_this_week_won"]
    limit = budget or remaining
    return {"total_price": total_price, "budget": limit, "within_budget": total_price <= limit,
            "difference": limit - total_price, "used_weekly_remaining": not budget}
