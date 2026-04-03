from __future__ import annotations

from pydantic import BaseModel

from app.schemas.session import SttProvider, TtsProvider


class SessionMetadata(BaseModel):
    session_id: str
    room_name: str
    agent_id: str
    stt_provider: SttProvider
    tts_provider: TtsProvider
    participant_identity: str
    participant_name: str

