from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.catalog import get_agent, list_agents
from app.core.config import Settings, get_settings
from app.livekit.session_manager import LiveKitSessionManager
from app.schemas.session import HealthResponse, SessionCreateRequest, SessionCreateResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    logger.info("Healthcheck requested")
    return HealthResponse()

@router.get("/agents")
async def agents() -> list[dict]:
    logger.info("Agent catalog requested")
    return [agent.model_dump() for agent in list_agents()]

@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    payload: SessionCreateRequest,
    settings: Settings = Depends(get_settings),
) -> SessionCreateResponse:
    logger.info(
        "Create session requested for agent=%s display_name=%s stt=%s tts=%s",
        payload.agent_id,
        payload.display_name,
        payload.stt_provider,
        payload.tts_provider,
    )
    try:
        agent = get_agent(payload.agent_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    manager = LiveKitSessionManager(settings)
    response = await manager.create_session(agent=agent, payload=payload)
    logger.info(
        "Session created successfully session_id=%s room_name=%s participant_identity=%s",
        response.session_id,
        response.room_name,
        response.participant_identity,
    )
    return response
