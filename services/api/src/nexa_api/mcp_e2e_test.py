"""Live end-to-end smoke tests for the Nexa MCP stack."""

import asyncio

from nexa_api.mcp_orchestrator import run_mcp_conversation_turn


async def main() -> None:
    """Run a small set of live conversational MCP checks."""

    print("\nNexa MCP end-to-end smoke test\n")

    presence = await run_mcp_conversation_turn(
        "Who is home?",
    )

    print("1. Presence result")
    print(presence)
    print()

    tasks = await run_mcp_conversation_turn(
        "What tasks are open?",
    )

    print("2. Open tasks result")
    print(tasks)
    print()

    confirmation = await run_mcp_conversation_turn(
        "Create a task called E2E verification task.",
        confirm=False,
    )

    print("3. Create task without confirmation")
    print(confirmation)
    print()

    confirmed = await run_mcp_conversation_turn(
        "Create a task called E2E verification task.",
        confirm=True,
    )

    print("4. Create task with confirmation")
    print(confirmed)
    print()

    tasks_after = await run_mcp_conversation_turn(
        "What tasks are open?",
    )

    print("5. Open tasks after creation")
    print(tasks_after)
    print()


if __name__ == "__main__":
    asyncio.run(main())