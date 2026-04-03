export type SttProvider = "deepgram" | "assemblyai";
export type TtsProvider = "elevenlabs" | "cartesia";
export type ConnectionState = "idle" | "connecting" | "connected" | "error";
export type AssistantState = "idle" | "listening" | "thinking" | "speaking" | "disconnected";

export interface AgentSummary {
  id: string;
  name: string;
  description: string;
  system_prompt_preview: string;
  tool_names: string[];
  accent_color: string;
  stt_options: SttProvider[];
  tts_options: TtsProvider[];
}

export interface SessionCreateRequest {
  agent_id: string;
  display_name: string;
  stt_provider?: SttProvider;
  tts_provider?: TtsProvider;
}

export interface SessionResponse {
  session_id: string;
  livekit_url: string;
  room_name: string;
  participant_identity: string;
  participant_name: string;
  token: string;
  selected_stt_provider: SttProvider;
  selected_tts_provider: TtsProvider;
  agent: AgentSummary;
}

export interface TranscriptEntry {
  id: string;
  role: "user" | "assistant" | "tool";
  text: string;
  isFinal: boolean;
  provider?: string;
}

export type VoiceWorkerEvent =
  | {
      type: "session_ready";
      agentId: string;
      agentName: string;
      roomName: string;
    }
  | {
      type: "assistant_state";
      state: AssistantState;
    }
  | {
      type: "user_transcript";
      text: string;
      final: boolean;
      provider: string;
    }
  | {
      type: "assistant_delta";
      delta: string;
    }
  | {
      type: "assistant_complete";
      text: string;
    }
  | {
      type: "tool_call";
      toolName: string;
      arguments: Record<string, unknown>;
    };

