import type { SttProvider, TtsProvider } from "../types";

export const STT_OPTIONS: Array<{ label: string; value: SttProvider }> = [
  { label: "Deepgram", value: "deepgram" },
  { label: "AssemblyAI", value: "assemblyai" }
];

export const TTS_OPTIONS: Array<{ label: string; value: TtsProvider }> = [
  { label: "ElevenLabs", value: "elevenlabs" },
  { label: "Cartesia", value: "cartesia" }
];

export const PROVIDER_GROUPS = [
  {
    title: "Speech-to-text",
    description: "The worker can swap STT providers through a common abstraction layer.",
    items: ["Deepgram streaming adapter", "AssemblyAI streaming adapter"]
  },
  {
    title: "Text-to-speech",
    description: "Assistant responses are synthesized through app-owned TTS wrappers.",
    items: ["ElevenLabs PCM streaming", "Cartesia bytes synthesis"]
  },
  {
    title: "Runtime orchestration",
    description: "LiveKit manages transport while the application owns the intelligence path.",
    items: ["FastAPI session provisioning", "Worker dispatch", "Tool planning", "LLM streaming"]
  }
];

