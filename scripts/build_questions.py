"""질문 세트 60문항 생성 스크립트.

질문마다 정답 근거와 기준 값을 '데이터와 도구 실행 결과'에서 계산해 기록한다 (모델이 쓰지 않는다).
유형별 개수: 단일 15 / 에이전트 2~3명 20 / 에이전트 4명 이상 15 / 범위 밖 10.

기준 날짜 2026-10-23, 우리 집 상태(data/household.json) 기준이다. 모든 값은 학습용 가상 값이다.
`reference`(기준 답 문장)는 템플릿 문장에 계산된 값을 채워 만든다. 사람이 읽어 검증하지 않았다.

실행: uv run python scripts/build_questions.py
결과: data/questions.json (프로그램용), data/questions.csv (사람이 보는 용)
"""
import csv
import json
from pathlib import Path

from kitchen_mcp.tools import TOOL_OWNER, TOOLS_BY_NAME, store

QUESTIONS = []


def call(name, **args):
    """기대 도구 호출 한 건: 이름과 인자."""
    return {"name": name, "args": args}


SEARCH_TOOLS = {"search_recipes", "find_substitute", "storage_tip"}


def run(c):
    """기대 도구 호출을 실제로 실행해 결과를 얻는다 (기준 값 계산용).
    검색 도구는 임베딩 모델이 필요하고 결과가 모델 의존이라 기준 값이 될 수 없다. 대신 reference_docs로 정답 문서를 지정한다."""
    if c["name"] in SEARCH_TOOLS:
        raise ValueError(f"검색 도구는 기준 값 계산에 쓰지 않는다: {c['name']}")
    return TOOLS_BY_NAME[c["name"]](**c["args"])


def add(type_, question, calls, reference, outcome, topics, docs=None):
    """질문 한 개를 등록한다. expected_agents는 기대 도구 호출의 소유 에이전트에서 자동으로 구한다."""
    agents = sorted({TOOL_OWNER[c["name"]] for c in calls}, key=list(
        ["recipe", "pantry", "nutrition", "substitute", "shopping", "cooking"]).index)
    QUESTIONS.append({
        "id": f"Q{len(QUESTIONS) + 1:02d}", "question": question, "type": type_,
        "expected_agents": agents, "reference_tool_calls": calls,
        "reference_docs": docs or [], "reference": reference,
        "reference_outcome": outcome, "reference_topics": topics,
    })


def recipe_id(name):
    return store.recipe_by_name_or_id(name)["id"]


def sub_id(src, dst):
    return next(s["id"] for s in store.substitutes() if s["from"] == src and s["to"] == dst)


def note_id(ingredient, situation):
    return next(n["id"] for n in store.storage_notes() if n["ingredient"] == ingredient and n["situation"] == situation)


def won(n):
    return f"{n:,}원"


T_ONE, T_MID, T_MANY, T_OUT = "단일", "2~3명", "4명 이상", "범위 밖"
OUT_REF = "주방·요리와 관련 없는 질문이라 도구를 호출하지 않고 이 서비스의 범위 밖이라고 답해야 한다."

# ───────────────────────── 단일 에이전트 15 ─────────────────────────
# recipe 3
c = call("search_recipes", query="매콤한 국물 요리", top_k=5)
# 정답 근거: 국물 태그이면서 매운 재료(고춧가루·고추장·청양고추)를 쓰는 레시피 (데이터에서 계산)
spicy = [r["name"] for r in store.recipes().values()
         if "국물" in r["tags"] and {i["name"] for i in r["ingredients"]} & {"고춧가루", "고추장", "청양고추"}]
add(T_ONE, "매콤하고 국물 있는 요리 뭐가 있어?", [c],
    "국물 태그이면서 고춧가루·고추장·청양고추를 쓰는 레시피: " + ", ".join(spicy) + ".",
    "매콤한 국물 요리 후보를 제시한다", ["레시피 추천"], docs=[recipe_id(n) for n in spicy])
c = call("get_recipe", recipe="제육볶음")
r = run(c)
add(T_ONE, "제육볶음 재료랑 만드는 순서 알려줘.", [c],
    f"제육볶음({r['servings']}인분) 재료: " + ", ".join(f"{i['name']} {i['amount']}{i['unit']}" for i in r["ingredients"])
    + ". 단계: " + " → ".join(s["desc"] for s in r["steps"]) + ".",
    "제육볶음의 재료와 단계를 안내한다", ["레시피 조회"], docs=[recipe_id("제육볶음")])
