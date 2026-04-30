from __future__ import annotations

import logging
from functools import lru_cache

from app.rag.schemas import RetrievedChunk, serialize_chunk
from app.rag.vector_store import RagVectorStore, get_vector_store

logger = logging.getLogger(__name__)


DEFAULT_TOP_K = 4
DEFAULT_MAX_DISTANCE = 1.2


class DocumentRetriever:
    def __init__(self, *, vector_store: RagVectorStore | None = None) -> None:
        """
        Retriever layer for RAG.
        """
        self._vector_store = vector_store or get_vector_store()
        self._top_k = DEFAULT_TOP_K
        self._max_distance = DEFAULT_MAX_DISTANCE

        logger.info(
            "[RAG] DocumentRetriever initialized top_k=%s max_distance=%s",
            self._top_k,
            self._max_distance,
        )

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        """
        Retrieve relevant document chunks for a user query.
        """
        normalized_query = query.strip()

        if not normalized_query:
            return []

        logger.info("[RAG] Retrieval query=%s", normalized_query)

        try:
            chunks = self._vector_store.query(
                query_text=normalized_query,
                limit=self._top_k,
            )
        except Exception:
            logger.exception("[RAG] Retrieval failed, continuing without document context.")
            return []

        filtered_chunks = self._keep_relevant_chunks(chunks)

        filenames = sorted({chunk.filename for chunk in filtered_chunks})

        logger.info(
            "[RAG] Retrieval result raw_chunks=%s filtered_chunks=%s filenames=%s",
            len(chunks),
            len(filtered_chunks),
            filenames,
        )

        return filtered_chunks

    def _keep_relevant_chunks(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """
        Remove weak retrieval results.
        """
        return [
            chunk
            for chunk in chunks
            if chunk.distance is None or chunk.distance <= self._max_distance
        ]


@lru_cache(maxsize=1)
def get_document_retriever() -> DocumentRetriever:
    return DocumentRetriever()


def retrieve_serialized_chunks(query: str) -> list[dict[str, object]]:
    return [
        serialize_chunk(chunk)
        for chunk in get_document_retriever().retrieve(query)
    ]


def get_rag_chunks(query: str) -> list[dict[str, object]]:
    return retrieve_serialized_chunks(query)
