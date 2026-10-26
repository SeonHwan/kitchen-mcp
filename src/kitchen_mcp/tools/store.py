"""데이터 로더. data/ 의 JSON을 한 번 읽어 메모리에 두고, 도구들이 읽기 전용으로 쓴다.

어떤 도구도 데이터 파일을 수정하지 않는다.
"""
import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def ingredients():
    """재료 이름 → 재료 사전 항목"""
    return {i["name"]: i for i in _load("ingredients.json")}


@lru_cache(maxsize=None)
def recipes():
    """레시피 id → 레시피"""
    return {r["id"]: r for r in _load("recipes.json")}


@lru_cache(maxsize=None)
def household():
    return _load("household.json")


@lru_cache(maxsize=None)
def substitutes():
    return _load("substitutes.json")


@lru_cache(maxsize=None)
def storage_notes():
    return _load("storage_notes.json")


def recipe_by_name_or_id(key):
    """'R001' 또는 '김치찌개' 어느 쪽이든 받는다. 없으면 None."""
    if key in recipes():
        return recipes()[key]
    for r in recipes().values():
        if r["name"] == key:
            return r
    return None


def grams_of(name, amount):
    """재료 분량(사전 단위)을 g으로 바꾼다. 개는 단위당 g, ml은 밀도를 곱한다."""
    return amount * ingredients()[name]["grams_per_unit"]
