import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.models.connection import (
    CreateConnectionRequest,
    DatabaseConnection,
    DatabaseConnectionResponse,
    UpdateConnectionRequest,
)
from app.services.connection_manager import (
    connection_manager,
)
from app.services.schema_service import schema_service
from app.services.schema_document_service import (
    schema_document_service,
)
from app.services.rag_service import rag_service
from app.services.query_service import query_service
from app.services.agent_service import agent_service
from app.services.mcp_client_service import (
    mcp_client_service,
)

from app.models.integration import (
    CreateIntegrationConnection,
    IntegrationConnection,
    IntegrationStatus,
    NotionPageRequest,
)

from app.services.integration_manager import IntegrationManager
from app.services.notion_oauth_service import NotionOAuthService
from app.services.integration_secret_manager import IntegrationSecretManager
from app.integrations.notion import NotionProvider

from app.services.notion_knowledge_service import (
    notion_knowledge_service,
)

logger = logging.getLogger("datamcp.backend")

app = FastAPI(title="DataMCP Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Temporary user identity.
# This will later be replaced by authenticated
# user information from JWT/session authentication.
CURRENT_USER_ID = "demo-user"

def get_current_user_id() -> str:
    return CURRENT_USER_ID


NOTION_OAUTH_STATES: dict[str, dict] = {}

NOTION_OAUTH_STATE_TTL = 600


integration_manager = IntegrationManager()
integration_secret_manager = IntegrationSecretManager()
notion_oauth_service = NotionOAuthService()
notion_provider = NotionProvider()


def internal_server_error() -> HTTPException:
    return HTTPException(
        status_code=500,
        detail="Internal server error",
    )


def get_owned_connection(
    connection_id: str,
    user_id: str | None = None,
) -> DatabaseConnection:
    
    if user_id is None:
        user_id = get_current_user_id()

    connection = connection_manager.get(
        connection_id,
        user_id,
    )

    if connection is None:
        raise HTTPException(
            status_code=404,
            detail="Connection not found",
        )

    return connection


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "backend",
    }


@app.get("/rag/health")
def rag_health():
    return rag_service.health_check()


@app.post(
    "/connections",
    response_model=DatabaseConnection,
)
def create_connection(
    request: CreateConnectionRequest,
    user_id: str = Depends(get_current_user_id),
):

    connection = DatabaseConnection(
        id=str(uuid4()),
        user_id=user_id,
        name=request.name,
        database_type=request.database_type,
        connection_string=request.connection_string,
    )

    adapter = None

    try:
        adapter = connection_manager.get_adapter(
            connection
        )

        success = adapter.test_connection()

        if success:
            connection.status = "connected"
        else:
            connection.status = "disconnected"

        return connection_manager.add(connection)

    except ValueError:
        connection.status = "error"
        return connection_manager.add(connection)

    except Exception:
        connection.status = "error"

        logger.exception(
            "Unexpected backend error while testing connection"
        )

        return connection_manager.add(connection)

    finally:
        if adapter is not None:
            adapter.close()


@app.get(
    "/connections",
    response_model=list[DatabaseConnectionResponse],
)
def list_connections(
    user_id: str = Depends(get_current_user_id),
):

    return connection_manager.get_all(
        user_id
    )


@app.get(
    "/connections/{connection_id}",
    response_model=DatabaseConnectionResponse,
)
def get_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user_id)
):

    return get_owned_connection(
        connection_id,
        user_id,
    )


@app.delete(
    "/connections/{connection_id}"
)
def delete_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
):

    deleted = connection_manager.delete(
        connection_id,
        user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Connection not found",
        )

    return {
        "success": True,
        "message": "Connection deleted",
    }


