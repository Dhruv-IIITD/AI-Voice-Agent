# AI Voice Agent

A custom browser-based voice AI proof of concept. You can jump in, select an agent profile, pick your Speech-to-Text (STT) and Text-to-Speech (TTS) providers, and chat in real-time.

Under the hood:
* **Frontend:** Next.js
* **Backend:** FastAPI + Python LiveKit worker
* **STT/TTS API Adapters:** Deepgram, AssemblyAI, ElevenLabs, Cartesia
* **LLM Engine:** OpenRouter (we just use their free Qwen model by default)

## Getting Started

### 1. The Backend

Open a terminal and go into the `backend` folder. Make sure you use a virtual env so you don't mess up your global python packages.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Create a `.env` file inside `backend/` and toss in your keys:
* `LIVEKIT_WS_URL`
* `LIVEKIT_API_URL`
* `LIVEKIT_API_KEY`
* `LIVEKIT_API_SECRET`
* `OPENROUTER_API_KEY`
* Any provider keys you plan on actively testing (like `DEEPGRAM_API_KEY` or `ELEVENLABS_API_KEY`)

Start the API:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open a second terminal block and fire up the LiveKit audio worker:
```bash
cd backend
.venv\Scripts\activate
python -m app.worker dev
```

### 2. The Frontend

Super simple setup here:
```bash
cd frontend
npm install
npm run dev
```
It usually listens on `http://localhost:3000`. 

If you forget to spin up the backend or want to see the UI really fast, the frontend will just fall back to a goofy local mock mode to simulate a voice session.

## Notes
Everything relies on LiveKit for passing audio back and forth perfectly. Tool calling is handled cleanly by letting the LLM plan what function to call before streaming its final text back down to the frontend. To prevent feedback issues and chaotic interruptions, your mic is paused while the bot is talking.