c = call("filter_recipes", tag="양식", max_total_minutes=20, only_owned_equipment=True)
names = [x["name"] for x in run(c)]
add(T_ONE, "우리 집 장비로 20분 안에 되는 양식 레시피 보여줘.", [c],
    f"조건에 맞는 레시피 {len(names)}개: " + ", ".join(names) + ".",
    "조건에 맞는 레시피 목록을 제시한다", ["레시피 필터"], docs=[recipe_id(n) for n in names])
# pantry 3
c = call("list_pantry")
add(T_ONE, "지금 냉장고에 뭐 있어?", [c], f"재고는 총 {len(run(c)['items'])}종이다.",
    "냉장고 재고를 안내한다", ["냉장고 재고"])
c = call("expiring_soon", within_days=2)
items = run(c)
add(T_ONE, "이틀 안에 상하는 재료 알려줘.", [c],
    "이틀 이내(이미 지난 것 포함): " + ", ".join(f"{p['name']}({p['days_left']}일)" for p in items) + ".",
    "임박·지난 재고를 알려준다", ["유통기한"])
c = call("match_recipe_to_pantry", recipe="김치볶음밥")
m = run(c)
add(T_ONE, "지금 있는 재료로 김치볶음밥 만들 수 있어?", [c],
    f"충분한 재료 비율 {m['coverage']:.0%}. 부족 {len(m['short'])}개, 없음 {len(m['missing'])}개"
    + (f"({', '.join(x['name'] for x in m['missing'])})" if m["missing"] else "") + ".",
    "재고로 만들 수 있는지 판단한다", ["냉장고 재고"], docs=[recipe_id("김치볶음밥")])
# nutrition 3
c = call("nutrition_of", recipe="카레라이스")
n = run(c)
add(T_ONE, "카레라이스 1인분 열량이랑 단백질이 얼마야?", [c],
    f"카레라이스 1인분 열량 {n['per_serving']['kcal']}kcal, 단백질 {n['per_serving']['protein_g']}g이다.",
    "1인분 영양을 안내한다", ["영양"], docs=[recipe_id("카레라이스")])
c = call("check_allergens", recipe="땅콩소스 비빔국수", allergies=["땅콩"])
a = run(c)
add(T_ONE, "땅콩 알레르기 있는데 땅콩소스 비빔국수 먹어도 돼?", [c],
    "땅콩 분류 재료가 포함되어 있다: " + ", ".join(x["ingredient"] for x in a["conflicts"]) + ". 알레르기 분류 목록 대조 결과이며 의료 판단이 아니다.",
    "알레르기 충돌을 알린다", ["알레르기"], docs=[recipe_id("땅콩소스 비빔국수")])
c = call("diet_rule_check", recipe="된장찌개", rule="저염")
d = run(c)
add(T_ONE, "된장찌개가 저염 기준에 맞아?", [c],
    f"된장찌개 1인분 나트륨 {d['per_serving']}mg으로 기준 {d['limit']:.0f}mg {d['limit_kind']}을 " + ("만족한다." if d["pass"] else "만족하지 않는다."),
    "저염 규칙 판정을 알린다", ["식이"], docs=[recipe_id("된장찌개")])
# substitute 2
c = call("find_substitute", query="달걀이 없을 때 대신 쓸 수 있는 재료", top_k=3)
add(T_ONE, "달걀이 없는데 대신 뭘 쓸 수 있어?", [c],
    f"대체 규칙: 달걀 대신 두부를 쓸 수 있다. 비율 달걀 1g당 두부 1.0g. {store.substitutes()[0]['note']}",
    "대체 재료와 차이를 안내한다", ["대체 재료"], docs=[sub_id("달걀", "두부")])
c = call("storage_tip", query="남은 밥 보관 방법", top_k=3)
add(T_ONE, "남은 밥은 어떻게 보관해?", [c],
    "밥은 식은 뒤 밀폐해 냉장 2일, 뜨거울 때 1회분씩 랩에 싸 냉동하면 30일 보관할 수 있다.",
    "밥 보관법을 안내한다", ["보관"], docs=[note_id("밥", "냉장"), note_id("밥", "냉동")])
# shopping 2
c = call("price_of", ingredient="소고기 불고기용", amount=300)
add(T_ONE, "소고기 불고기용 300g은 얼마야?", [c], f"소고기 불고기용 300g은 {won(run(c)['price'])}이다.",
    "가격을 계산해 안내한다", ["가격"])
c = call("budget_check", total_price=45000)
b = run(c)
add(T_ONE, "장을 4만 5천 원어치 보려는데 이번 주 예산 안이야?", [c],
    f"이번 주 남은 예산 {won(b['budget'])} 대비 45,000원은 " + ("예산 안이다." if b["within_budget"] else "예산을 초과한다."),
    "남은 예산 대비 판정을 알린다", ["예산"])
