from app.services.rag_service import rag_service


class KnowledgeDocumentService:

    def create_document(
        self,
        content: str,
        title: str,
        source_type: str,
        source_id: str,
        user_id: str,
    ) -> dict:

        return {
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "content": content,
        }

    def ingest_document(
        self,
        document: dict,
    ) -> dict:

        return rag_service.ingest_documents(
            [document]
        )


knowledge_document_service = KnowledgeDocumentService()