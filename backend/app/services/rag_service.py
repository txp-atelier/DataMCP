import requests


class RAGService:

    def __init__(self):
        self.base_url = "http://rag:8002"

    def health_check(self) -> dict:
        response = requests.get(
            f"{self.base_url}/health",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def ingest_documents(
        self,
        documents: list[dict],
    ) -> dict:
        response = requests.post(
            f"{self.base_url}/documents",
            json={
                "documents": documents,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def ingest_knowledge(
        self,
        documents: list[dict],
    ) -> dict:
        knowledge_documents = []

        for document in documents:
            knowledge_documents.append({
                "user_id": document["user_id"],
                "source_type": document.get(
                    "source_type",
                    "knowledge",
                ),
                "source_id": document.get(
                    "source_id"
                ),
                "title": document.get(
                    "title"
                ),
                "content": document["content"],
            })

        return self.ingest_documents(
            knowledge_documents
        )

    def search(
        self,
        query: str,
        k: int = 4,
        connection_id: str | None = None,
        user_id: str | None = None,
        source_type: str | None = None,
    ) -> dict:
        response = requests.post(
            f"{self.base_url}/search",
            json={
                "query": query,
                "k": k,
                "connection_id": connection_id,
                "user_id": user_id,
                "source_type": source_type,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


rag_service = RAGService()