# cooking 2
c = call("estimate_total_time", recipe="잔치국수")
e = run(c)
add(T_ONE, "잔치국수 만드는 데 총 몇 분 걸려?", [c], f"차례로 하면 {e['total_minutes']}분이고 그중 사람이 붙어 있는 시간은 {e['active_minutes']}분이다.",
    "총 시간을 안내한다", ["조리 시간"], docs=[recipe_id("잔치국수")])
c = call("plan_parallel_steps", recipe="볼로네제 스파게티")
p = run(c)
add(T_ONE, "볼로네제 스파게티는 동시에 할 수 있는 단계를 겹치면 몇 분이야?", [c],
    f"겹치면 {p['parallel_minutes']}분, 차례로 하면 {p['sequential_minutes']}분이다(약 {p['saved_minutes']}분 절약).",
    "병렬 계획 시간을 안내한다", ["조리 시간"], docs=[recipe_id("볼로네제 스파게티")])

# ───────────────────────── 에이전트 2~3명 20 ─────────────────────────
c1 = call("match_recipe_to_pantry", recipe="김치찌개", servings=4)
c2 = call("build_shopping_list", recipes=["김치찌개"], servings=4)
m, s = run(c1), run(c2)
add(T_MID, "김치찌개를 4인분 하려는데 우리 집에 모자란 재료가 뭐고 사려면 얼마야?", [c1, c2],
    f"모자라거나 없는 재료: " + ", ".join(i["name"] for i in s["items"]) + f". 장보기 합계 {won(s['total_price'])}.",
    "부족 재료와 구매 금액을 안내한다", ["냉장고 재고", "가격"], docs=[recipe_id("김치찌개")])
c1 = call("get_recipe", recipe="마파두부")
c2 = call("check_allergens", recipe="마파두부", allergies=["대두"])
a = run(c2)
add(T_MID, "마파두부 레시피 알려주고 대두 알레르기 있는 사람이 먹어도 되는지 봐줘.", [c1, c2],
    "마파두부는 대두 분류 재료를 포함한다: " + ", ".join(x["ingredient"] for x in a["conflicts"]) + ". 알레르기 분류 대조 결과이며 의료 판단이 아니다.",
    "레시피와 알레르기 충돌을 안내한다", ["레시피 조회", "알레르기"], docs=[recipe_id("마파두부")])
c1 = call("diet_rule_check", recipe="까르보나라", rule="저칼로리")
c2 = call("estimate_total_time", recipe="까르보나라")
d, e = run(c1), run(c2)
add(T_MID, "까르보나라가 저칼로리 기준에 맞는지, 그리고 총 몇 분 걸리는지 알려줘.", [c1, c2],
    f"까르보나라 1인분 열량 {d['per_serving']}kcal로 저칼로리 기준 {d['limit']:.0f}kcal {d['limit_kind']}을 " + ("만족한다" if d["pass"] else "만족하지 않는다") + f". 차례로 하면 총 {e['total_minutes']}분이다.",
    "식이 판정과 소요 시간을 안내한다", ["식이", "조리 시간"], docs=[recipe_id("까르보나라")])
c1 = call("expiring_soon", within_days=1)
c2 = call("find_substitute", query="시금치가 없거나 모자랄 때 대체 재료", top_k=3)
add(T_MID, "내일까지 상하는 재료를 알려주고, 그중 시금치 대신 쓸 수 있는 건 뭐야?", [c1, c2],
    "내일까지 임박·지난 재고: " + ", ".join(f"{p['name']}({p['days_left']}일)" for p in run(c1)) + ". 시금치는 브로콜리로 대체할 수 있다(1g당 1.0g, 더 단단해 데치는 시간을 늘린다).",
    "임박 재고와 시금치 대체를 안내한다", ["유통기한", "대체 재료"], docs=[sub_id("시금치", "브로콜리")])
c1 = call("filter_recipes", tag="간편", max_total_minutes=15, only_owned_equipment=True)
c2 = call("estimate_total_time", recipe="참치마요덮밥")
add(T_MID, "15분 안에 되는 간편 요리 중에서, 참치마요덮밥은 정확히 몇 분 걸려?", [c1, c2],
    f"조건에 맞는 간편 레시피 {len(run(c1))}개. 참치마요덮밥은 차례로 하면 {run(c2)['total_minutes']}분이다.",
    "간편 요리와 소요 시간을 안내한다", ["레시피 필터", "조리 시간"], docs=[recipe_id("참치마요덮밥")])
