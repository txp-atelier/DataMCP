from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class MCPClientService:

    MCP_URL = "http://mcp-server:8001/mcp"

    async def list_tools(self) -> list[dict]:
        async with streamablehttp_client(
            self.MCP_URL,
            headers={
                "Host": "localhost:8001"
            },
        ) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:

                await session.initialize()

                result = await session.list_tools()

                return [
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.inputSchema,
                    }
                    for tool in result.tools
                ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
        user_id: str,
    ):
        arguments = {
            **arguments,
            "user_id": user_id,
        }

        async with streamablehttp_client(
            self.MCP_URL,
            headers={
                "Host": "localhost:8001"
            },
        ) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:

                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

                return result


mcp_client_service = MCPClientService()