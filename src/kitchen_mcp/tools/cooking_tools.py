"""cooking 에이전트의 도구: estimate_total_time, plan_parallel_steps.

단계는 두 종류다. active=사람이 붙어서 하는 단계, 대기=불·시간이 일하는 단계(끓이기, 재우기 등).
parallel=True인 단계는 앞의 대기 단계가 도는 동안 겹쳐 할 수 있다 (표시는 recipes.py의 PARALLEL, 검증되지 않은 값).
이 병렬 계획은 단순 모델이다: 사람은 한 명이라 active 단계끼리는 겹치지 못하고, 대기 단계는 사람 없이 진행된다.
"""

from kitchen_mcp.tools import store


def estimate_total_time(recipe: str) -> dict:
    """레시피를 단계 순서대로 차례로 했을 때(병렬 없음) 총 시간과, 사람이 붙어 있어야 하는 시간을 계산한다.
    필요한 장비 중 우리 집에 없는 것도 알려 준다."""
    r = store.recipe_by_name_or_id(recipe)
    if r is None:
        return {"error": f"레시피를 찾을 수 없음: {recipe}"}
    total = sum(s["minutes"] for s in r["steps"])
    active = sum(s["minutes"] for s in r["steps"] if s["active"])
    missing = sorted(set(r["equipment"]) - set(store.household()["equipment"]))
    return {"recipe": r["name"], "total_minutes": total, "active_minutes": active,
            "waiting_minutes": total - active, "missing_equipment": missing,
            "can_cook_with_owned_equipment": not missing}


def plan_parallel_steps(recipe: str) -> dict:
    """대기 단계가 도는 동안 겹쳐 할 수 있는 단계를 겹쳐서 계획하고, 걸리는 시간(parallel_minutes)을 계산한다.
    각 단계의 시작·종료 분(start, end)을 돌려준다."""
    r = store.recipe_by_name_or_id(recipe)
    if r is None:
        return {"error": f"레시피를 찾을 수 없음: {recipe}"}
    schedule = []
    person_free = 0   # 사람이 다음 active 단계를 시작할 수 있는 시각
    prev_end = 0      # 직전 단계의 종료 시각
    for k, s in enumerate(r["steps"], start=1):
        if s["parallel"]:
            ready = person_free          # 앞 단계(대기)가 끝나길 기다리지 않는다
        else:
            ready = prev_end             # 앞 단계가 끝나야 시작한다
        start = max(ready, person_free) if s["active"] else ready
        end = start + s["minutes"]
        if s["active"]:
            person_free = end
        schedule.append({"step": k, "desc": s["desc"], "start": start, "end": end,
                         "active": s["active"], "overlapped": s["parallel"]})
        prev_end = end if not s["parallel"] else max(prev_end, end)
    parallel_minutes = max(x["end"] for x in schedule)
    sequential = sum(s["minutes"] for s in r["steps"])
    return {"recipe": r["name"], "sequential_minutes": sequential, "parallel_minutes": parallel_minutes,
            "saved_minutes": sequential - parallel_minutes, "schedule": schedule}
