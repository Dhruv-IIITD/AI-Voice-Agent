from __future__ import annotations

import logging
import os
from functools import lru_cache

from app.rag.schemas import RetrievedChunk, serialize_chunk
from app.rag.vector_store import RagVectorStore, get_vector_store

logger = logging.getLogger(__name__)


class DocumentRetriever:
    def __init__(self, *, vector_store: RagVectorStore | None = None) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._top_k = max(1, int(os.getenv("RAG_TOP_K", "4")))
        self._max_distance = float(os.getenv("RAG_MAX_DISTANCE", "1.2"))

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        logger.info("[RAG] Retrieval query=%s", normalized_query)
        try:
            chunks = self._vector_store.query(query_text=normalized_query, limit=self._top_k)
        except Exception:
            logger.exception("[RAG] Retrieval failed, continuing without document context.")
            return []

        filtered = [
            chunk
            for chunk in chunks
            if chunk.distance is None or chunk.distance <= self._max_distance
        ]
        filenames = sorted({chunk.filename for chunk in filtered})
        logger.info(
            "[RAG] Retrieval result chunks=%s filenames=%s",
            len(filtered),
            filenames,
        )
        return filtered


@lru_cache(maxsize=1)
def get_document_retriever() -> DocumentRetriever:
    return DocumentRetriever()


def retrieve_serialized_chunks(query: str) -> list[dict[str, object]]:
    return [serialize_chunk(chunk) for chunk in get_document_retriever().retrieve(query)]
