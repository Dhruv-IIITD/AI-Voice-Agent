
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
- `GROQ_API_KEY`
- `GROQ_MODEL` (optional, defaults to `llama-3.1-8b-instant`)
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
