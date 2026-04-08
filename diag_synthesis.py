import httpx
import asyncio

async def diagnose_synthesis():
    # This key WORKED for GET /v1/models with Status 200 (prefixed)
    prefixed_key = "sk_3b4e4485f3c6d99e1caf6276b1ad10e738aa9f077ce9b474"
    
    voice_id = "EXAVITQu4vr4xnSDxMaL"
    model = "eleven_multilingual_v2"
    formats = ["pcm_24000", "mp3_44100_128"]

    print("Diagnosing Synthesis Permissions (using working prefixed key)...\n")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Verify it still works for GET
        resp = await client.get("https://api.elevenlabs.io/v1/models", headers={"xi-api-key": prefixed_key})
        print(f"GET /v1/models Status: {resp.status_code}")

        # 2. Test Synthesis with different formats
        for fmt in formats:
            print(f"Testing Synthesis with format: {fmt}...")
            # Try plain POST (non-stream)
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": prefixed_key,
                    "content-type": "application/json",
                },
                params={"output_format": fmt},
                json={
                    "text": "Check.",
                    "model_id": model,
                }
            )
            print(f"  Result: {resp.status_code}")
            if resp.status_code != 200:
                print(f"  Error Detail: {resp.text[:200]}")

if __name__ == "__main__":
    asyncio.run(diagnose_synthesis())
