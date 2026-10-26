"""도구 단위 시험 (모델·임베딩 없이). 실행: uv run python tests/test_tools.py
기대값은 data/*.json 에서 손으로 계산해 적었다 (도구 코드와 같은 식을 복사하지 않았다)."""
import sys

from kitchen_mcp.tools import ALL_TOOLS, TOOL_GROUPS  # noqa: E402
from kitchen_mcp.tools.cooking_tools import estimate_total_time, plan_parallel_steps  # noqa: E402
from kitchen_mcp.tools.nutrition_tools import check_allergens, diet_rule_check, nutrition_of  # noqa: E402
from kitchen_mcp.tools.pantry_tools import expiring_soon, list_pantry, match_recipe_to_pantry  # noqa: E402
from kitchen_mcp.tools.recipe_tools import filter_recipes, get_recipe  # noqa: E402
from kitchen_mcp.tools.shopping_tools import budget_check, build_shopping_list, price_of  # noqa: E402

failed = []


def check(name, cond, detail=""):
    print(("통과 " if cond else "실패 ") + name + ("" if cond else f"  → {detail}"))
    if not cond:
        failed.append(name)


# 구조
check("도구 16개", len(ALL_TOOLS) == 16, len(ALL_TOOLS))
check("에이전트 6명", len(TOOL_GROUPS) == 6)
check("도구 이름 중복 없음", len({t.__name__ for t in ALL_TOOLS}) == 16)

# recipe
check("get_recipe 이름", get_recipe("계란말이")["id"] == "R004")
check("get_recipe 없는 레시피", "error" in get_recipe("없는요리"))
f = filter_recipes(tag="간편", max_total_minutes=10)
check("filter_recipes 태그+시간", all(x["total_minutes"] <= 10 for x in f) and len(f) > 0, f)
# 도구에 적힌 태그 목록이 실제 레시피 데이터의 태그와 정확히 같아야 한다 (어긋나면 모델이 틀린 태그를 쓰게 된다)
from kitchen_mcp.tools.recipe_tools import VALID_TAGS  # noqa: E402
from kitchen_mcp.tools import store  # noqa: E402
data_tags = {t for r in store.recipes().values() for t in r["tags"]}
check("VALID_TAGS가 레시피 데이터의 태그와 일치", set(VALID_TAGS) == data_tags, (set(VALID_TAGS) ^ data_tags))
from kitchen_mcp.tools import TOOLS_BY_NAME  # noqa: E402
# 모델에게 실제로 전달되는 설명(MCP 서버는 함수의 독스트링을 도구 설명으로 쓴다)에 태그가 모두 적혀 있어야 한다
check("filter_recipes 설명(모델에게 전달되는 독스트링)에 모든 태그가 적혀 있음",
      all(t in TOOLS_BY_NAME["filter_recipes"].__doc__ for t in VALID_TAGS))
bad = filter_recipes(tag="저녁")
check("filter_recipes 없는 태그는 오류와 사용 가능한 태그를 돌려줌",
      isinstance(bad, dict) and "error" in bad and "한식" in bad["error"], bad)
check("filter_recipes 오븐 레시피는 보유 장비 필터에서 빠짐",
      "오븐 치킨 구이" not in [x["name"] for x in filter_recipes(only_owned_equipment=True)])

# 영양: 계란말이(2인분) = 달걀 4개(220g) + 당근 0.25개(37.5g) + 대파 10g + 소금 2g + 식용유 10ml(9.2g)
# 열량 = 143*2.2 + 41*0.375 + 30*0.1 + 0 + 884*0.092 = 314.6 + 15.375 + 3 + 81.328 = 414.303
n = nutrition_of("계란말이")
check("nutrition_of 열량 합계 ≈ 414.3", abs(n["total"]["kcal"] - 414.3) < 0.15, n["total"])
check("nutrition_of 1인분 = 합계/2", abs(n["per_serving"]["kcal"] - 207.2) < 0.2, n["per_serving"])
n4 = nutrition_of("계란말이", servings=4)
check("nutrition_of 인분 환산(4인분 = 2배)", abs(n4["total"]["kcal"] - 828.6) < 0.3, n4["total"])

# 알레르기
a = check_allergens("땅콩버터 바나나 토스트")
check("땅콩 알레르기 충돌 감지(가족 목록 사용)",
      a["checked_allergies"] == ["땅콩"] and a["conflicts"][0]["ingredient"] == "땅콩버터" and not a["safe"], a)
