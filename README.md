# kitchen-mcp

[kitchen-agent](https://github.com/SeonHwan/kitchen-agent)(LangGraph 멀티 에이전트)가 쓰는 도구를 MCP 서버로 분리한 프로젝트.
에이전트 하나 = 도구 묶음 하나 = MCP 서버 하나. 전송은 stdio.

| 서버 | 도구 |
|---|---|
| `kitchen_mcp.servers.recipe` | search_recipes, get_recipe, filter_recipes |
| `kitchen_mcp.servers.pantry` | list_pantry, match_recipe_to_pantry, expiring_soon |
| `kitchen_mcp.servers.nutrition` | nutrition_of, check_allergens, diet_rule_check |
| `kitchen_mcp.servers.substitute` | find_substitute, storage_tip |
| `kitchen_mcp.servers.shopping` | price_of, build_shopping_list, budget_check |
| `kitchen_mcp.servers.cooking` | estimate_total_time, plan_parallel_steps |

데이터는 모두 학습용 가상 값이다 (`docs/data.md`). `data/`는 git에 넣지 않는다.

## 실행
```bash
uv run python -m kitchen_mcp.servers.recipe        # 서버 하나 (stdio, 보통은 클라이언트가 띄운다)
uv run python tests/test_tools.py                  # 도구 단위 시험 35건 (모델·임베딩 없음)
uv run python scripts/check_all_servers.py         # 6개 서버를 띄워 도구 목록 대조 (모델 호출 없음)
uv run python scripts/probe_server.py recipe get_recipe '{"recipe": "계란말이"}'   # 서버 하나에 도구 한 건 호출
```

## 데이터 다시 만들기
생성 스크립트(`scripts/`)는 **실행한 위치의 `data/`**에 쓴다. 프로젝트 루트에서 `uv run python scripts/ingredients.py`처럼 실행한다 (순서와 의존은 `docs/data.md`).
`ingredients.json`과 `household.json`은 다시 만들어 서버 데이터와 바이트 단위로 같음을 확인했다 (나머지 3개는 확인하지 않았다).
