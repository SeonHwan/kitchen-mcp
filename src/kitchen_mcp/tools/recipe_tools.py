"""recipe 에이전트의 도구: search_recipes, get_recipe, filter_recipes."""

from kitchen_mcp.tools import store
from kitchen_mcp.tools.embedding import recipe_index


def search_recipes(query: str, top_k: int = 5) -> list:
    """질문과 의미가 비슷한 레시피를 임베딩 검색으로 찾는다. [{id, name, score}] 를 점수 순으로 돌려준다."""
    hits = recipe_index().search(query, k=top_k)
    return [{"id": h["id"], "name": store.recipes()[h["id"]]["name"], "score": h["score"]} for h in hits]


def get_recipe(recipe: str) -> dict:
    """레시피 id(R001) 또는 이름으로 상세(재료, 단계, 장비, 태그, 인분)를 가져온다. 없으면 {'error': ...}."""
    r = store.recipe_by_name_or_id(recipe)
    if r is None:
        return {"error": f"레시피를 찾을 수 없음: {recipe}"}
    return r


VALID_TAGS = ("간편", "구이", "국물", "면", "반찬", "밥", "볶음", "부침", "샐러드", "아이", "야식", "양식", "일식", "중식", "한식")


def filter_recipes(tag: str = "", max_total_minutes: int = 0, only_owned_equipment: bool = False):
    """태그, 순차 합계 시간(분), 보유 장비로 레시피를 거른다. 조건을 비워 두면(''/0/False) 그 조건은 적용하지 않는다.
    tag는 반드시 다음 중 하나다: 간편, 구이, 국물, 면, 반찬, 밥, 볶음, 부침, 샐러드, 아이, 야식, 양식, 일식, 중식, 한식.
    ('저녁', '매콤' 같은 다른 말은 태그가 아니다. 그런 조건은 search_recipes로 찾는다.)
    시간은 단계를 차례로 했을 때의 합계다 (병렬 고려 없음). [{id, name, total_minutes}] 를 돌려준다.
    없는 태그를 주면 {'error': ...} 로 사용 가능한 태그를 알려 준다."""
    if tag and tag not in VALID_TAGS:
        return {"error": f"알 수 없는 태그: {tag}. 사용 가능한 태그: {', '.join(VALID_TAGS)}"}
    owned = set(store.household()["equipment"])
    result = []
    for r in store.recipes().values():
        total = sum(s["minutes"] for s in r["steps"])
        if tag and tag not in r["tags"]:
            continue
        if max_total_minutes and total > max_total_minutes:
            continue
        if only_owned_equipment and set(r["equipment"]) - owned:
            continue
        result.append({"id": r["id"], "name": r["name"], "total_minutes": total})
    return result
