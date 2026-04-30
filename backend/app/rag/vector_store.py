from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from app.rag.embeddings import get_embedding_function
from app.rag.schemas import RetrievedChunk, StoredDocument


logger = logging.getLogger(__name__)

COLLECTION_NAME = "voice_documents"


class RagVectorStore:
    def __init__(self) -> None:
        self._storage_dir = Path(__file__).resolve().parents[2] / ".rag_store"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        self._registry_path = self._storage_dir / "documents.json"
        self._registry = self._load_registry()

        self._client = chromadb.PersistentClient(path=str(self._storage_dir))

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=get_embedding_function(),
        )

        logger.info(
            "[RAG] Chroma vector store ready collection=%s storage_dir=%s",
            COLLECTION_NAME,
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
        cleaned_chunks = [chunk.strip() for chunk in chunks if chunk and chunk.strip()]

        if not cleaned_chunks:
            raise ValueError("Cannot add an empty document.")

        if document_id in self._registry:
            self.delete_document(document_id)

        ids = [f"{document_id}:{index}" for index in range(len(cleaned_chunks))]

        metadatas: list[dict[str, Any]] = []

        for index, chunk in enumerate(cleaned_chunks):
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
            documents=cleaned_chunks,
            metadatas=metadatas,
        )

        record = StoredDocument(
            document_id=document_id,
            filename=filename,
            chunk_count=len(cleaned_chunks),
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )

        self._registry[document_id] = record.model_dump()
        self._save_registry()

        logger.info(
            "[RAG] Added document_id=%s filename=%s chunks=%s",
            document_id,
            filename,
            len(cleaned_chunks),
        )

        return record

    def list_documents(self) -> list[StoredDocument]:
        records: list[StoredDocument] = []

        for payload in self._registry.values():
            try:
                records.append(StoredDocument.model_validate(payload))
            except Exception as exc:
                logger.warning("[RAG] Skipping invalid registry record: %s", exc)

        records.sort(key=lambda item: item.uploaded_at, reverse=True)
        return records

    def delete_document(self, document_id: str) -> bool:
        if not document_id:
            return False

        deleted = False

        matches = self._collection.get(where={"document_id": document_id})
        ids = list(matches.get("ids") or [])

        if ids:
            self._collection.delete(ids=ids)
            deleted = True

            logger.info(
                "[RAG] Deleted %s chunk(s) for document_id=%s",
                len(ids),
                document_id,
            )

        if document_id in self._registry:
            self._registry.pop(document_id, None)
            self._save_registry()
            deleted = True

        return deleted

    def query(self, *, query_text: str, limit: int) -> list[RetrievedChunk]:
        query_text = query_text.strip()

        if not query_text or not self.has_documents():
            return []

        result = self._collection.query(
            query_texts=[query_text],
            n_results=max(1, int(limit)),
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

            content = str(document_text or "")

            try:
                chunk_index = int(metadata.get("chunk_index", 0))
            except (TypeError, ValueError):
                chunk_index = 0

            try:
                chunk_distance = float(distance) if distance is not None else None
            except (TypeError, ValueError):
                chunk_distance = None

            snippet = str(
                metadata.get("source_snippet")
                or " ".join(content.strip().split())[:200]
            )

            chunks.append(
                RetrievedChunk(
                    document_id=str(metadata.get("document_id") or ""),
                    filename=str(metadata.get("filename") or "uploaded-document"),
                    chunk_index=chunk_index,
                    snippet=snippet,
                    content=content,
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

        if not isinstance(payload, dict):
            logger.warning("[RAG] Documents registry was not a dictionary, starting clean.")
            return {}

        return payload

    def _save_registry(self) -> None:
        self._registry_path.write_text(
            json.dumps(self._registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


@lru_cache(maxsize=1)
def get_vector_store() -> RagVectorStore:
    return RagVectorStore()