c1 = call("match_recipe_to_pantry", recipe="계란말이", servings=4)
c2 = call("estimate_total_time", recipe="계란말이")
add(T_MID, "계란말이를 4인분 하면 재료가 충분한지, 시간은 얼마나 걸리는지 알려줘.", [c1, c2],
    f"충분한 재료 비율 {run(c1)['coverage']:.0%}, 부족 {len(run(c1)['short'])}개. 총 {run(c2)['total_minutes']}분 걸린다.",
    "재고 충족 여부와 소요 시간을 안내한다", ["냉장고 재고", "조리 시간"], docs=[recipe_id("계란말이")])
c1 = call("price_of", ingredient="연어", amount=200)
c2 = call("storage_tip", query="연어 냉동 보관", top_k=3)
add(T_MID, "연어 200g은 얼마고, 사 오면 어떻게 보관해?", [c1, c2],
    f"연어 200g은 {won(run(c1)['price'])}이다. 연어는 랩으로 밀착해 싸 냉동하면 30일 보관하고 냉장 해동한다.",
    "연어 가격과 보관법을 안내한다", ["가격", "보관"], docs=[note_id("연어", "냉동")])
c1 = call("storage_tip", query="닭가슴살 냉동 보관", top_k=3)
c2 = call("nutrition_of", recipe="닭가슴살 샐러드")
add(T_MID, "닭가슴살 냉동 보관은 어떻게 해? 그리고 닭가슴살 샐러드 1인분 단백질은?", [c1, c2],
    f"닭가슴살은 1회분씩 나눠 랩으로 싸서 얼려 60일 보관하고 해동 후 다시 얼리지 않는다. 닭가슴살 샐러드 1인분 단백질은 {run(c2)['per_serving']['protein_g']}g이다.",
    "닭가슴살 보관법과 샐러드 영양을 안내한다", ["보관", "영양"], docs=[note_id("닭가슴살", "냉동"), recipe_id("닭가슴살 샐러드")])
c1 = call("search_recipes", query="아이가 좋아하는 간단한 아침 식사", top_k=5)
c2 = call("check_allergens", recipe="프렌치토스트", allergies=["우유"])
breakfast = [r["name"] for r in store.recipes().values()
             if {"간편", "아이"} <= set(r["tags"]) and {i["name"] for i in r["ingredients"]} & {"식빵", "달걀"}]
add(T_MID, "아이가 좋아할 만한 간단한 아침 요리를 찾아주고, 프렌치토스트에 우유 알레르기 재료가 있는지 알려줘.", [c1, c2],
    "간편·아이 태그이고 식빵이나 달걀을 쓰는 레시피: " + ", ".join(breakfast) + ". 프렌치토스트의 우유 분류 재료: "
    + ", ".join(x["ingredient"] for x in run(c2)["conflicts"]) + ".",
    "아침 요리 후보와 우유 충돌을 안내한다", ["레시피 추천", "알레르기"],
    docs=sorted({recipe_id(n) for n in breakfast} | {recipe_id("프렌치토스트")}))
c1 = call("get_recipe", recipe="오븐 치킨 구이")
c2 = call("estimate_total_time", recipe="오븐 치킨 구이")
add(T_MID, "오븐 치킨 구이 레시피 알려주고 우리 집 장비로 만들 수 있는지 봐줘.", [c1, c2],
    f"우리 집에 없는 장비: {', '.join(run(c2)['missing_equipment'])}. 그래서 이 장비로는 만들 수 없다.",
    "장비 부족으로 못 만든다고 알린다", ["레시피 조회", "조리 시간"], docs=[recipe_id("오븐 치킨 구이")])
c1 = call("build_shopping_list", recipes=["까르보나라"], servings=2)
c2 = call("plan_parallel_steps", recipe="까르보나라")
add(T_MID, "까르보나라 2인분 장보기 목록을 만들어주고, 단계를 겹쳐서 하면 몇 분 걸리는지도 알려줘.", [c1, c2],
    f"사야 할 재료: " + ", ".join(i["name"] for i in run(c1)["items"]) + f". 합계 {won(run(c1)['total_price'])}. 겹쳐서 하면 {run(c2)['parallel_minutes']}분이다.",
    "장보기 목록과 병렬 조리 시간을 안내한다", ["가격", "조리 시간"], docs=[recipe_id("까르보나라")])
