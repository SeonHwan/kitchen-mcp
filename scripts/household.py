"""우리 집 상태 생성 스크립트: 냉장고 재고, 보유 장비, 가족 구성, 주간 예산.

모든 값은 가상 값이다 (docs/data.md 참고). 난수를 쓰지 않으므로 항상 같은 결과가 나온다.
현재 날짜는 코드에 박지 않고 기준 날짜(--base-date)로 받는다. 기본값은 2026-10-23(금요일 저녁 질문용).

실행: uv run python scripts/household.py [--base-date 2026-10-23]
결과: data/household.json (프로그램용), data/pantry.csv (사람이 보는 용)
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

from ingredients import ALLERGENS, build_ingredients
from recipes import EQUIPMENT, build_recipes

DEFAULT_BASE_DATE = "2026-10-23"

FAMILY = [
    {"role": "아빠", "age": 42, "allergies": []},
    {"role": "엄마", "age": 40, "allergies": []},
    {"role": "첫째", "age": 10, "allergies": ["땅콩"]},
    {"role": "둘째", "age": 6, "allergies": []},
]
EQUIPMENT_OWNED = ["가스레인지", "에어프라이어", "전자레인지", "믹서", "밥솥"]  # 오븐 없음
WEEKLY_BUDGET_WON = 150000
SPENT_THIS_WEEK_WON = 90000  # 기준 날짜까지 이번 주에 이미 쓴 금액 (남은 예산 = 예산 - 이 값)

# (재료, 수량, 유통기한). 수량 단위는 재료 사전의 단위(g, ml, 개)를 따른다.
PANTRY = [
    ("달걀", 6, "2026-11-02"), ("대파", 100, "2026-10-27"), ("양파", 3, "2026-11-10"),
    ("감자", 4, "2026-11-15"), ("당근", 2, "2026-10-30"), ("애호박", 1, "2026-10-26"),
    ("시금치", 150, "2026-10-24"), ("방울토마토", 200, "2026-10-23"), ("오이", 2, "2026-10-25"),
    ("사과", 2, "2026-11-05"), ("두부", 300, "2026-10-24"), ("배추김치", 500, "2026-12-01"),
    ("밥", 800, "2026-10-24"), ("돼지고기 목살", 400, "2026-10-24"), ("닭가슴살", 300, "2026-10-26"),
    ("햄", 150, "2026-11-05"), ("우유", 500, "2026-10-26"),
    ("플레인요거트", 200, "2026-10-20"),  # 기준 날짜에 이미 지난 재고
    ("모차렐라치즈", 200, "2026-10-30"), ("식빵", 6, "2026-10-25"), ("김", 20, "2027-03-01"),
    ("마늘", 80, "2026-11-10"), ("고추장", 300, "2027-01-15"), ("고춧가루", 100, "2027-02-01"),
    ("간장", 500, "2027-06-01"), ("식용유", 700, "2027-05-01"), ("참기름", 200, "2027-04-01"),
    ("소금", 500, "2028-01-01"), ("설탕", 400, "2028-01-01"), ("마요네즈", 200, "2027-01-10"),
    ("참치캔", 2, "2028-01-01"), ("스파게티면", 400, "2027-08-01"), ("토마토소스", 300, "2027-03-01"),
    ("땅콩버터", 250, "2027-02-01"),  # 땅콩 알레르기 가족이 있는 집의 함정 재고
]


def build_household(base_date):
    unit_of = {i.name: i.unit for i in build_ingredients()}
    pantry = []
    for name, amount, expires in PANTRY:
        if name not in unit_of:
            raise ValueError(f"재료 사전에 없는 재고: {name}")
        pantry.append({"name": name, "amount": amount, "unit": unit_of[name], "expires": expires})
    return {
        "base_date": base_date,
        "family": FAMILY,
        "equipment": EQUIPMENT_OWNED,
        "weekly_budget_won": WEEKLY_BUDGET_WON,
        "spent_this_week_won": SPENT_THIS_WEEK_WON,
        "pantry": pantry,
    }


def validate(h):
    date.fromisoformat(h["base_date"])
    names = [p["name"] for p in h["pantry"]]
    if len(set(names)) != len(names):
        raise ValueError("냉장고에 같은 재료가 두 줄")
    for p in h["pantry"]:
        date.fromisoformat(p["expires"])
        if p["amount"] <= 0:
            raise ValueError(f"{p['name']}: 수량은 양수여야 함")
    if set(h["equipment"]) - EQUIPMENT:
        raise ValueError("알 수 없는 장비")
    for m in h["family"]:
        if set(m["allergies"]) - ALLERGENS:
            raise ValueError(f"{m['role']}: 알 수 없는 알레르기 분류")
    if h["spent_this_week_won"] > h["weekly_budget_won"]:
        raise ValueError("이미 쓴 금액이 주간 예산보다 큼")


def days_left(p, base):
    return (date.fromisoformat(p["expires"]) - base).days


def write_csv(h, path):
    base = date.fromisoformat(h["base_date"])
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["재료", "수량", "단위", "유통기한", f"남은 일수 (기준 {h['base_date']})"])
        for p in h["pantry"]:
            w.writerow([p["name"], p["amount"], p["unit"], p["expires"], days_left(p, base)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-date", default=DEFAULT_BASE_DATE)
    args = parser.parse_args()

    h = build_household(args.base_date)
    validate(h)
    Path("data").mkdir(exist_ok=True)
    Path("data/household.json").write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(h, "data/pantry.csv")

    base = date.fromisoformat(h["base_date"])
    expired = [p["name"] for p in h["pantry"] if days_left(p, base) < 0]
    soon = [f"{p['name']}({days_left(p, base)}일)" for p in h["pantry"] if 0 <= days_left(p, base) <= 3]
    # 재고만으로 (수량 부족 없이, 지난 재고 제외) 만들 수 있는 레시피 수 — 데이터가 질문에 쓸 만한지 보는 점검
    stock = {p["name"]: p["amount"] for p in h["pantry"] if days_left(p, base) >= 0}
    makeable = []
    for r in build_recipes():
        if set(r["equipment"]) - set(h["equipment"]):
            continue
        if all(stock.get(i["name"], 0) >= i["amount"] for i in r["ingredients"]):
            makeable.append(r["name"])

    print("저장: data/household.json, data/pantry.csv  (기준 날짜", h["base_date"], ")")
    print("가족", len(h["family"]), "명, 알레르기:", [m["allergies"] for m in h["family"] if m["allergies"]])
    print("재고", len(h["pantry"]), "종 / 유통기한 지남:", expired, "/ 3일 이내:", soon)
    print("장비 없음:", sorted(EQUIPMENT - set(h["equipment"])), "/ 남은 예산:",
          h["weekly_budget_won"] - h["spent_this_week_won"], "원")
    print("재고만으로 지금 만들 수 있는 레시피", len(makeable), "개:", makeable)


if __name__ == "__main__":
    main()
