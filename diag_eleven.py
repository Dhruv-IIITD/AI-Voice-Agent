import httpx
import asyncio

async def diagnose():
    # The current key in .env (48 chars after sk_)
    base_key = "3b4e4485f3c6d99e1caf6276b1ad10e738aa9f077ce9b474"
    prefixed_key = f"sk_{base_key}"
    
    voice_id = "EXAVITQu4vr4xnSDxMaL"
    models = ["eleven_multilingual_v2", "eleven_turbo_v2_5", "eleven_flash_v2_5"]
    formats = ["pcm_24000", "mp3_44100_128"]
    keys = [prefixed_key, base_key]

    print("Starting Detailed ElevenLabs Diagnostic (Synthesis Only)...\n")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for key in keys:
            key_display = key[:15] + "..." + (" (prefixed)" if key.startswith("sk_") else " (raw)")
            print(f"--- Testing Key: {key_display} ---")
            
            for model in models:
                for fmt in formats:
                    print(f"  Testing Model: {model} | Format: {fmt}...")
                    try:
                        resp = await client.post(
                            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                            headers={
                                "xi-api-key": key,
                                "content-type": "application/json",
                            },
                            params={"output_format": fmt, "optimize_streaming_latency": 0},
                            json={
                                "text": "Test.",
                                "model_id": model,
                            }
                        )
                        if resp.status_code == 200:
                            print(f"    [SUCCESS] Stream POST worked!")
                            # If it works, we stop here as we found a winner
                            return
                        else:
                            print(f"    [FAIL] Status {resp.status_code}: {resp.text[:100]}")
                    except Exception as e:
                        print(f"    [ERROR] {e}")
            print("\n")

if __name__ == "__main__":
    asyncio.run(diagnose())
