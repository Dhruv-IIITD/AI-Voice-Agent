from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SttProvider = Literal["deepgram", "assemblyai"]
TtsProvider = Literal["elevenlabs", "cartesia"]


class AgentSummary(BaseModel):
    id: str
    name: str
    description: str
    system_prompt_preview: str
    tool_names: list[str]
    accent_color: str
    stt_options: list[SttProvider] = Field(default_factory=lambda: ["deepgram", "assemblyai"])
    tts_options: list[TtsProvider] = Field(default_factory=lambda: ["elevenlabs", "cartesia"])


class SessionCreateRequest(BaseModel):
    agent_id: str
    display_name: str = "Browser User"
    stt_provider: SttProvider | None = None
    tts_provider: TtsProvider | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    livekit_url: str
    room_name: str
    participant_identity: str
    participant_name: str
    token: str
    agent: AgentSummary
    selected_stt_provider: SttProvider
    selected_tts_provider: TtsProvider


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "voice-engineering-poc"

