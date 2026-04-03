
## Setup

### 1. Backend

Use a virtual environment. The LiveKit agent runtime installs newer `numpy` and `protobuf` versions, so isolating dependencies is strongly recommended.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
copy .env.example .env
```

Fill in these required values in `backend/.env`:

- `LIVEKIT_WS_URL`
- `LIVEKIT_API_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- if you want to avoid paid OpenRouter models entirely, keep `OPENROUTER_REQUIRE_FREE=true` and use `OPENROUTER_MODEL=qwen/qwen3.6-plus:free` or another model ending in `:free`
- the provider keys you plan to use, such as `DEEPGRAM_API_KEY` and `ELEVENLABS_API_KEY`

Run the FastAPI app with:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the worker in a second terminal:

```bash
cd backend
.venv\Scripts\activate
python -m app.worker dev
```
