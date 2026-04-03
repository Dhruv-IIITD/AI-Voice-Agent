from __future__ import annotations

from app.core.config import Settings
from app.providers.tts.base import BaseTTSClient
from app.providers.tts.cartesia import CartesiaTTSClient
from app.providers.tts.elevenlabs import ElevenLabsTTSClient
from app.schemas.session import TtsProvider


def build_tts_provider(settings: Settings, provider: TtsProvider) -> BaseTTSClient:
    if provider == "elevenlabs":
        if not settings.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY is required when using the ElevenLabs adapter.")
        return ElevenLabsTTSClient(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            model_id=settings.elevenlabs_model_id,
            sample_rate=settings.tts_sample_rate,
        )

    if provider == "cartesia":
        if not settings.cartesia_api_key:
            raise ValueError("CARTESIA_API_KEY is required when using the Cartesia adapter.")
        return CartesiaTTSClient(
            api_key=settings.cartesia_api_key,
            voice_id=settings.cartesia_voice_id,
            model_id=settings.cartesia_model_id,
            sample_rate=settings.tts_sample_rate,
        )

    raise ValueError(f"Unsupported TTS provider '{provider}'.")

