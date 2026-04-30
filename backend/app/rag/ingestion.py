from __future__ import annotations

import io
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.rag.schemas import StoredDocument
from app.rag.vector_store import RagVectorStore, get_vector_store


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

logger = logging.getLogger(__name__)


def _load_text_document(filename: str, payload: bytes, file_type: str) -> list[Document]:
    text = payload.decode("utf-8", errors="ignore").strip()

    if not text:
        return []

    return [
        Document(
            page_content=text,
            metadata={
                "source": filename,
                "filename": filename,
                "file_type": file_type,
            },
        )
    ]


def _load_pdf_documents(filename: str, payload: bytes) -> list[Document]:
    try:
        reader = PdfReader(io.BytesIO(payload))
    except Exception as exc:
        raise ValueError("Unable to parse PDF file.") from exc

    documents: list[Document] = []

    for page_index, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()

        if not text:
            continue

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": filename,
                    "filename": filename,
                    "file_type": ".pdf",
                    "page": page_index + 1,
                },
            )
        )

    return documents


def _load_uploaded_documents(filename: str, payload: bytes) -> list[Document]:
    extension = Path(filename).suffix.lower()

    if extension in {".txt", ".md"}:
        return _load_text_document(filename, payload, extension)

    if extension == ".pdf":
        return _load_pdf_documents(filename, payload)

    raise ValueError(f"Unsupported file type: {extension}")


def _split_documents(documents: list[Document]) -> list[Document]:
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = splitter.split_documents(documents)
    cleaned_chunks: list[Document] = []

    for index, chunk in enumerate(chunks):
        content = chunk.page_content.strip()

        if not content:
            continue

        chunk.page_content = content
        chunk.metadata["chunk_index"] = index
        cleaned_chunks.append(chunk)

    logger.info(
        "[RAG] Split %s document(s) into %s chunk(s).",
        len(documents),
        len(cleaned_chunks),
    )

    return cleaned_chunks


async def ingest_uploaded_document(
    *,
    upload: UploadFile,
    vector_store: RagVectorStore | None = None,
) -> StoredDocument:
    filename = upload.filename or "uploaded-document.txt"
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type '{extension}'. Supported types: {supported}"
        )

    payload = await upload.read()

    if not payload:
        raise ValueError("Uploaded file is empty.")

    documents = _load_uploaded_documents(filename, payload)

    if not documents:
        raise ValueError("No readable text found in the uploaded file.")

    chunk_documents = _split_documents(documents)

    if not chunk_documents:
        raise ValueError("Document text could not be chunked.")

    chunks = [chunk.page_content for chunk in chunk_documents]

    store = vector_store or get_vector_store()
    document_id = uuid4().hex

    logger.info(
        "[RAG] Ingesting filename=%s document_id=%s chunks=%s",
        filename,
        document_id,
        len(chunks),
    )

    return store.add_document_chunks(
        document_id=document_id,
        filename=filename,
        chunks=chunks,
    )