check("땅콩 없는 레시피는 안전", check_allergens("김치찌개")["safe"] is True)
check("직접 준 알레르기 목록 사용", check_allergens("계란말이", ["계란"])["conflicts"][0]["allergens"] == ["계란"])
check("diet_rule_check 알 수 없는 규칙", "error" in diet_rule_check("김치찌개", "없는규칙"))

# pantry (기준 날짜 2026-10-23)
exp = expiring_soon(0)
names = [p["name"] for p in exp]
check("expiring_soon(0): 지난 요거트와 오늘 만료 방울토마토", names == ["플레인요거트", "방울토마토"], names)
check("list_pantry 34종", len(list_pantry()["items"]) == 34)
m = match_recipe_to_pantry("계란말이")  # 달걀 4(재고 6) 당근 0.25(2) 대파 10(100) 소금 2(500) 식용유 10(700) → 전부 충분
check("match_recipe_to_pantry 계란말이는 전부 충분", m["coverage"] == 1.0 and not m["short"] and not m["missing"], m)
m2 = match_recipe_to_pantry("계란말이", servings=14)  # 2인분 달걀 4개 → 14인분은 28개 필요, 재고 6 → 22 부족
check("match_recipe_to_pantry 인분 환산 부족량",
      any(s["name"] == "달걀" and s["need"] == 28 and s["lack"] == 22 for s in m2["short"]), m2["short"])
m3 = match_recipe_to_pantry("요거트 과일볼")  # 플레인요거트는 유통기한 지남 → expired
check("유통기한 지난 재고는 expired로 분류", any(e["name"] == "플레인요거트" for e in m3["expired"]), m3)

# 장보기
check("price_of 달걀 3개 = 1050원", price_of("달걀", 3)["price"] == 1050)
check("price_of 없는 재료", "error" in price_of("유니콘", 1))
s = build_shopping_list(["요거트 과일볼"])  # 요거트(만료)300g*4=1200, 사과1(재고2) X, 바나나1*500, 딸기100*14, 꿀20*12, 호두20*25
check("build_shopping_list 만료 재고는 새로 사야 함", any(i["name"] == "플레인요거트" and i["buy"] == 300 for i in s["items"]), s)
check("build_shopping_list 합계 = 항목 합", s["total_price"] == sum(i["price"] for i in s["items"]))
both = build_shopping_list(["계란말이", "치즈 오믈렛"])  # 달걀 4+4=8, 재고 6 → 2개 부족(합산 후 비교)
check("build_shopping_list 레시피 간 재료 합산 후 재고 비교",
      any(i["name"] == "달걀" and i["buy"] == 2 for i in both["items"]), both["items"])
b = budget_check(70000)  # 남은 예산 150000-90000 = 60000
check("budget_check 기본은 남은 예산 6만원", b["budget"] == 60000 and not b["within_budget"] and b["difference"] == -10000, b)
check("budget_check 직접 준 예산", budget_check(15000, 20000)["within_budget"] is True)

# 조리: 잔치국수 = 육수12(대기) / 볶기8(겹침) / 지단5(겹침) / 삶기5(대기) / 담기3 → 순차 33
e = estimate_total_time("잔치국수")
check("estimate_total_time 합계 33, 사람이 붙는 시간 16", e["total_minutes"] == 33 and e["active_minutes"] == 16, e)
check("오븐 레시피는 장비 부족 표시", estimate_total_time("오븐 치킨 구이")["can_cook_with_owned_equipment"] is False)
p = plan_parallel_steps("잔치국수")
check("plan_parallel_steps는 순차보다 짧거나 같다", p["parallel_minutes"] <= p["sequential_minutes"], p)
# 육수 0~12 / 볶기 0~8 / 지단 8~13 (사람은 한 명이라 볶기 뒤) / 삶기 13~18 / 담기 18~21 → 21분
check("plan_parallel_steps 잔치국수 병렬 21분(순차 33분)",
      p["parallel_minutes"] == 21 and p["saved_minutes"] == 12, p["schedule"])
q = plan_parallel_steps("계란말이")  # 병렬 표시 없음 → 순차와 같다
check("병렬 표시 없는 레시피는 순차와 같다", q["parallel_minutes"] == q["sequential_minutes"] == 15, q)
check("plan_parallel_steps 없는 레시피", "error" in plan_parallel_steps("없는요리"))

print()
print("실패", len(failed), "개" if failed else "— 전부 통과")
sys.exit(1 if failed else 0)
