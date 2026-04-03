
## BackEnd Setup

### 1. Backend

Use a virtual environment..

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Fill in these required values in `backend/.env`:

- `LIVEKIT_WS_URL`
- `LIVEKIT_API_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- use `OPENROUTER_MODEL=qwen/qwen3.6-plus:free`
- the provider keys, such as `DEEPGRAM_API_KEY` and `ELEVENLABS_API_KEY`

### 1. Run the FastAPI app:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Run the LiveKit worker in a second terminal:

```bash
cd backend
.venv\Scripts\activate
python -m app.worker dev
```
