from fastapi import FastAPI
from pydantic import BaseModel

from app.vector_store import vector_store_service


app = FastAPI(
    title="DataMCP RAG Service",
)


class Document(BaseModel):
    user_id: str
    content: str

    source_type: str = "database"
    source_id: str | None = None
    title: str | None = None

    connection_id: str | None = None
    table: str | None = None


class IngestRequest(BaseModel):
    documents: list[Document]


class SearchRequest(BaseModel):
    query: str
    k: int = 4
    connection_id: str | None = None
    user_id: str | None = None
    source_type: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "rag",
    }


@app.post("/documents")
def ingest_documents(
    request: IngestRequest,
):
    documents = [
        document.model_dump()
        for document in request.documents
    ]

    ids = vector_store_service.replace_documents(
        documents
    )

    return {
        "status": "success",
        "documents_replaced": len(ids),
    }


@app.post("/search")
def search_documents(
    request: SearchRequest,
):
    results = vector_store_service.search(
        query=request.query,
        k=request.k,
        connection_id=request.connection_id,
        user_id=request.user_id,
        source_type=request.source_type,
    )

    return {
        "query": request.query,
        "connection_id": request.connection_id,
        "user_id": request.user_id,
        "source_type": request.source_type,
        "results": [
            {
                "content": result.page_content,
                "metadata": result.metadata,
            }
            for result in results
        ],
    }