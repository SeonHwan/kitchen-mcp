"""16개 도구와 에이전트별 묶음.

에이전트 하나 = 도구 묶음 하나. 에이전트끼리 도구를 공유하지 않는다.
"""
from kitchen_mcp.tools.cooking_tools import estimate_total_time, plan_parallel_steps
from kitchen_mcp.tools.nutrition_tools import check_allergens, diet_rule_check, nutrition_of
from kitchen_mcp.tools.pantry_tools import expiring_soon, list_pantry, match_recipe_to_pantry
from kitchen_mcp.tools.recipe_tools import filter_recipes, get_recipe, search_recipes
from kitchen_mcp.tools.shopping_tools import budget_check, build_shopping_list, price_of
from kitchen_mcp.tools.substitute_tools import find_substitute, storage_tip

TOOL_GROUPS = {
    "recipe": [search_recipes, get_recipe, filter_recipes],
    "pantry": [list_pantry, match_recipe_to_pantry, expiring_soon],
    "nutrition": [nutrition_of, check_allergens, diet_rule_check],
    "substitute": [find_substitute, storage_tip],
    "shopping": [price_of, build_shopping_list, budget_check],
    "cooking": [estimate_total_time, plan_parallel_steps],
}
ALL_TOOLS = [t for group in TOOL_GROUPS.values() for t in group]
TOOL_OWNER = {t.__name__: agent for agent, group in TOOL_GROUPS.items() for t in group}
TOOLS_BY_NAME = {t.__name__: t for t in ALL_TOOLS}