@app.put(
    "/connections/{connection_id}"
)
def update_connection(
    connection_id: str,
    request: UpdateConnectionRequest,
    user_id: str = Depends(get_current_user_id),
):
    existing = connection_manager.get(
        connection_id,
        user_id,
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="Connection not found",
        )

    connection_string = (
        request.connection_string.strip()
        if request.connection_string.strip()
        else existing.connection_string
    )

    updated = DatabaseConnection(
        id=connection_id,
        user_id=user_id,
        name=request.name,
        database_type=request.database_type,
        connection_string=connection_string,
        status="unknown",
    )

    adapter = None

    try:
        adapter = connection_manager.get_adapter(
            updated
        )

        success = adapter.test_connection()

        if success:
            updated.status = "connected"
        else:
            updated.status = "disconnected"

        return connection_manager.update(
            updated,
            user_id,
        )

    except ValueError:
        updated.status = "error"

        return connection_manager.update(
            updated,
            user_id,
        )

    except Exception:
        updated.status = "error"

        logger.exception(
            "Unexpected backend error while updating connection"
        )

        return connection_manager.update(
            updated,
            user_id,
        )

    finally:
        if adapter is not None:
            adapter.close()


@app.post(
    "/connections/{connection_id}/test"
)
def test_connection(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
):

    connection = get_owned_connection(
        connection_id,
        user_id,
    )

    adapter = None

    try:
        adapter = connection_manager.get_adapter(
            connection
        )

        success = adapter.test_connection()

        if success:
            connection.status = "connected"
        else:
            connection.status = "disconnected"

        connection_manager.update(
            connection,
            user_id,
        )

        return {
            "connection_id": connection_id,
            "success": success,
            "status": connection.status,
        }

    except ValueError as error:

        connection.status = "error"

        connection_manager.update(
            connection,
            user_id,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:

        connection.status = "error"

        connection_manager.update(
            connection,
            user_id,
        )

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()

    finally:

        if adapter is not None:
            adapter.close()


@app.get(
    "/connections/{connection_id}/schema"
)
def get_connection_schema(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
):

    get_owned_connection(
        connection_id,
        user_id,
    )

    try:

        schema = schema_service.get_schema(
            connection_id
        )

        return {
            "connection_id": connection_id,
            "schema": schema,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception:

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()


@app.get(
    "/connections/{connection_id}/sample/{table_name}"
)
def get_sample_data(
    connection_id: str,
    table_name: str,
    limit: int = 5,
    user_id: str = Depends(get_current_user_id),
):

    connection = get_owned_connection(
        connection_id,
        user_id,
    )

    adapter = None

    try:

        adapter = connection_manager.get_adapter(
            connection
        )

        data = adapter.get_sample_data(
            table_name,
            limit,
        )

        return {
            "connection_id": connection_id,
            "table": table_name,
            "data": data,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()

    finally:

        if adapter is not None:
            adapter.close()


@app.get(
    "/connections/{connection_id}/schema/documents"
)
def get_schema_documents(
    connection_id: str,
):

    get_owned_connection(
        connection_id
    )

    try:

        schema = schema_service.get_schema(
            connection_id
        )

        documents = (
            schema_document_service.create_documents(
                schema,
                connection_id,
            )
        )

        return {
            "connection_id": connection_id,
            "documents": documents,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception:

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()


@app.post(
    "/connections/{connection_id}/schema/ingest"
)
def ingest_schema(
    connection_id: str,
):

    get_owned_connection(
        connection_id
    )

    try:

        schema = schema_service.get_schema(
            connection_id
        )

        documents = (
            schema_document_service.create_documents(
                schema=schema,
                connection_id=connection_id,
            )
        )

        result = (
            schema_document_service.ingest_documents(
                documents
            )
        )

        return {
            "connection_id": connection_id,
            "documents": len(documents),
            "rag": result,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception:

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()


@app.post("/rag/search")
def search_rag(
    request: dict,
    user_id: str = Depends(get_current_user_id),
):

    query = request.get("query")
    k = request.get("k", 4)
    connection_id = request.get("connection_id")
    source_type = request.get("source_type")

    if not query:
        raise HTTPException(
            status_code=400,
            detail="query is required",
        )

    if connection_id:
        get_owned_connection(
            connection_id,
            user_id,
        )

    return rag_service.search(
        query=query,
        k=k,
        connection_id=connection_id,
        user_id=user_id,
        source_type=source_type,
    )


@app.post(
    "/connections/{connection_id}/query"
)
def execute_read_query(
    connection_id: str,
    request: dict,
    user_id: str = Depends(get_current_user_id),
):

    query = request.get("query")

    if not query:
        raise HTTPException(
            status_code=400,
            detail="query is required",
        )

    connection = get_owned_connection(
        connection_id,
        user_id,
    )

    adapter = None

    try:

        query_service.validate_read_query(
            query
        )

        adapter = connection_manager.get_adapter(
            connection
        )

        data = adapter.execute_read_query(
            query
        )

        return {
            "connection_id": connection_id,
            "query": query,
            "data": data,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()

    finally:

        if adapter is not None:
            adapter.close()


@app.post(
    "/connections/{connection_id}/mongodb/query"
)
def execute_mongodb_query(
    connection_id: str,
    request: dict,
    user_id: str = Depends(get_current_user_id),
):

    collection_name = request.get(
        "collection_name"
    )

    filter_query = (
        request.get("filter_query")
        or {}
    )

    projection = request.get(
        "projection"
    )

    limit = request.get(
        "limit",
        100,
    )

    if not collection_name:
        raise HTTPException(
            status_code=400,
            detail="collection_name is required",
        )

    connection = get_owned_connection(
        connection_id,
        user_id,
    )

    if (
        connection.database_type.value
        != "mongodb"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Connection is not a "
                "MongoDB database"
            ),
        )

    adapter = None

    try:

        adapter = connection_manager.get_adapter(
            connection
        )

        data = (
            adapter.execute_mongodb_query(
                collection_name=collection_name,
                filter_query=filter_query,
                projection=projection,
                limit=limit,
            )
        )

        return {
            "connection_id": connection_id,
            "collection_name": collection_name,
            "data": data,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()

    finally:

        if adapter is not None:
            adapter.close()


@app.post(
    "/integrations",
    response_model=IntegrationConnection,
)
def create_integration(
    request: CreateIntegrationConnection,
    user_id: str = Depends(get_current_user_id),
):
    return integration_manager.create(
        request,
        user_id,
    )


@app.get(
    "/integrations",
    response_model=list[IntegrationConnection],
)
def list_integrations(
    user_id: str = Depends(get_current_user_id),
):
    return integration_manager.get_all(
        user_id,
    )

@app.get("/integrations/notion/authorize")
def authorize_notion(
    user_id: str = Depends(get_current_user_id),
):
    state = uuid4().hex

    NOTION_OAUTH_STATES[state] = {
        "user_id": user_id,
        "created_at": time.time(),
    }

    authorization_url = (
        notion_oauth_service.get_authorization_url(
            state
        )
    )

    return {
        "authorization_url": authorization_url,
    }


@app.get("/integrations/notion/callback")
async def notion_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
):
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Notion authorization failed: {error}",
        )

    if not state:
        raise HTTPException(
            status_code=400,
            detail="Missing OAuth state",
        )

    oauth_state = NOTION_OAUTH_STATES.pop(state, None)

    if not oauth_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state",
        )

    if time.time() - oauth_state["created_at"] > NOTION_OAUTH_STATE_TTL:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state",
        )

    if oauth_state["user_id"] != user_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Missing authorization code",
        )

    integration = None

    integrations = integration_manager.get_all(
        user_id
    )

    for item in integrations:
        if item.provider.value == "notion":
            integration = item
            break

    if not integration:
        raise HTTPException(
            status_code=404,
            detail="Notion integration not found",
        )

    try:
        token_data = await notion_oauth_service.exchange_code(
            code
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    integration_secret_manager.save(
        integration.id,
        token_data,
    )

    integration = integration_manager.update(
        integration_id=integration.id,
        user_id=user_id,
        status=IntegrationStatus.CONNECTED,
        external_account_id=token_data.get("workspace_id"),
    )

    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Notion Connected</title>
        </head>
        <body>
            <script>
                if (window.opener) {
                    window.opener.postMessage(
                        {
                            type: "NOTION_OAUTH_SUCCESS"
                        },
                        "http://localhost:3000"
                    );
                }

                window.close();
            </script>

            <p>Notion connected successfully. You can close this window.</p>
        </body>
        </html>
        """
    )


@app.get("/integrations/notion/search")
async def search_notion(
    query: str = "",
    user_id: str = Depends(get_current_user_id),
):
    return await notion_provider.search(
        query,
        user_id,
    )


@app.get("/integrations/notion/pages/{page_id}")
async def get_notion_page(
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    return await notion_provider.get(
        page_id,
        user_id,
    )


@app.post("/integrations/notion/pages")
async def create_notion_page(
    request: NotionPageRequest,
    user_id: str = Depends(get_current_user_id),
):
    page = await notion_provider.create(
        request.title,
        request.content,
        user_id,
    )

    ingestion = await notion_knowledge_service.ingest_page(
        page["id"],
        user_id,
    )

    return {
        "page": page,
        "rag": ingestion["rag"],
    }


@app.put("/integrations/notion/pages/{page_id}")
async def update_notion_page(
    page_id: str,
    request: NotionPageRequest,
    user_id: str = Depends(get_current_user_id),
):
    page = await notion_provider.update(
        page_id,
        request.title,
        request.content,
        user_id,
    )

    ingestion = await notion_knowledge_service.ingest_page(
        page_id,
        user_id,
    )

    return {
        "page": page,
        "rag": ingestion["rag"],
    }


@app.post("/integrations/notion/pages/{page_id}/ingest")
async def ingest_notion_page(
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    return await notion_knowledge_service.ingest_page(
        page_id,
        user_id,
    )


@app.post("/integrations/notion/disconnect")
async def disconnect_notion(
    user_id: str = Depends(get_current_user_id),
):
    integrations = integration_manager.get_all(
        user_id
    )

    notion_integration = next(
        (
            integration
            for integration in integrations
            if integration.provider.value == "notion"
        ),
        None,
    )

    if notion_integration is None:
        raise HTTPException(
            status_code=404,
            detail="Notion is not connected",
        )

    integration_secret_manager.delete(
        notion_integration.id
    )

    integration = integration_manager.disconnect(
        notion_integration.id,
        user_id,
    )

    return {
        "status": "disconnected",
        "integration": integration,
    }


@app.get("/integrations/notion/status")
async def notion_status(
    user_id: str = Depends(get_current_user_id),
):
    integrations = integration_manager.get_all(
        user_id
    )

    notion_integration = next(
        (
            integration
            for integration in integrations
            if integration.provider.value == "notion"
        ),
        None,
    )

    if notion_integration is None:
        return {
            "connected": False,
        }

    return {
        "connected": (
            notion_integration.status.value
            == "connected"
        ),
        "integration": notion_integration,
    }


@app.post("/agent")
async def process_agent_question(
    request: dict,
    user_id: str = Depends(get_current_user_id),
):
    question = request.get(
        "question"
    )

    connection_id = request.get(
        "connection_id"
    )

    messages = request.get(
        "messages",
        [],
    )

    if not question:
        raise HTTPException(
            status_code=400,
            detail="question is required",
        )

    if connection_id:
        get_owned_connection(
            connection_id,
            user_id,
        )

    try:

        return await agent_service.process(
            question,
            user_id,
            connection_id,
            messages,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.get("/agent/tools")
async def get_agent_tools():

    try:

        tools = (
            await mcp_client_service.list_tools()
        )

        return {
            "tools": tools,
        }

    except Exception:

        logger.exception(
            "Unexpected backend error"
        )

        raise internal_server_error()