c1 = call("expiring_soon", within_days=0)
c2 = call("search_recipes", query="방울토마토를 쓰는 요리", top_k=5)
add(T_MID, "오늘 상하는 재료가 뭐고, 그걸로 할 만한 요리가 있어?", [c1, c2],
    "오늘까지 임박·지난 재고: " + ", ".join(f"{p['name']}({p['days_left']}일)" for p in run(c1)) + ". 방울토마토를 쓰는 요리를 추천한다.",
    "임박 재고를 알리고 활용 요리를 추천한다", ["유통기한", "레시피 추천"],
    docs=[r["id"] for r in store.recipes().values() if "방울토마토" in {i["name"] for i in r["ingredients"]}])
c1 = call("find_substitute", query="버터 대신 쓸 수 있는 재료", top_k=3)
c2 = call("price_of", ingredient="올리브유", amount=100)
add(T_MID, "버터가 없으면 뭘 쓸 수 있어? 올리브유로 대신하려는데 100ml는 얼마야?", [c1, c2],
    f"버터 대신 식용유(0.8배) 또는 올리브유(0.8배)를 볶음용으로만 쓸 수 있다. 올리브유 100ml는 {won(run(c2)['price'])}이다.",
    "버터 대체와 올리브유 가격을 안내한다", ["대체 재료", "가격"], docs=[sub_id("버터", "식용유"), sub_id("버터", "올리브유")])
c1 = call("check_allergens", recipe="땅콩버터 바나나 토스트")
c2 = call("find_substitute", query="땅콩버터 대신 쓸 수 있는 재료", top_k=3)
add(T_MID, "우리 집 가족 알레르기 기준으로 땅콩버터 바나나 토스트 괜찮아? 안 되면 땅콩버터 대신 쓸 걸 알려줘.", [c1, c2],
    "가족 중 땅콩 알레르기가 있어 땅콩버터가 충돌한다. 땅콩버터를 참깨로 바꿀 수 있지만(0.6배) 알레르기 분류가 참깨로 바뀐다.",
    "알레르기 충돌과 대체 재료를 안내한다", ["알레르기", "대체 재료"], docs=[recipe_id("땅콩버터 바나나 토스트"), sub_id("땅콩버터", "참깨")])
c1 = call("nutrition_of", recipe="김치볶음밥", servings=4)
c2 = call("match_recipe_to_pantry", recipe="김치볶음밥", servings=4)
add(T_MID, "김치볶음밥 4인분의 총 열량이랑, 지금 재료로 4인분이 되는지 알려줘.", [c1, c2],
    f"김치볶음밥 4인분 총 열량 {run(c1)['total']['kcal']}kcal. 충분한 재료 비율 {run(c2)['coverage']:.0%}.",
    "4인분 열량과 재고 충족을 안내한다", ["영양", "냉장고 재고"], docs=[recipe_id("김치볶음밥")])
c1 = call("plan_parallel_steps", recipe="잔치국수")
c2 = call("build_shopping_list", recipes=["잔치국수"], servings=4)
add(T_MID, "잔치국수 4인분을 겹쳐서 하면 몇 분이고, 장은 뭘 봐야 해?", [c1, c2],
    f"겹치면 {run(c1)['parallel_minutes']}분. 사야 할 재료: " + ", ".join(i["name"] for i in run(c2)["items"]) + f"(합계 {won(run(c2)['total_price'])}).",
    "병렬 시간과 장보기를 안내한다", ["조리 시간", "가격"], docs=[recipe_id("잔치국수")])
c1 = call("storage_tip", query="두부 개봉 후 보관", top_k=3)
c2 = call("diet_rule_check", recipe="두부 스테이크", rule="고단백")
add(T_MID, "두부는 개봉하면 어떻게 보관하고, 두부 스테이크는 고단백 기준에 맞아?", [c1, c2],
    f"두부는 개봉 후 물에 담가 밀폐하고 매일 물을 갈아 주며 2일 안에 먹는다. 두부 스테이크 1인분 단백질 {run(c2)['per_serving']}g으로 기준 {run(c2)['limit']:.0f}g {run(c2)['limit_kind']}을 " + ("만족한다." if run(c2)["pass"] else "만족하지 않는다."),
    "두부 보관과 고단백 판정을 안내한다", ["보관", "식이"], docs=[note_id("두부", "개봉 후 냉장"), recipe_id("두부 스테이크")])
c1 = call("filter_recipes", tag="국물", max_total_minutes=30, only_owned_equipment=True)
c2 = call("check_allergens", recipe="순두부찌개", allergies=["대두", "계란"])
add(T_MID, "30분 안에 되는 국물 요리를 보여주고, 순두부찌개에 대두나 계란 재료가 있는지도 알려줘.", [c1, c2],
    f"조건에 맞는 국물 레시피 {len(run(c1))}개. 순두부찌개의 충돌: " + "; ".join(f"{x['ingredient']}({','.join(x['allergens'])})" for x in run(c2)["conflicts"]) + ".",
    "국물 요리 목록과 알레르기 충돌을 안내한다", ["레시피 필터", "알레르기"], docs=[recipe_id("순두부찌개")])
