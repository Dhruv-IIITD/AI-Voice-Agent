import httpx
import asyncio
import os

async def test_elevenlabs():
    api_key = "sk_f8535fbae568db89764f3fdc81ee3c3736818c428b48a3ec"
    voice_id = "EXAVITQu4vr4xnSDxMaL"
    model_id = "eleven_multilingual_v2"
    
    headers = {
        "xi-api-key": api_key,
        "accept": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        # 1. Test GET /v1/user
        print("Testing GET /v1/user...")
        resp_user = await client.get("https://api.elevenlabs.io/v1/user", headers=headers)
        print(f"GET /v1/user Status: {resp_user.status_code}")
        if resp_user.status_code == 200:
            print("Successfully retrieved user info.")
        else:
            print(f"Response: {resp_user.text}")

        # 2. Test GET /v1/voices
        print("\nTesting GET /v1/voices...")
        resp_voices = await client.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        print(f"GET /v1/voices Status: {resp_voices.status_code}")
        
        # 3. Test POST /v1/text-to-speech/{voice_id}
        print(f"\nTesting POST /v1/text-to-speech/{voice_id}...")
        resp_tts = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={**headers, "content-type": "application/json"},
            json={
                "text": "Hello test.",
                "model_id": model_id,
            }
        )
        print(f"POST TTS Status: {resp_tts.status_code}")
        if resp_tts.status_code != 200:
            print(f"Error Response: {resp_tts.text}")
        else:
            print("Successfully synthesized audio!")

if __name__ == "__main__":
    asyncio.run(test_elevenlabs())
