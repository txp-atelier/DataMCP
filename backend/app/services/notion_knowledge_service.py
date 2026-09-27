from app.integrations.notion import notion_provider
from app.services.knowledge_document_service import (
    knowledge_document_service,
)


class NotionKnowledgeService:

    async def ingest_page(
        self,
        page_id: str,
        user_id: str,
    ) -> dict:

        page = await notion_provider.get(
            page_id,
            user_id,
        )

        document = (
            knowledge_document_service.create_document(
                content=page["content"],
                title=page["title"],
                source_type="notion",
                source_id=page["id"],
                user_id=user_id,
            )
        )

        result = (
            knowledge_document_service.ingest_document(
                document
            )
        )

        return {
            "status": "success",
            "page": page,
            "rag": result,
        }


notion_knowledge_service = NotionKnowledgeService()