c1 = call("price_of", ingredient="달걀", amount=10)
c2 = call("storage_tip", query="달걀 냉장 보관", top_k=3)
add(T_MID, "달걀 10개 가격이랑 달걀 보관법 알려줘.", [c1, c2],
    f"달걀 10개는 {won(run(c1)['price'])}이다. 달걀은 씻지 말고 뾰족한 쪽을 아래로 두어 냉장 21일 보관한다.",
    "달걀 가격과 보관법을 안내한다", ["가격", "보관"], docs=[note_id("달걀", "냉장")])

c1 = call("get_recipe", recipe="감자 수프")
c2 = call("storage_tip", query="우유 개봉 후 보관", top_k=3)
add(T_MID, "감자 수프 재료 알려주고, 수프에 쓰는 우유는 개봉 후 어떻게 보관해?", [c1, c2],
    "감자 수프 재료: " + ", ".join(f"{i['name']} {i['amount']}{i['unit']}" for i in run(c1)["ingredients"])
    + ". 우유는 개봉 후 냉장하고 3일 안에 먹으며 입을 닦아 닫아 둔다.",
    "수프 재료와 우유 보관법을 안내한다", ["레시피 조회", "보관"], docs=[recipe_id("감자 수프"), note_id("우유", "개봉 후 냉장")])

# ───────────────────────── 에이전트 4명 이상 15 ─────────────────────────
c = [call("filter_recipes", tag="국물", max_total_minutes=40, only_owned_equipment=True),
     call("match_recipe_to_pantry", recipe="김치찌개", servings=4),
     call("check_allergens", recipe="김치찌개", allergies=["땅콩"]),
     call("build_shopping_list", recipes=["김치찌개"], servings=4),
     call("estimate_total_time", recipe="김치찌개")]
add(T_MANY, "금요일 저녁 4인 가족, 아이 하나가 땅콩 알레르기, 냉장고 재료 위주로, 40분 안에, 예산 2만 원 안으로 국물 요리 추천해 줘. 김치찌개로 확인해 봐.", c,
    f"김치찌개 4인분: 땅콩 충돌 {'없음' if run(c[2])['safe'] else '있음'}, 부족 재료 " + ", ".join(i["name"] for i in run(c[3])["items"])
    + f"(합계 {won(run(c[3])['total_price'])}, 2만 원 " + ("안" if run(c[3])['total_price'] <= 20000 else "초과") + f"), 총 {run(c[4])['total_minutes']}분.",
    "조건을 모두 확인해 김치찌개 가능 여부를 답한다", ["레시피 추천", "냉장고 재고", "알레르기", "가격", "조리 시간"], docs=[recipe_id("김치찌개")])

def many4(question, name, servings, budget, minutes, extra_tool=None, topics_extra=()):
    """4명 이상 유형: 레시피 하나를 recipe / pantry / nutrition / shopping / cooking 에이전트가 함께 점검한다.
    extra_tool이 있으면 도구 호출을 한 건 더 한다. 기준 답은 도구 실행 결과에서 계산한다."""
    cs = [call("get_recipe", recipe=name),
          call("match_recipe_to_pantry", recipe=name, servings=servings),
          call("check_allergens", recipe=name),
          call("build_shopping_list", recipes=[name], servings=servings)]
    sl = run(cs[3])
    cs.append(call("budget_check", total_price=sl["total_price"], budget=budget))
    cs.append(call("plan_parallel_steps", recipe=name))
    if extra_tool:
        cs.append(extra_tool)
    m, al, bd, pl = run(cs[1]), run(cs[2]), run(cs[4]), run(cs[5])
    eq = run(call("estimate_total_time", recipe=name))
    parts = [f"{name} {servings}인분"]
    parts.append("가족 알레르기 충돌 " + ("없음" if al["safe"] else ", ".join(f"{x['ingredient']}({','.join(x['allergens'])})" for x in al["conflicts"])))
    if m["expired"]:
        parts.append("유통기한이 지난 재고 " + ", ".join(x["name"] for x in m["expired"]))
    parts.append("사야 할 재료 " + (", ".join(i["name"] for i in sl["items"]) or "없음") + f"(합계 {won(sl['total_price'])}, 예산 {won(budget)} " + ("안" if bd["within_budget"] else "초과") + ")")
    parts.append(f"겹쳐서 하면 {pl['parallel_minutes']}분으로 {minutes}분 " + ("안" if pl["parallel_minutes"] <= minutes else "을 넘음"))
    if eq["missing_equipment"]:
        parts.append("우리 집에 없는 장비 " + ", ".join(eq["missing_equipment"]))
    topics = ["레시피 조회", "냉장고 재고", "알레르기", "가격", "예산", "조리 시간"] + list(topics_extra)
    add(T_MANY, question, cs, ". ".join(parts) + ".", f"{name}의 알레르기·재고·예산·시간 조건을 종합해 가능 여부를 답한다", topics,
        docs=[recipe_id(name)])


