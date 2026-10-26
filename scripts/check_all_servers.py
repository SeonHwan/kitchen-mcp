"""6개 서버를 차례로 띄워 list_tools 결과가 TOOL_GROUPS와 같은지 대조한다 (모델 호출 없음)."""
import asyncio

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from kitchen_mcp.tools import TOOL_GROUPS


async def main():
    all_ok = True
    for agent, funcs in TOOL_GROUPS.items():
        params = StdioServerParameters(command="uv", args=["run", "python", "-m", f"kitchen_mcp.servers.{agent}"])
        async with Client(params) as client:
            names = [t.name for t in (await client.list_tools()).tools]
        expected = [f.__name__ for f in funcs]
        ok = names == expected
        all_ok = all_ok and ok
        print(("일치 " if ok else "불일치 ") + agent, names if ok else (names, expected))
    print("전부 일치" if all_ok else "불일치 있음")


asyncio.run(main())
