import type { AgentSummary, SessionResponse } from "../types";

export const MOCK_AGENTS: AgentSummary[] = [
  {
    id: "support",
    name: "Support Agent",
    description: "Handles product FAQs and can look up demo order statuses for support-style conversations.",
    system_prompt_preview: "You are a concise support agent for a SaaS product demo.",
    tool_names: ["lookup_faq", "lookup_order_status"],
    accent_color: "#C5522B",
    stt_options: ["deepgram", "assemblyai"],
    tts_options: ["elevenlabs", "cartesia"]
  },
  {
    id: "scheduler",
    name: "Scheduling Agent",
    description: "Answers current-time and simple scheduling questions with timezone awareness.",
    system_prompt_preview: "You are a scheduling assistant for a browser voice demo.",
    tool_names: ["current_time", "lookup_faq"],
    accent_color: "#186B5C",
    stt_options: ["deepgram", "assemblyai"],
    tts_options: ["elevenlabs", "cartesia"]
  },
  {
    id: "calculator",
    name: "Calculator Agent",
    description: "Solves arithmetic requests and explains the result in a short, grounded response.",
    system_prompt_preview: "You are a calculator assistant for a browser voice demo.",
    tool_names: ["calculate_expression"],
    accent_color: "#5E6FD8",
    stt_options: ["deepgram", "assemblyai"],
    tts_options: ["elevenlabs", "cartesia"]
  }
];

export function createMockSession(
  agent: AgentSummary,
  displayName: string,
  sttProvider: SessionResponse["selected_stt_provider"],
  ttsProvider: SessionResponse["selected_tts_provider"]
): SessionResponse {
  return {
    session_id: `mock-${crypto.randomUUID().slice(0, 8)}`,
    livekit_url: "mock://local-preview",
    room_name: `mock-room-${agent.id}`,
    participant_identity: `preview-${crypto.randomUUID().slice(0, 8)}`,
    participant_name: displayName,
    token: "mock-token",
    selected_stt_provider: sttProvider,
    selected_tts_provider: ttsProvider,
    agent
  };
}
