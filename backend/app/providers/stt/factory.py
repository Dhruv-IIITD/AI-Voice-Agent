from __future__ import annotations

from app.core.config import Settings
from app.providers.stt.assemblyai import AssemblyAIStreamingSTT
from app.providers.stt.base import BaseStreamingSTT
from app.providers.stt.deepgram import DeepgramStreamingSTT
from app.schemas.session import SttProvider


def build_stt_provider(settings: Settings, provider: SttProvider) -> BaseStreamingSTT:
    if provider == "deepgram":
        if not settings.deepgram_api_key:
            raise ValueError("DEEPGRAM_API_KEY is required when using the Deepgram adapter.")
        return DeepgramStreamingSTT(
            api_key=settings.deepgram_api_key,
            model=settings.deepgram_model,
        )

    if provider == "assemblyai":
        if not settings.assemblyai_api_key:
            raise ValueError("ASSEMBLYAI_API_KEY is required when using the AssemblyAI adapter.")
        return AssemblyAIStreamingSTT(
            api_key=settings.assemblyai_api_key,
            speech_model=settings.assemblyai_speech_model,
        )

    raise ValueError(f"Unsupported STT provider '{provider}'.")

