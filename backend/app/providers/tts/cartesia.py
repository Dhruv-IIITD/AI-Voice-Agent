from __future__ import annotations

import httpx

from app.providers.tts.base import BaseTTSClient, SynthesizedAudio


class CartesiaTTSClient(BaseTTSClient):
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "X-API-Key": self._api_key,
                    "Cartesia-Version": "2024-06-10",
                    "content-type": "application/json",
                },
                json={
                    "model_id": self._model_id,
                    "transcript": text,
                    "voice": {
                        "mode": "id",
                        "id": self._voice_id,
                    },
                    "language": "en",
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": self.sample_rate,
                    },
                },
            )
            response.raise_for_status()
        return SynthesizedAudio(audio=response.content, sample_rate=self.sample_rate)

