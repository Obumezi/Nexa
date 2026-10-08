"""Simple Nexa MCP client smoke test."""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def print_tool_result(
    session: ClientSession,
    tool_name: str,
    arguments: dict[str, object] | None = None,
) -> object:
    """Call an MCP tool and print its structured result."""

    result = await session.call_tool(
        tool_name,
        arguments or {},
    )

    print(f"\n{tool_name} result:")
    print(result.structured_content)

    return result.structured_content


async def main() -> None:
    """Test Nexa read tools and safe task actions over MCP."""

    url = "http://127.0.0.1:8000/mcp"

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("Available tools:")

            for tool in tools.tools:
                print(f"- {tool.name}")

            await print_tool_result(
                session,
                "nexa_status",
            )

            await print_tool_result(
                session,
                "get_open_tasks",
            )

            print("\n--- CREATE TASK: FIRST CALL ---")

            await print_tool_result(
                session,
                "create_task",
                {
                    "title": "MCP integration smoke test",
                    "description": (
                        "Verify safe task creation through Streamable HTTP."
                    ),
                    "confirm": False,
                },
            )

            print("\n--- TASKS AFTER UNCONFIRMED CREATE ---")

            await print_tool_result(
                session,
                "get_open_tasks",
            )

            print("\n--- CREATE TASK: CONFIRMED CALL ---")

            await print_tool_result(
                session,
                "create_task",
                {
                    "title": "MCP integration smoke test",
                    "description": (
                        "Verify safe task creation through Streamable HTTP."
                    ),
                    "confirm": True,
                },
            )

            print("\n--- TASKS AFTER CONFIRMED CREATE ---")

            await print_tool_result(
                session,
                "get_open_tasks",
            )

            print("\n--- COMPLETE TASK: FIRST CALL ---")

            await print_tool_result(
                session,
                "complete_task",
                {
                    "title": "MCP integration smoke test",
                    "confirm": False,
                },
            )

            print("\n--- TASKS AFTER UNCONFIRMED COMPLETION ---")

            await print_tool_result(
                session,
                "get_open_tasks",
            )

            print("\n--- COMPLETE TASK: CONFIRMED CALL ---")

            await print_tool_result(
                session,
                "complete_task",
                {
                    "title": "MCP integration smoke test",
                    "confirm": True,
                },
            )

            print("\n--- TASKS AFTER CONFIRMED COMPLETION ---")

            await print_tool_result(
                session,
                "get_open_tasks",
            )


if __name__ == "__main__":
    asyncio.run(main())