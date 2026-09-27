from langchain_chroma import Chroma

from app.embeddings import embedding_service


class VectorStoreService:

    def __init__(self):
        self.vector_store = Chroma(
            collection_name="datamcp_schema",
            embedding_function=(
                embedding_service.get_embeddings()
            ),
            persist_directory="/app/chroma_data",
        )

    def add_documents(
        self,
        documents: list[dict],
    ):
        texts = [
            document["content"]
            for document in documents
        ]

        metadatas = [
            {
                "user_id": document["user_id"],
                "source_type": document.get(
                    "source_type",
                    "database",
                ),
                "source_id": document.get(
                    "source_id"
                ),
                "title": document.get(
                    "title"
                ),
                "connection_id": document.get(
                    "connection_id"
                ),
                "table": document.get(
                    "table"
                ),
            }
            for document in documents
        ]

        return self.vector_store.add_texts(
            texts=texts,
            metadatas=metadatas,
        )

    def replace_documents(
        self,
        documents: list[dict],
    ):
        if not documents:
            return []

        user_ids = {
            document["user_id"]
            for document in documents
        }

        if len(user_ids) != 1:
            raise ValueError(
                "All documents must belong to "
                "the same user"
            )

        source_types = {
            document.get(
                "source_type",
                "database",
            )
            for document in documents
        }

        if len(source_types) != 1:
            raise ValueError(
                "All documents must have "
                "the same source_type"
            )

        source_type = next(
            iter(source_types)
        )

        if source_type == "database":
            connection_ids = {
                document.get("connection_id")
                for document in documents
            }

            if len(connection_ids) != 1:
                raise ValueError(
                    "All database documents must "
                    "belong to the same connection"
                )

            connection_id = next(
                iter(connection_ids)
            )

            self.vector_store.delete(
                where={
                    "connection_id": connection_id
                }
            )

        else:
            source_ids = {
                document.get("source_id")
                for document in documents
            }

            if len(source_ids) != 1:
                raise ValueError(
                    "All knowledge documents must "
                    "belong to the same source"
                )

            source_id = next(
                iter(source_ids)
            )

            self.vector_store.delete(
                where={
                    "$and": [
                        {
                            "user_id": next(
                                iter(user_ids)
                            )
                        },
                        {
                            "source_type": source_type
                        },
                        {
                            "source_id": source_id
                        },
                    ]
                }
            )

        return self.add_documents(
            documents
        )

    def search(
        self,
        query: str,
        k: int = 4,
        connection_id: str | None = None,
        user_id: str | None = None,
        source_type: str | None = None,
    ):
        filters = []

        if connection_id:
            filters.append(
                {
                    "connection_id": connection_id
                }
            )

        if user_id:
            filters.append(
                {
                    "user_id": user_id
                }
            )

        if source_type:
            filters.append(
                {
                    "source_type": source_type
                }
            )

        filter_metadata = None

        if len(filters) == 1:
            filter_metadata = filters[0]

        elif len(filters) > 1:
            filter_metadata = {
                "$and": filters
            }

        return self.vector_store.similarity_search(
            query,
            k=k,
            filter=filter_metadata,
        )


vector_store_service = VectorStoreService()