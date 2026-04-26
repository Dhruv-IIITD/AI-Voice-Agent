from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from app.rag.embeddings import get_embedding_function
from app.rag.schemas import RetrievedChunk, StoredDocument

logger = logging.getLogger(__name__)


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parents[2] / ".rag_store"


class RagVectorStore:
    def __init__(self) -> None:
        self._storage_dir = Path(os.getenv("RAG_STORAGE_DIR") or _default_storage_dir())
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        self._registry_path = self._storage_dir / "documents.json"
        self._registry = self._load_registry()

        collection_name = os.getenv("RAG_COLLECTION_NAME", "voice_documents")
        self._client = chromadb.PersistentClient(path=str(self._storage_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=get_embedding_function(),
        )

        logger.info(
            "[RAG] Vector store ready collection=%s storage_dir=%s",
            collection_name,
            self._storage_dir,
        )

    def has_documents(self) -> bool:
        return bool(self._registry)

    def add_document_chunks(
        self,
        *,
        document_id: str,
        filename: str,
        chunks: list[str],
    ) -> StoredDocument:
        if not chunks:
            raise ValueError("Cannot add an empty document.")

        ids = [f"{document_id}:{index}" for index in range(len(chunks))]
        metadatas: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            snippet = " ".join(chunk.strip().split())[:200]
            metadatas.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": index,
                    "source_snippet": snippet,
                }
            )

        self._collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

        record = StoredDocument(
            document_id=document_id,
            filename=filename,
            chunk_count=len(chunks),
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
        self._registry[document_id] = record.model_dump()
        self._save_registry()
        return record

    def list_documents(self) -> list[StoredDocument]:
        records = [StoredDocument.model_validate(payload) for payload in self._registry.values()]
        records.sort(key=lambda item: item.uploaded_at, reverse=True)
        return records

    def delete_document(self, document_id: str) -> bool:
        deleted = False
        matches = self._collection.get(
            where={"document_id": document_id},
        )
        ids = list(matches.get("ids") or [])
        if ids:
            self._collection.delete(ids=ids)
            deleted = True

        if document_id in self._registry:
            self._registry.pop(document_id, None)
            self._save_registry()
            deleted = True

        return deleted

    def query(self, *, query_text: str, limit: int) -> list[RetrievedChunk]:
        if not query_text.strip():
            return []
        if not self.has_documents():
            return []

        result = self._collection.query(
            query_texts=[query_text],
            n_results=max(1, limit),
            include=["documents", "metadatas", "distances"],
        )

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for index, document_text in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None

            if not isinstance(metadata, dict):
                metadata = {}

            chunk_index_value = metadata.get("chunk_index", 0)
            try:
                chunk_index = int(chunk_index_value)
            except (TypeError, ValueError):
                chunk_index = 0

            chunk_distance: float | None = None
            if distance is not None:
                try:
                    chunk_distance = float(distance)
                except (TypeError, ValueError):
                    chunk_distance = None

            chunks.append(
                RetrievedChunk(
                    document_id=str(metadata.get("document_id") or ""),
                    filename=str(metadata.get("filename") or "uploaded-document"),
                    chunk_index=chunk_index,
                    snippet=str(metadata.get("source_snippet") or ""),
                    content=str(document_text or ""),
                    distance=chunk_distance,
                )
            )
        return chunks

    def _load_registry(self) -> dict[str, dict[str, object]]:
        if not self._registry_path.exists():
            return {}

        try:
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("[RAG] Failed to parse documents registry, starting clean.")
            return {}

        if isinstance(payload, dict):
            return payload
        return {}

    def _save_registry(self) -> None:
        self._registry_path.write_text(
            json.dumps(self._registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


@lru_cache(maxsize=1)
def get_vector_store() -> RagVectorStore:
    return RagVectorStore()
