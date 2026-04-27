from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.rag.schemas import StoredDocument
from app.rag.vector_store import RagVectorStore, get_vector_store

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}
logger = logging.getLogger(__name__)


def _extract_txt(payload: bytes) -> str:
    return payload.decode("utf-8", errors="ignore")


def _extract_pdf(payload: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(payload))
    except Exception as exc:
        raise ValueError("Unable to parse PDF file.") from exc

    page_text: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted.strip():
            page_text.append(extracted)
    return "\n\n".join(page_text)

 
def _extract_text(filename: str, payload: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension == ".txt":
        return _extract_txt(payload)
    if extension == ".pdf":
        return _extract_pdf(payload)
    raise ValueError(f"Unsupported file type: {extension}")


def _split_text(content: str) -> list[str]:
    try:
        chunk_size = max(200, int(os.getenv("RAG_CHUNK_SIZE", "900")))
    except ValueError:
        logger.warning("[RAG] Invalid RAG_CHUNK_SIZE provided; falling back to 900.")
        chunk_size = 900

    try:
        chunk_overlap = max(0, int(os.getenv("RAG_CHUNK_OVERLAP", "120")))
    except ValueError:
        logger.warning("[RAG] Invalid RAG_CHUNK_OVERLAP provided; falling back to 120.")
        chunk_overlap = 120

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = [chunk.strip() for chunk in splitter.split_text(content) if chunk.strip()]
    return chunks


async def ingest_uploaded_document(
    *,
    upload: UploadFile,
    vector_store: RagVectorStore | None = None,
) -> StoredDocument:
    filename = upload.filename or "uploaded-document.txt"
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {supported}")

    payload = await upload.read()
    if not payload:
        raise ValueError("Uploaded file is empty.")

    text = _extract_text(filename, payload).strip()
    if not text:
        raise ValueError("No readable text found in the uploaded file.")

    chunks = _split_text(text)
    if not chunks:
        raise ValueError("Document text could not be chunked.")

    store = vector_store or get_vector_store()
    document_id = uuid4().hex
    return store.add_document_chunks(
        document_id=document_id,
        filename=filename,
        chunks=chunks,
    )
