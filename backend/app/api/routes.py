from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.agents.catalog import get_agent, list_agents
from app.core.config import Settings, get_settings
from app.livekit.session_manager import LiveKitSessionManager
from app.rag.ingestion import ingest_uploaded_document
from app.rag.schemas import DocumentDeleteResponse, DocumentListResponse, DocumentUploadResponse
from app.rag.vector_store import get_vector_store
from app.schemas.session import HealthResponse, SessionCreateRequest, SessionCreateResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _rag_unavailable_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="RAG storage is unavailable. Check vector DB and embedding configuration.",
    )

@router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    # simple health check so we know backend is alive
    logger.info("Healthcheck requested")
    return HealthResponse()

@router.get("/agents")
async def agents() -> list[dict]:
    logger.info("Agent catalog requested")
    return [agent.model_dump() for agent in list_agents()]

@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    payload:SessionCreateRequest,
    settings:Settings = Depends(get_settings),
) -> SessionCreateResponse:
    # 
    logger.info(
        "Create session requested for agent=%s display_name=%s stt=%s tts=%s",
        payload.agent_id,
        payload.display_name,
        payload.stt_provider,
        payload.tts_provider,
    )

    # 2. validate agent exists
    try:
        agent = get_agent(payload.agent_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # 3. create LiveKit session via manager
    manager = LiveKitSessionManager(settings)
    response = await manager.create_session(agent=agent, payload=payload)
    
    logger.info(
        "Session created successfully session_id=%s room_name=%s participant_identity=%s",
        response.session_id,
        response.room_name,
        response.participant_identity,
    )
    return response

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    logger.info("Document upload requested filename=%s", file.filename)
    try:
        # Upload the document into RAG Pipeline
        document = await ingest_uploaded_document(upload=file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Document upload failed unexpectedly filename=%s", file.filename)
        raise _rag_unavailable_exception() from exc
    finally:
        await file.close()

    logger.info(
        "Document upload completed document_id=%s filename=%s chunk_count=%s",
        document.document_id,
        document.filename,
        document.chunk_count,
    )
    return DocumentUploadResponse(document=document)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    try:
        documents = get_vector_store().list_documents()
    except Exception as exc:
        logger.exception("Failed to list documents from vector store")
        raise _rag_unavailable_exception() from exc

    logger.info("Documents listed count=%s", len(documents))
    return DocumentListResponse(documents=documents)


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(document_id: str) -> DocumentDeleteResponse:
    try:
        deleted = get_vector_store().delete_document(document_id=document_id)
    except Exception as exc:
        logger.exception("Failed to delete document document_id=%s", document_id)
        raise _rag_unavailable_exception() from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found.",
        )

    logger.info("Document deleted document_id=%s", document_id)
    return DocumentDeleteResponse(document_id=document_id, deleted=True)
