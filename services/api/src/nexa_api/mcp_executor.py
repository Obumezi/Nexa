"""Execute planned Nexa MCP tool calls over Streamable HTTP."""

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from nexa_api.mcp_orchestrator import MCPToolCall

DEFAULT_MCP_URL = "http://127.0.0.1:8000/mcp"


async def execute_mcp_tool_call(
    tool_call: MCPToolCall,
    url: str = DEFAULT_MCP_URL,
) -> object:
    """Execute a planned MCP tool call and return structured content."""

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            await session.initialize()

            result = await session.call_tool(
                tool_call.tool_name,
                tool_call.arguments,
            )

            if result.structured_content is not None:
                return result.structured_content

            return {
                "content": [
                    getattr(item, "text", str(item))
                    for item in result.content
                ]
            }