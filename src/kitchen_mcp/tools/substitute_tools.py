"""substitute 에이전트의 도구: find_substitute, storage_tip. 둘 다 임베딩 검색이다."""

from kitchen_mcp.tools import store
from kitchen_mcp.tools.embedding import storage_index, substitute_index


def find_substitute(query: str, top_k: int = 3) -> list:
    """재료가 없을 때 쓸 대체 재료 규칙을 검색한다. 예: '달걀이 없을 때'. 규칙 문서(id, 원래/대체 재료, 비율, 차이)를 돌려준다."""
    by_id = {s["id"]: s for s in store.substitutes()}
    out = []
    for h in substitute_index().search(query, k=top_k):
        s = by_id[h["id"]]
        out.append({"id": s["id"], "from": s["from"], "to": s["to"], "ratio": s["ratio"],
                    "note": s["note"], "score": h["score"]})
    return out


def storage_tip(query: str, top_k: int = 3) -> list:
    """재료·상황별 보관 방법과 주의점을 검색한다. 예: '남은 밥 보관'. 노트(id, 재료, 상황, 기간, 주의점)를 돌려준다."""
    by_id = {n["id"]: n for n in store.storage_notes()}
    out = []
    for h in storage_index().search(query, k=top_k):
        n = by_id[h["id"]]
        out.append({"id": n["id"], "ingredient": n["ingredient"], "situation": n["situation"],
                    "days": n["days"], "tip": n["tip"], "score": h["score"]})
    return out