# 알레르기 충돌, 장비 없음, 유통기한 지난 재고, 예산 초과가 실제로 걸리는 시나리오를 섞는다.
many4("이번 금요일 저녁에 아이들까지 네 식구가 먹을 땅콩소스 비빔국수를 해 보려고 해. 우리 집 알레르기 기준으로 괜찮은지, 집에 있는 걸로 얼마나 되는지, 장을 보면 2만 원 안인지, 25분 안에 끝나는지 봐줘.",
      "땅콩소스 비빔국수", 4, 20000, 25)
many4("오븐 치킨 구이를 네 명이서 먹고 싶은데, 우리 집 장비로 가능한지부터 알려주고 알레르기, 재료 상태, 3만 원 예산, 50분 제한까지 같이 확인해 줘.",
      "오븐 치킨 구이", 4, 30000, 50)
many4("요거트 과일볼을 가족 모두 먹을 건데 냉장고에 있는 요거트가 괜찮은지 포함해서 재료를 점검해 줘. 알레르기, 장보기 금액(7천 원 이내), 10분 안에 되는지도.",
      "요거트 과일볼", 4, 7000, 10)
many4("땅콩버터 바나나 토스트를 우리 네 식구 간식으로 만들면 어때? 알레르기 문제 없는지, 재료는 충분한지, 5천 원 안인지, 얼마나 걸리는지 알려줘.",
      "땅콩버터 바나나 토스트", 4, 5000, 15)
many4("네 명이 먹을 제육볶음인데 고기가 모자라면 사야 하잖아. 사야 할 양과 금액이 2만 원을 넘는지, 알레르기는 없는지, 40분 안에 가능한지 알려줘.",
      "제육볶음", 4, 20000, 40)
many4("카레라이스 4인분을 오늘 저녁에 하려는데, 1만 원 예산에 맞는지가 제일 궁금해. 시간은 60분까지 괜찮고 알레르기와 재고도 같이 봐줘.",
      "카레라이스", 4, 10000, 60)
many4("밥이 모자란 것 같은데 김치볶음밥을 네 명분 할 수 있을까? 밥과 김치 재고, 알레르기, 1만 5천 원 예산, 30분 제한을 확인해 줘.",
      "김치볶음밥", 4, 15000, 30)
many4("퇴근하고 20분 안에 네 식구 저녁을 끝내야 해서 참치마요덮밥을 생각 중이야. 알레르기와 재고, 8천 원 예산이랑 정말 20분 안에 되는지 알려줘.",
      "참치마요덮밥", 4, 8000, 20)
many4("멸치 견과 볶음을 반찬으로 네 명분 만들어 보고 싶어. 땅콩이 들어가니 우리 집 알레르기와 맞는지 먼저 보고, 재고와 5천 원 예산, 20분 제한도 봐줘.",
      "멸치 견과 볶음", 4, 5000, 20)
many4("애호박전을 네 식구 저녁 반찬으로 하려고 하는데 애호박이 곧 상할 것 같아. 재고가 충분한지, 알레르기, 장보기 금액(1만 원 이내), 40분 안에 되는지 확인해 줘.",
      "애호박전", 4, 10000, 40)
many4("순두부찌개 4인분 해 먹으려는데 재고에 순두부가 없는 것 같아. 사야 할 목록과 합계, 알레르기, 시간(30분)까지 한 번에 정리해 줘.",
      "순두부찌개", 4, 15000, 30)
many4("4인 가족 저녁으로 까르보나라 어때? 베이컨과 달걀이 우리 집에 있는지, 알레르기, 5천 원 이내 예산, 40분 제한을 확인해 줘.",
      "까르보나라", 4, 5000, 40)

many4("닭볶음탕을 네 명이 먹으려는데 25분밖에 없어. 그 시간 안에 되는지, 알레르기와 재고, 6천 원 예산도 같이 확인해 줘.",
      "닭볶음탕", 4, 6000, 25)

