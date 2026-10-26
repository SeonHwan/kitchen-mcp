"""보관·위생 노트 40개 생성 스크립트.

모든 값은 가상 값이다 (docs/data.md 참고). 보관 기간과 주의점은 실제 식품 안전 기준이 아니며 근거가 없다.
각 노트의 `text`는 storage_tip 도구의 임베딩 검색 대상 문서가 된다.

실행: uv run python scripts/storage_notes.py
결과: data/storage_notes.json (프로그램용), data/storage_notes.csv (사람이 보는 용)
"""
import csv
import json
from pathlib import Path

from ingredients import build_ingredients

# (재료, 상황, 보관 기간(일), 주의점)
NOTES = [
    ("달걀", "냉장", 21, "씻지 말고 뾰족한 쪽을 아래로 두어 냉장고 안쪽에 둔다."),
    ("우유", "개봉 후 냉장", 3, "마시고 남은 것을 팩째 오래 두지 않고 입을 닦아 닫아 둔다."),
    ("두부", "개봉 후 냉장", 2, "물에 담가 밀폐하고 매일 물을 갈아 준다."),
    ("순두부", "개봉 후 냉장", 1, "물기가 많아 빨리 상하므로 당일 먹는 것이 좋다."),
    ("대파", "냉장", 7, "씻지 말고 키친타월로 싸서 세워 둔다. 썰어 두었다면 냉동한다."),
    ("양파", "실온", 30, "통풍이 되는 서늘한 곳에 두고 감자와 따로 보관한다."),
    ("감자", "실온", 30, "빛을 피해 보관한다. 싹과 푸른 부분은 도려내고 쓴다."),
    ("마늘", "실온", 30, "통마늘은 통풍되는 망에, 깐 마늘은 냉장 밀폐한다."),
    ("시금치", "냉장", 3, "씻지 않고 키친타월로 싸서 비닐에 담는다. 시들기 쉽다."),
    ("콩나물", "냉장", 3, "물에 담가 밀폐 용기에 두고 물을 갈아 준다."),
    ("애호박", "냉장", 7, "랩으로 싸서 채소 칸에 둔다. 썬 것은 2일 안에 쓴다."),
    ("토마토", "냉장", 7, "꼭지를 아래로 두고 겹치지 않게 놓는다."),
    ("닭가슴살", "냉장", 2, "다른 식재료와 닿지 않게 밀폐해 가장 아래 칸에 둔다."),
    ("닭가슴살", "냉동", 60, "1회분씩 나눠 랩으로 싸서 얼린다. 해동 후 다시 얼리지 않는다."),
    ("돼지고기 목살", "냉장", 3, "핏물이 새지 않게 용기에 담아 가장 아래 칸에 둔다."),
    ("돼지고기 목살", "냉동", 90, "1회분씩 소분해 납작하게 얼리면 빨리 해동된다."),
    ("소고기 불고기용", "냉장", 3, "양념하지 않은 상태로 밀폐해 둔다. 양념한 것은 1일 안에 조리한다."),
    ("고등어", "냉장", 1, "비린내가 퍼지므로 밀폐하고 당일 조리를 권한다."),
    ("연어", "냉동", 30, "랩으로 밀착해 싸고 냉장 해동한다."),
    ("새우", "냉동", 90, "얼음막을 입혀 얼리고 찬물이나 냉장고에서 해동한다."),
    ("오징어", "냉동", 60, "내장을 제거해 손질한 뒤 얼린다."),
    ("배추김치", "냉장", 90, "공기가 닿지 않게 눌러 담고 국물에 잠기게 둔다."),
    ("밥", "냉장", 2, "식은 뒤 밀폐한다. 데울 때는 충분히 뜨겁게 한다."),
    ("밥", "냉동", 30, "뜨거울 때 1회분씩 랩에 평평하게 싸서 얼린다."),
    ("햄", "개봉 후 냉장", 7, "랩으로 단면을 밀착해 싸 둔다."),
    ("베이컨", "개봉 후 냉장", 7, "소분해 밀폐한다. 오래 둘 것은 냉동한다."),
    ("어묵", "개봉 후 냉장", 5, "물기를 닦고 밀폐한다."),
    ("버터", "냉장", 60, "냄새가 배지 않게 포장지째 밀폐 용기에 둔다."),
    ("모차렐라치즈", "개봉 후 냉장", 7, "지퍼백의 공기를 빼고 밀봉한다."),
    ("플레인요거트", "개봉 후 냉장", 5, "깨끗한 숟가락을 쓰고 뚜껑을 바로 닫는다."),
    ("생크림", "개봉 후 냉장", 3, "냉장 온도에서 흔들리지 않게 안쪽에 둔다. 얼리면 분리된다."),
    ("식빵", "실온", 4, "밀봉해 서늘한 곳에 둔다. 오래 둘 것은 냉동한다."),
    ("식빵", "냉동", 30, "슬라이스째 소분해 얼리고 토스터나 에어프라이어로 바로 굽는다."),
    ("참치캔", "개봉 후 냉장", 2, "캔째 두지 말고 유리나 플라스틱 용기에 옮긴다."),
    ("고추장", "개봉 후 냉장", 180, "표면을 평평하게 하고 밀폐한다. 곰팡이가 보이면 해당 부분을 넉넉히 덜어낸다."),
    ("된장", "개봉 후 냉장", 365, "표면을 눌러 공기를 빼고 밀폐한다."),
    ("식용유", "개봉 후 실온", 90, "빛과 열을 피하고 뚜껑을 꼭 닫는다."),
    ("쌀", "실온", 60, "밀폐 용기에 담아 서늘한 곳에 둔다. 습기와 벌레를 피한다."),
    ("스파게티면", "삶은 후 냉장", 3, "올리브유를 살짝 버무려 밀폐한다. 붙기 쉽다."),
    ("바나나", "실온", 5, "꼭지를 랩으로 싸 두면 천천히 익는다. 냉장하면 껍질이 검게 변한다."),
]


def build_notes():
    names = {i.name for i in build_ingredients()}
    notes = []
    for n, (ingredient, situation, days, tip) in enumerate(NOTES, start=1):
        if ingredient not in names:
            raise ValueError(f"재료 사전에 없는 재료: {ingredient}")
        notes.append({
            "id": f"T{n:03d}", "ingredient": ingredient, "situation": situation, "days": days, "tip": tip,
            "text": f"{ingredient} {situation} 보관: {days}일. {tip}",
        })
    return notes


def validate(notes):
    if len(notes) != 40:
        raise ValueError(f"노트는 40개여야 함: {len(notes)}")
    keys = [(n["ingredient"], n["situation"]) for n in notes]
    if len(set(keys)) != len(keys):
        raise ValueError("같은 (재료, 상황) 노트가 두 번 있음")
    if any(n["days"] <= 0 for n in notes):
        raise ValueError("보관 기간은 양수여야 함")


def main():
    notes = build_notes()
    validate(notes)
    Path("data").mkdir(exist_ok=True)
    Path("data/storage_notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    with open("data/storage_notes.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "재료", "상황", "보관 기간(일)", "주의점"])
        for n in notes:
            w.writerow([n["id"], n["ingredient"], n["situation"], n["days"], n["tip"]])
    print("보관·위생 노트", len(notes), "개 저장: data/storage_notes.json, data/storage_notes.csv")
    print("재료 종류", len({n["ingredient"] for n in notes}), "개")


if __name__ == "__main__":
    main()
