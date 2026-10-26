"""nutrition 에이전트의 MCP 서버. 도구 3개: nutrition_of, check_allergens, diet_rule_check.

실행: uv run python -m kitchen_mcp.servers.nutrition   (stdio. 보통은 클라이언트가 자식 프로세스로 띄운다)
"""
from mcp.server.mcpserver import MCPServer

from kitchen_mcp.tools import TOOL_GROUPS

AGENT = "nutrition"

server = MCPServer(AGENT)
for tool_function in TOOL_GROUPS[AGENT]:
    server.tool()(tool_function)  # 함수 이름이 도구 이름, 독스트링이 설명, 타입 힌트가 인자 스키마가 된다

if __name__ == "__main__":
    server.run()  # 기본이 stdio: 표준입력으로 요청을 받고 표준출력으로 응답한다