c = [call("expiring_soon", within_days=3), call("search_recipes", query="애호박 시금치 두부 같은 곧 상하는 재료를 쓰는 요리", top_k=5),
     call("check_allergens", recipe="두부조림"), call("build_shopping_list", recipes=["두부조림"], servings=4),
     call("estimate_total_time", recipe="두부조림")]
add(T_MANY, "3일 안에 상하는 재료로 4인 가족 저녁을 해결하고 싶어. 두부조림이 가능한지 알레르기, 사야 할 재료, 시간까지 봐줘.", c,
    "3일 이내 임박 재고 " + str(len(run(c[0]))) + "종. 두부조림: 알레르기 충돌 " + ("없음" if run(c[2])["safe"] else "있음")
    + ", 사야 할 재료 " + (", ".join(i["name"] for i in run(c[3])["items"]) or "없음") + f"(합계 {won(run(c[3])['total_price'])}), 총 {run(c[4])['total_minutes']}분.",
    "임박 재고 활용 요리의 가능 여부를 종합해 답한다", ["유통기한", "레시피 추천", "알레르기", "가격", "조리 시간"],
    docs=sorted({r["id"] for r in store.recipes().values() if {i["name"] for i in r["ingredients"]} & {"애호박", "시금치", "두부"}}))

# ───────────────────────── 범위 밖 10 ─────────────────────────
for q in ["오늘 서울 날씨 어때?", "파이썬으로 리스트 정렬하는 방법 알려줘.", "삼성전자 주가 알려줘.",
          "어제 프리미어리그 경기 결과가 어떻게 됐어?", "제주도 3박 4일 여행 일정 짜줘.", "감기에 걸렸는데 어떤 약을 먹어야 해?",
          "전월세 계약할 때 주의할 점이 뭐야?", "영어로 자기소개 문장 써줘.", "내일 로또 번호 추천해줘.",
          "우리 집 강아지가 아픈 것 같은데 어떻게 해야 해?"]:
    add(T_OUT, q, [], OUT_REF, "범위 밖임을 알린다(도구 호출 없음)", [])


def validate():
    types = {}
    for q in QUESTIONS:
        types[q["type"]] = types.get(q["type"], 0) + 1
        for c in q["reference_tool_calls"]:
            if c["name"] not in TOOLS_BY_NAME:
                raise ValueError(f"{q['id']}: 없는 도구 {c['name']}")
            if c["name"] in SEARCH_TOOLS:
                if not q["reference_docs"]:
                    raise ValueError(f"{q['id']}: 검색 도구 질문에는 reference_docs가 있어야 함")
                continue
            result = run(c)
            if isinstance(result, dict) and "error" in result:
                raise ValueError(f"{q['id']}: 도구가 오류를 돌려줌 {c} → {result}")
        agents = {TOOL_OWNER[c["name"]] for c in q["reference_tool_calls"]}
        n = len(agents)
        want = {T_ONE: n == 1, T_MID: 2 <= n <= 3, T_MANY: n >= 4, T_OUT: n == 0}[q["type"]]
        if not want:
            raise ValueError(f"{q['id']}: 유형 {q['type']}과 에이전트 수 {n} 불일치 ({sorted(agents)})")
        for d in q["reference_docs"]:
            if not any(d in s for s in (store.recipes(), {x["id"] for x in store.substitutes()}, {x["id"] for x in store.storage_notes()})):
                raise ValueError(f"{q['id']}: 없는 근거 문서 {d}")
    want = {T_ONE: 15, T_MID: 20, T_MANY: 15, T_OUT: 10}
    if types != want or len(QUESTIONS) != 60:
        raise ValueError(f"유형별 개수가 목표와 다름: {types}")
    return types


def main():
    types = validate()
    Path("data").mkdir(exist_ok=True)
    Path("data/questions.json").write_text(json.dumps(QUESTIONS, ensure_ascii=False, indent=2), encoding="utf-8")
    with open("data/questions.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "유형", "질문", "기대 에이전트", "기대 도구 호출", "근거 문서 ID", "기준 답", "기대 결과", "허용 주제"])
        for q in QUESTIONS:
            calls = " / ".join(f"{c['name']}({json.dumps(c['args'], ensure_ascii=False)})" for c in q["reference_tool_calls"])
            w.writerow([q["id"], q["type"], q["question"], ",".join(q["expected_agents"]), calls,
                        ",".join(q["reference_docs"]), q["reference"], q["reference_outcome"], ",".join(q["reference_topics"])])
    print("질문", len(QUESTIONS), "개 저장: data/questions.json, data/questions.csv  유형별:", types)


if __name__ == "__main__":
    main()
