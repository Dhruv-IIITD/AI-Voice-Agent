import httpx
import asyncio

async def quick_test():
    base_key = "3b4e4485f3c6d99e1caf6276b1ad10e738aa9f077ce9b474"
    prefixed_key = f"sk_{base_key}"
    
    async with httpx.AsyncClient() as client:
        # Check raw key first
        for key in [base_key, prefixed_key]:
            resp = await client.get("https://api.elevenlabs.io/v1/models", headers={"xi-api-key": key})
            print(f"Key {'prefixed' if key.startswith('sk_') else 'raw'} Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"  Error: {resp.text[:100]}")

if __name__ == "__main__":
    asyncio.run(quick_test())
