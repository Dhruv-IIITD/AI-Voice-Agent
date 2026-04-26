from __future__ import annotations

import logging
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from livekit import api

from app.agents.catalog import AgentDefinition
from app.core.config import Settings
from app.runtime.session_metadata import SessionMetadata
from app.schemas.session import SessionCreateRequest, SessionCreateResponse, SttProvider, TtsProvider

logger = logging.getLogger(__name__)

class LiveKitSessionManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # This method creates a LiveKit room and creates an agent dispatch for the session, 
    # then generates a participant token and returns the session details.
    async def create_session(
        self,
        *,
        agent: AgentDefinition,
        payload: SessionCreateRequest,
    ) -> SessionCreateResponse:
        logger.info(
            "Provisioning LiveKit session for agent=%s display_name=%s",
            agent.id,
            payload.display_name,
        )
        session_id = uuid4().hex
        room_name = f"voice-{agent.id}-{session_id[:8]}"
        participant_identity = f"user-{session_id[:8]}"
        stt_provider = payload.stt_provider or self._settings.default_stt_provider
        tts_provider = payload.tts_provider or self._settings.default_tts_provider
        self._validate_provider_selection(stt_provider=stt_provider, tts_provider=tts_provider)
        logger.info(
            "Resolved provider selection stt=%s tts=%s room_name=%s",
            stt_provider,
            tts_provider,
            room_name,
        )

        metadata = SessionMetadata(
            session_id=session_id,
            room_name=room_name,
            agent_id=agent.id,
            stt_provider=stt_provider,
            tts_provider=tts_provider,
            participant_identity=participant_identity,
            participant_name=payload.display_name,
        )

        try:
            async with api.LiveKitAPI(
                url=self._settings.resolved_livekit_api_url,
                api_key=self._settings.livekit_api_key,
                api_secret=self._settings.livekit_api_secret,
            ) as lkapi:
                logger.info("Creating room via LiveKit API at %s", self._settings.resolved_livekit_api_url)
                # create a room for the session with room_name 
                await lkapi.room.create_room(
                    api.CreateRoomRequest(
                        name=room_name,
                        empty_timeout=60 * 5,
                        max_participants=4,
                    )
                )
                logger.info("Room created successfully room_name=%s", room_name)
                await lkapi.agent_dispatch.create_dispatch(
                    api.CreateAgentDispatchRequest(
                        agent_name=self._settings.livekit_agent_name,
                        room=room_name,
                        metadata=metadata.model_dump_json(),
                    )
                )
                logger.info(
                    "Worker dispatch created agent_name=%s room_name=%s",
                    self._settings.livekit_agent_name,
                    room_name,
                )
        except Exception as exc: 
            logger.exception("Failed to provision LiveKit session")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to provision the LiveKit room or worker dispatch.",
            ) from exc

        token = (
            api.AccessToken(self._settings.livekit_api_key, self._settings.livekit_api_secret)
            .with_identity(participant_identity)
            .with_name(payload.display_name)
            .with_metadata(metadata.model_dump_json())
            .with_ttl(timedelta(hours=1))
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .to_jwt()
        )
        logger.info(
            "Generated participant token for session_id=%s participant_identity=%s",
            session_id,
            participant_identity,
        )

        return SessionCreateResponse(
            session_id=session_id,
            livekit_url=self._settings.livekit_ws_url,
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=payload.display_name,
            token=token,
            agent=agent.as_summary(),
            selected_stt_provider=stt_provider,
            selected_tts_provider=tts_provider,
        )

    def _validate_provider_selection(
        self,
        *,
        stt_provider: SttProvider,
        tts_provider: TtsProvider,
    ) -> None:
        if stt_provider == "deepgram" and not self._settings.deepgram_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected STT provider 'deepgram' is missing DEEPGRAM_API_KEY.",
            )
        if stt_provider == "assemblyai" and not self._settings.assemblyai_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected STT provider 'assemblyai' is missing ASSEMBLYAI_API_KEY.",
            )
        if tts_provider == "elevenlabs" and not self._settings.elevenlabs_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected TTS provider 'elevenlabs' is missing ELEVENLABS_API_KEY.",
            )
        if tts_provider == "cartesia" and not self._settings.cartesia_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected TTS provider 'cartesia' is missing CARTESIA_API_KEY.",
            )
