import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = (
    "https://ne-cc084a3067bf4a9bbe7c0a4bc5e5ffee."
    "ecs.us-east-1.on.aws/mcp/"
)


async def main() -> None:
    print(f"Connecting to: {MCP_URL}")

    async with streamable_http_client(MCP_URL) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            result = await session.initialize()

            print("\nMCP initialization successful")
            print(f"Server: {result.server_info.name}")
            print(f"Version: {result.server_info.version}")

            tools = await session.list_tools()

            print(f"\nTools available: {len(tools.tools)}")

            for tool in tools.tools:
                print(f" - {tool.name}")

            print("\n" + "=" * 60)
            print("TEST 1: NEXA STATUS")
            print("=" * 60)

            status_result = await session.call_tool(
                "nexa_status",
                {},
            )

            print(status_result)

            print("\n" + "=" * 60)
            print("TEST 2: HOUSEHOLD PRESENCE")
            print("=" * 60)

            presence_result = await session.call_tool(
                "get_household_presence",
                {},
            )

            print(presence_result)

            print("\n" + "=" * 60)
            print("TEST 3: CREATE HOUSEHOLD TASK")
            print("=" * 60)

            create_task_result = await session.call_tool(
                "create_task",
                {
                    "title": "Hackathon MCP verification task",
                    "description": (
                        "Created through the public Nexa MCP endpoint."
                    ),
                    "confirm": True,
                },
            )

            print(create_task_result)

            print("\n" + "=" * 60)
            print("TEST 4: GET OPEN TASKS")
            print("=" * 60)

            open_tasks_result = await session.call_tool(
                "get_open_tasks",
                {},
            )

            print(open_tasks_result)

            print("\n" + "=" * 60)
            print("PUBLIC MCP TEST COMPLETE")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())