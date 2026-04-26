from __future__ import annotations

import logging

import httpx

from app.providers.tts.base import BaseTTSClient, SynthesizedAudio

logger = logging.getLogger(__name__)


class ElevenLabsTTSClient(BaseTTSClient):
    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model_id: str,
        sample_rate: int,
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self.sample_rate = sample_rate

    async def synthesize(self, text: str) -> SynthesizedAudio:
        logger.info(
            "ElevenLabs synthesis requested voice_id=%s text_length=%s",
            self._voice_id,
            len(text),
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}/stream",
                params={
                    "output_format": f"pcm_{self.sample_rate}",
                    "optimize_streaming_latency": 4,
                },
                headers={
                    "xi-api-key": self._api_key,
                    "accept": "audio/pcm",
                    "content-type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": self._model_id,
                    "voice_settings": {
                        "stability": 0.45,
                        "similarity_boost": 0.8,
                    },
                },
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(
                        "ElevenLabs synthesis failed status=%s body=%s",
                        response.status_code,
                        error_body.decode(errors="ignore")[:500],
                    )
                    response.raise_for_status()

                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
        return SynthesizedAudio(audio=bytes(chunks), sample_rate=self.sample_rate)

