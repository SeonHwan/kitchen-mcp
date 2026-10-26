"""서버 하나를 stdio로 띄워 도구 목록과 호출 한 건을 확인한다 (모델 호출 없음).
실행: uv run python scripts/probe_server.py recipe get_recipe '{"recipe": "계란말이"}'"""
import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def main(agent, tool_name, arguments):
    params = StdioServerParameters(command="uv", args=["run", "python", "-m", f"kitchen_mcp.servers.{agent}"])
    async with Client(params) as client:
        listed = await client.list_tools()
        print("도구:", [t.name for t in listed.tools])
        result = await client.call_tool(tool_name, arguments)
        print("isError:", result.is_error if hasattr(result, "is_error") else getattr(result, "isError", "?"))
        print("structured:", json.dumps(result.structured_content if hasattr(result, "structured_content") else None, ensure_ascii=False)[:300])
        print("content:", [c.text[:200] for c in result.content if hasattr(c, "text")])


asyncio.run(main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3])))
