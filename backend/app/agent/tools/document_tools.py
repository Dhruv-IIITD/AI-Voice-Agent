from __future__ import annotations

import logging

from app.rag.retriever import retrieve_serialized_chunks

logger = logging.getLogger(__name__)


def search_uploaded_docs(query: str) -> dict[str, object]:
    try:
        chunks = retrieve_serialized_chunks(query)
    except Exception:
        logger.exception("[ToolCall] search_uploaded_docs failed query=%s", query)
        return {
            "query": query,
            "chunk_count": 0,
            "filenames": [],
            "chunks": [],
            "summary": "I could not access uploaded documents right now.",
        }

    filenames = sorted({str(chunk.get("filename") or "") for chunk in chunks if chunk.get("filename")})

    if not chunks:
        summary = "No relevant content was found in uploaded documents."
    else:
        summary = f"Found {len(chunks)} relevant document chunks from {', '.join(filenames) or 'uploaded documents'}."

    return {
        "query": query,
        "chunk_count": len(chunks),
        "filenames": filenames,
        "chunks": chunks,
        "summary": summary,
    }
