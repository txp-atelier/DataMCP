import requests
import uvicorn

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("DataMCP")

BACKEND_URL = "http://backend:8000"


@mcp.tool()
def health_check() -> str:
    """Check whether the DataMCP MCP server is running."""
    return "DataMCP MCP server is healthy"


@mcp.tool()
def list_connections(
    user_id: str,
) -> list[dict]:
    """
    List databases currently connected to DataMCP
    for the current user.

    Connection credentials are never returned.
    """
    response = requests.get(
        f"{BACKEND_URL}/connections",
        params={
            "user_id": user_id,
        },
        timeout=10,
    )

    response.raise_for_status()

    connections = response.json()

    return [
        {
            "id": connection["id"],
            "name": connection["name"],
            "database_type": connection["database_type"],
            "status": connection["status"],
        }
        for connection in connections
    ]


@mcp.tool()
def get_database_schema(
    connection_id: str,
    user_id: str,
) -> dict:
    """
    Get the schema of a connected database
    belonging to the current user.
    """
    response = requests.get(
        f"{BACKEND_URL}/connections/{connection_id}/schema",
        params={
            "user_id": user_id,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def search_schema(
    query: str,
    connection_id: str,
    user_id: str,
    k: int = 4,
) -> dict:
    """
    Search database schema using RAG for a specific
    connection belonging to the current user.
    """
    response = requests.post(
        f"{BACKEND_URL}/rag/search",
        json={
            "query": query,
            "k": k,
            "connection_id": connection_id,
            "user_id": user_id,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def search_knowledge(
    query: str,
    user_id: str,
    k: int = 4,
) -> dict:
    """
    Search the user's saved knowledge and project documentation
    using semantic RAG retrieval.

    Use this tool when the user asks about:
    - their own projects
    - previous plans or decisions
    - saved architecture or documentation
    - notes or information previously stored in their knowledge base
    - information that should come from their connected knowledge sources

    Do not rely on general knowledge when the answer may exist
    in the user's saved knowledge.
    """

    response = requests.post(
        f"{BACKEND_URL}/rag/search",
        json={
            "query": query,
            "k": k,
            "user_id": user_id,
            "source_type": "notion",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def ingest_notion_page(
    page_id: str,
    user_id: str,
) -> dict:
    """
    Ingest a Notion page into the user's semantic knowledge base.

    Use this when a Notion page should become searchable
    through DataMCP's RAG knowledge system.
    """

    response = requests.post(
        f"{BACKEND_URL}/integrations/notion/pages/{page_id}/ingest",
        params={
            "user_id": user_id,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def notion_connection_status(
    user_id: str,
) -> dict:
    """
    Check whether Notion is currently connected
    for the current user.

    Use this before creating or updating Notion pages.
    """
    response = requests.get(
        f"{BACKEND_URL}/integrations/notion/status",
        params={
            "user_id": user_id,
        },
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    return {
        "connected": data.get("connected", False),
        "provider": "notion",
    }


@mcp.tool()
def search_notion(
    query: str,
    user_id: str,
) -> list[dict]:
    """
    Search the user's connected Notion workspace.
    """
    response = requests.get(
        f"{BACKEND_URL}/integrations/notion/search",
        params={
            "query": query,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def get_notion_page(
    page_id: str,
    user_id: str,
) -> dict:
    """
    Get a Notion page and its content.
    """
    response = requests.get(
        f"{BACKEND_URL}/integrations/notion/pages/{page_id}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def create_notion_page(
    title: str,
    content: str,
    user_id: str,
) -> dict:
    """
    Create a new page in the user's Notion workspace.
    """
    response = requests.post(
        f"{BACKEND_URL}/integrations/notion/pages",
        json={
            "title": title,
            "content": content,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def update_notion_page(
    page_id: str,
    title: str,
    content: str,
    user_id: str,
) -> dict:
    """
    Update an existing Notion page.
    """
    response = requests.put(
        f"{BACKEND_URL}/integrations/notion/pages/{page_id}",
        json={
            "title": title,
            "content": content,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def get_sample_data(
    connection_id: str,
    table_name: str,
    user_id: str,
    limit: int = 5,
) -> dict:
    """
    Get sample rows from a table in a connected database.
    """
    response = requests.get(
        f"{BACKEND_URL}/connections/{connection_id}/sample/{table_name}",
        params={
            "limit": limit,
            "user_id": user_id,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def describe_table(
    connection_id: str,
    table_name: str,
    user_id: str,
) -> dict:
    """
    Get the schema information for a specific table.
    """
    response = requests.get(
        f"{BACKEND_URL}/connections/{connection_id}/schema",
        params={
            "user_id": user_id,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    schema = data.get("schema", {})

    tables = schema.get("tables", {})

    if table_name not in tables:
        raise ValueError(
            f"Table '{table_name}' not found"
        )

    return {
        "connection_id": connection_id,
        "table": table_name,
        "schema": tables[table_name],
    }


@mcp.tool()
def execute_read_query(
    connection_id: str,
    query: str,
    user_id: str,
) -> dict:
    """
    Execute a read-only SQL query against a connected database.
    Only SELECT queries are allowed.
    """
    response = requests.post(
        f"{BACKEND_URL}/connections/{connection_id}/query",
        json={
            "query": query,
            "user_id": user_id,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def execute_mongodb_query(
    connection_id: str,
    collection_name: str,
    user_id: str,
    filter_query: dict | None = None,
    projection: dict | None = None,
    limit: int = 100,
) -> dict:
    """
    Execute a read-only query against a MongoDB collection.

    Supports filtering and projection.

    The limit must be between 1 and 100.
    Use the default limit of 100 unless a smaller limit is requested.
    """
    response = requests.post(
        f"{BACKEND_URL}/connections/{connection_id}/mongodb/query",
        json={
            "collection_name": collection_name,
            "filter_query": filter_query or {},
            "projection": projection,
            "limit": limit,
            "user_id": user_id,
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    app = mcp.streamable_http_app()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
    )