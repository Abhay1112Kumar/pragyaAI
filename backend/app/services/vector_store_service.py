from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
)


class VectorStoreService:
    def __init__(self) -> None:
        self.embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        self.vector_store = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=str(CHROMA_DIR),
        )

    def index_documents(
        self,
        documents: list[Document],
    ) -> int:
        chunks = self.text_splitter.split_documents(documents)

        if not chunks:
            return 0

        chunk_ids: list[str] = []

        for chunk_index, chunk in enumerate(chunks):
            chunk_id = str(uuid4())

            chunk.metadata["chunk_id"] = chunk_id
            chunk.metadata["chunk_index"] = chunk_index

            chunk_ids.append(chunk_id)

        self.vector_store.add_documents(
            documents=chunks,
            ids=chunk_ids,
        )

        return len(chunks)

    def search(
        self,
        query: str,
        limit: int = 4,
        document_id: str | None = None,
    ) -> list[dict]:
        search_filter = None

        if document_id:
            search_filter = {
                "document_id": document_id,
            }

        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=limit,
            filter=search_filter,
        )

        return [
            {
                "content": document.page_content,
                "metadata": document.metadata,
                "score": float(score),
            }
            for document, score in results
        ]

    def delete_document(self, document_id: str) -> int:
        collection = self.vector_store._collection

        existing = collection.get(
            where={
                "document_id": document_id,
            }
        )

        ids = existing.get("ids", [])

        if not ids:
            return 0

        self.vector_store.delete(ids=ids)

        return len(ids)


vector_store_service = VectorStoreService()