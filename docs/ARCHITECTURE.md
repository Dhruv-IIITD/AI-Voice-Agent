# Architecture Notes

This is a quick breakdown of how the pieces fit together without getting into too much detail.

We basically split this into three chunks:
1. **Frontend:** React/Next.js UI for the frontend.
2. **API layer:** A FastAPI app handling standard CRUD and connection setup.
3. **Worker:** A persistent Python worker that actually plugs into the LiveKit audio room.

### How a session works
1. You load the frontend, pick an agent/voice, and hit connect. This sends a `POST /api/sessions` to the backend.
2. FastAPI provisions a room through LiveKit, flags down the python worker, and hands a secure connection token right back to your browser.
3. Your browser connects straight to LiveKit WebRTC and starts pushing microphone frames.
4. The worker script (`backend/app/worker.py`) sits in that identical room, subscribes to your mic, and pumps those audio frames straight into Deepgram or AssemblyAI.
5. As transcriptions finish, they get handed to the OpenRouter LLM. The LLM decides if it needs to trigger any function calls (tools), and then just streams the final response.
6. We synthesize that text with ElevenLabs (or Cartesia) and inject the resulting audio directly back into the LiveKit room so you can hear it.

### Other notes

- We use explicit provider wrappers in `backend/app/providers` instead of monolithic plugins so it's easy to swap things out.
- The UI stays up to date by listening to simple JSON events that the python worker sends over the LiveKit data channel (stuff like `user_transcript` or `assistant_state`).
- The application stops sending your mic audio to STT when the bot is talking to prevent feedback loops. We just feed it silence so the STT engine properly flushes the end of your sentence.
