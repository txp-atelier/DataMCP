import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


CONNECTION_ID = "ee221b86-aa0f-4d19-a35b-d21af17fa898"


async def main():
    async with streamablehttp_client(
        "http://mcp-server:8001/mcp",
        headers={
            "Host": "localhost:8001",
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

            tools = await session.list_tools()

            print("Available tools:")

            for tool in tools.tools:
                print(f"- {tool.name}")

            result = await session.call_tool(
                "execute_read_query",
                arguments={
                    "connection_id": "ee221b86-aa0f-4d19-a35b-d21af17fa898",
                    "query": "SELECT * FROM customers LIMIT 5",
                },
            )

            print("\nexecute_read_query result:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())