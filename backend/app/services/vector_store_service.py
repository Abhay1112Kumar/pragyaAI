import math
import re
from collections import Counter
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    HYBRID_CANDIDATE_MULTIPLIER,
    HYBRID_RRF_K,
)
from app.shared.config import settings


class VectorStoreService:
    def __init__(self) -> None:
        if settings.embedding_provider.lower() == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is required for Gemini embeddings.")
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.embedding_model,
                google_api_key=settings.gemini_api_key,
            )
        else:
            self.embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

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
        owner_id: str | None = None,
    ) -> list[dict]:
        filters = []
        if document_id:
            filters.append({"document_id": document_id})
        if owner_id:
            filters.append({"owner_id": owner_id})

        if len(filters) > 1:
            search_filter = {"$and": filters}
        elif filters:
            search_filter = filters[0]
        else:
            search_filter = None

        candidate_count = max(limit, limit * HYBRID_CANDIDATE_MULTIPLIER)
        semantic_results = self.vector_store.similarity_search_with_score(
            query=query,
            k=candidate_count,
            filter=search_filter,
        )

        semantic_chunks = [
            {
                "content": document.page_content,
                "metadata": document.metadata,
                "semantic_distance": float(score),
            }
            for document, score in semantic_results
        ]

        stored = self.vector_store._collection.get(
            where=search_filter,
            include=["documents", "metadatas"],
        )
        lexical_chunks = self._bm25_search(
            query=query,
            ids=stored.get("ids", []),
            documents=stored.get("documents", []),
            metadatas=stored.get("metadatas", []),
            limit=candidate_count,
        )

        return self._reciprocal_rank_fusion(
            semantic_chunks=semantic_chunks,
            lexical_chunks=lexical_chunks,
            limit=limit,
        )

    def _bm25_search(
        self,
        query: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        limit: int,
    ) -> list[dict]:
        query_terms = self._tokenize(query)
        if not query_terms or not documents:
            return []

        tokenized_documents = [self._tokenize(document) for document in documents]
        average_length = sum(map(len, tokenized_documents)) / len(tokenized_documents)
        document_frequencies = Counter()
        for terms in tokenized_documents:
            document_frequencies.update(set(terms))

        scored_chunks = []
        document_count = len(documents)
        k1 = 1.5
        b = 0.75

        for chunk_id, content, metadata, terms in zip(
            ids, documents, metadatas, tokenized_documents
        ):
            frequencies = Counter(terms)
            score = 0.0
            for term in query_terms:
                frequency = frequencies[term]
                if not frequency:
                    continue
                document_frequency = document_frequencies[term]
                inverse_document_frequency = math.log(
                    1 + (document_count - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                length_normalization = 1 - b
                if average_length:
                    length_normalization += b * len(terms) / average_length
                score += inverse_document_frequency * (
                    frequency * (k1 + 1)
                    / (frequency + k1 * length_normalization)
                )

            if score > 0:
                chunk_metadata = dict(metadata or {})
                chunk_metadata.setdefault("chunk_id", chunk_id)
                scored_chunks.append(
                    {
                        "content": content,
                        "metadata": chunk_metadata,
                        "bm25_score": score,
                    }
                )

        return sorted(
            scored_chunks,
            key=lambda chunk: chunk["bm25_score"],
            reverse=True,
        )[:limit]

    def _reciprocal_rank_fusion(
        self,
        semantic_chunks: list[dict],
        lexical_chunks: list[dict],
        limit: int,
    ) -> list[dict]:
        fused: dict[str, dict] = {}

        for method, chunks in (
            ("semantic", semantic_chunks),
            ("bm25", lexical_chunks),
        ):
            for rank, chunk in enumerate(chunks, start=1):
                chunk_id = self._chunk_key(chunk)
                entry = fused.setdefault(
                    chunk_id,
                    {
                        "content": chunk["content"],
                        "metadata": chunk["metadata"],
                        "score": 0.0,
                        "retrieval_methods": [],
                    },
                )
                entry["score"] += 1 / (HYBRID_RRF_K + rank)
                entry["retrieval_methods"].append(method)

        return sorted(
            fused.values(),
            key=lambda chunk: chunk["score"],
            reverse=True,
        )[:limit]

    def _chunk_key(self, chunk: dict) -> str:
        metadata = chunk["metadata"]
        return str(
            metadata.get("chunk_id")
            or f"{metadata.get('document_id')}:{metadata.get('chunk_index')}"
        )

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def stats(self) -> dict[str, int]:
        stored = self.vector_store._collection.get(
            include=["metadatas"],
        )
        metadatas = stored.get("metadatas", [])
        document_ids = {
            metadata.get("document_id")
            for metadata in metadatas
            if metadata and metadata.get("document_id")
        }
        return {
            "chunks": len(stored.get("ids", [])),
            "documents": len(document_ids),
        }

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
