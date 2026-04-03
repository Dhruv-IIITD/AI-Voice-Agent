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

    app_name: str = "Voice Engineering POC"
    api_prefix: str = "/api"
    frontend_origin: str = "http://localhost:3000"

    livekit_ws_url: str = Field(..., alias="LIVEKIT_WS_URL")
    livekit_api_url: str | None = Field(default=None, alias="LIVEKIT_API_URL")
    livekit_api_key: str = Field(..., alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., alias="LIVEKIT_API_SECRET")
    livekit_agent_name: str = Field(default="browser-voice-agent", alias="LIVEKIT_AGENT_NAME")

    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="qwen/qwen3.6-plus:free", alias="OPENROUTER_MODEL")
    openrouter_site_url: str | None = Field(default=None, alias="OPENROUTER_SITE_URL")
    openrouter_app_name: str | None = Field(default=None, alias="OPENROUTER_APP_NAME")
    openrouter_require_free: bool = Field(default=True, alias="OPENROUTER_REQUIRE_FREE")
    llm_temperature: float = 0.2

    default_stt_provider: Literal["deepgram", "assemblyai"] = Field(
        default="deepgram",
        alias="DEFAULT_STT_PROVIDER",
    )
    deepgram_api_key: str | None = Field(default=None, alias="DEEPGRAM_API_KEY")
    deepgram_model: str = Field(default="nova-3", alias="DEEPGRAM_MODEL")
    assemblyai_api_key: str | None = Field(default=None, alias="ASSEMBLYAI_API_KEY")
    assemblyai_speech_model: str = Field(default="u3-rt-pro", alias="ASSEMBLYAI_SPEECH_MODEL")

    default_tts_provider: Literal["elevenlabs", "cartesia"] = Field(
        default="elevenlabs",
        alias="DEFAULT_TTS_PROVIDER",
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
