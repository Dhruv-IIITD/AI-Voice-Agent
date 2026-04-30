from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Voice Agent"
    api_prefix: str = "/api"
    frontend_origin: str = "http://localhost:3000"

    livekit_ws_url: str = Field(..., alias="LIVEKIT_WS_URL")
    livekit_api_url: str | None = Field(default=None, alias="LIVEKIT_API_URL")
    livekit_api_key: str = Field(..., alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., alias="LIVEKIT_API_SECRET")
    livekit_agent_name: str = Field(default="browser-voice-agent", alias="LIVEKIT_AGENT_NAME")

    llm_provider: Literal["openai", "gemini", "groq"] = Field(
        default="groq",
        alias="LLM_PROVIDER",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = Field(default=35.0, alias="LLM_TIMEOUT_SECONDS")

    default_stt_provider: Literal["deepgram", "assemblyai"] = Field(
        default="deepgram",
        alias="DEFAULT_STT_PROVIDER",
    )
    stt_fallback_provider: Literal["deepgram", "assemblyai"] | None = Field(
        default=None,
        alias="STT_FALLBACK_PROVIDER",
    )
    deepgram_api_key: str | None = Field(default=None, alias="DEEPGRAM_API_KEY")
    deepgram_model: str = Field(default="nova-3", alias="DEEPGRAM_MODEL")
    assemblyai_api_key: str | None = Field(default=None, alias="ASSEMBLYAI_API_KEY")
    assemblyai_speech_model: str = Field(default="u3-rt-pro", alias="ASSEMBLYAI_SPEECH_MODEL")

    default_tts_provider: Literal["elevenlabs", "cartesia"] = Field(
        default="elevenlabs",
        alias="DEFAULT_TTS_PROVIDER",
    )
    tts_fallback_provider: Literal["elevenlabs", "cartesia"] | None = Field(
        default=None,
        alias="TTS_FALLBACK_PROVIDER",
    )
    elevenlabs_api_key: str | None = Field(default=None, alias="ELEVENLABS_API_KEY")
    elevenlabs_model_id: str = Field(default="eleven_flash_v2_5", alias="ELEVENLABS_MODEL_ID")
    elevenlabs_voice_id: str = Field(default="EXAVITQu4vr4xnSDxMaL", alias="ELEVENLABS_VOICE_ID")
    cartesia_api_key: str | None = Field(default=None, alias="CARTESIA_API_KEY")
    cartesia_model_id: str = Field(default="sonic-2", alias="CARTESIA_MODEL_ID")
    cartesia_voice_id: str = Field(
        default="694f9389-aac1-45b6-b726-9d9369183238",
        alias="CARTESIA_VOICE_ID",
    )

    tts_sample_rate: int = Field(default=24000, alias="TTS_SAMPLE_RATE")
    audio_frame_ms: int = Field(default=20, alias="AUDIO_FRAME_MS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def resolved_livekit_api_url(self) -> str:
        source = self.livekit_api_url or self.livekit_ws_url
        if source.startswith("wss://"):
            return "https://" + source.removeprefix("wss://")
        if source.startswith("ws://"):
            return "http://" + source.removeprefix("ws://")
        return source

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
