from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


class StoredDocument(BaseModel):
    document_id: str
    filename: str
    chunk_count: int = Field(ge=0)
    uploaded_at: str


class DocumentUploadResponse(BaseModel):
    document: StoredDocument


class DocumentListResponse(BaseModel):
    documents: list[StoredDocument]


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    filename: str
    chunk_index: int
    snippet: str
    content: str
    distance: float | None = None


def serialize_chunk(chunk: RetrievedChunk) -> dict[str, object]:
    return {
        "document_id": chunk.document_id,
        "filename": chunk.filename,
        "chunk_index": chunk.chunk_index,
        "snippet": chunk.snippet,
        "content": chunk.content,
        "distance": chunk.distance,
    }
