"use client";

import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";

import { useVoiceSession } from "../hooks/use-voice-session";
import { fetchAgents, fetchBackendHealth } from "../lib/api-client";
import { buildAgentProfiles, createFallbackAgentProfiles, type AgentProfile } from "../lib/agent-profiles";
import { toUserFriendlyBackendError } from "../lib/error-utils";
import { STT_OPTIONS, TTS_OPTIONS } from "../lib/constants";
import type { SttProvider, TtsProvider } from "../types";

export type BackendConnectionStatus = "connected" | "unavailable" | "preview" | "checking";

const BACKEND_UNAVAILABLE_MESSAGE =
  "Backend is unavailable. Start the FastAPI backend and LiveKit worker to use real voice, RAG, memory, and metrics features.";

interface VoicePlatformContextValue {
  agents: AgentProfile[];
  selectedAgent: AgentProfile | null;
  selectedAgentId: string;
  setSelectedAgentId: (agentId: string) => void;
  agentsLoading: boolean;
  agentsError: string | null;
  sttProvider: SttProvider;
  ttsProvider: TtsProvider;
  setSttProvider: (provider: SttProvider) => void;
  setTtsProvider: (provider: TtsProvider) => void;
  availableSttOptions: Array<{ label: string; value: SttProvider }>;
  availableTtsOptions: Array<{ label: string; value: TtsProvider }>;
  providerSelectionLocked: boolean;
  backendStatus: BackendConnectionStatus;
  backendMessage: string | null;
  frontendPreviewMode: boolean;
  refreshBackendStatus: () => Promise<void>;
  connectSession: () => Promise<void>;
  disconnectSession: () => Promise<void>;
  toggleMute: () => Promise<void>;
  voiceSession: ReturnType<typeof useVoiceSession>;
}

const VoicePlatformContext = createContext<VoicePlatformContextValue | undefined>(undefined);

export function VoicePlatformProvider({ children }: PropsWithChildren) {
  const voiceSession = useVoiceSession();
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [sttProvider, setSttProvider] = useState<SttProvider>("deepgram");
  const [ttsProvider, setTtsProvider] = useState<TtsProvider>("elevenlabs");
  const [frontendPreviewMode, setFrontendPreviewMode] = useState(false);
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);

  const refreshBackendStatus = useCallback(async () => {
    try {
      await fetchBackendHealth();
      setBackendReachable(true);
    } catch {
      setBackendReachable(false);
    }
  }, []);

  const loadAgents = useCallback(async () => {
    setAgentsLoading(true);
    try {
      const backendAgents = await fetchAgents();
      const mappedAgents = buildAgentProfiles(backendAgents);
      setAgents(mappedAgents);
      setSelectedAgentId((current) => current || mappedAgents[0]?.id || "");
      setFrontendPreviewMode(false);
      setAgentsError(null);
      setBackendReachable(true);
    } catch (caughtError) {
      const fallbackAgents = createFallbackAgentProfiles();
      setAgents(fallbackAgents);
      setSelectedAgentId((current) => current || fallbackAgents[0]?.id || "");
      setFrontendPreviewMode(true);
      setBackendReachable(false);
      setAgentsError(toUserFriendlyBackendError(caughtError, BACKEND_UNAVAILABLE_MESSAGE));
    } finally {
      setAgentsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void refreshBackendStatus();
    }, 15000);
    return () => window.clearInterval(intervalId);
  }, [refreshBackendStatus]);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [agents, selectedAgentId]
  );

  const availableSttOptions = useMemo(() => {
    if (!selectedAgent) {
      return STT_OPTIONS;
    }
    const options = STT_OPTIONS.filter((option) => selectedAgent.stt_options.includes(option.value));
    return options.length > 0 ? options : STT_OPTIONS;
  }, [selectedAgent]);

  const availableTtsOptions = useMemo(() => {
    if (!selectedAgent) {
      return TTS_OPTIONS;
    }
    const options = TTS_OPTIONS.filter((option) => selectedAgent.tts_options.includes(option.value));
    return options.length > 0 ? options : TTS_OPTIONS;
  }, [selectedAgent]);

  useEffect(() => {
    if (availableSttOptions.length > 0 && !availableSttOptions.some((option) => option.value === sttProvider)) {
      setSttProvider(availableSttOptions[0].value);
    }
  }, [availableSttOptions, sttProvider]);

  useEffect(() => {
    if (availableTtsOptions.length > 0 && !availableTtsOptions.some((option) => option.value === ttsProvider)) {
      setTtsProvider(availableTtsOptions[0].value);
    }
  }, [availableTtsOptions, ttsProvider]);

  const providerSelectionLocked =
    voiceSession.connectionState === "connecting" || voiceSession.connectionState === "connected";

  const connectSession = useCallback(async () => {
    if (!selectedAgent) {
      return;
    }

    await voiceSession.connect(
      {
        agent_id: selectedAgent.backend_agent_id,
        display_name: "Browser User",
        stt_provider: sttProvider,
        tts_provider: ttsProvider
      },
      { mockMode: frontendPreviewMode, mockScenarioId: selectedAgent.id }
    );
  }, [frontendPreviewMode, selectedAgent, sttProvider, ttsProvider, voiceSession]);

  const backendStatus: BackendConnectionStatus = useMemo(() => {
    if (frontendPreviewMode) {
      return "preview";
    }
    if (backendReachable === true) {
      return "connected";
    }
    if (backendReachable === false) {
      return "unavailable";
    }
    return "checking";
  }, [backendReachable, frontendPreviewMode]);

  const backendMessage = useMemo(() => {
    if (backendStatus === "preview") {
      return BACKEND_UNAVAILABLE_MESSAGE;
    }
    if (backendStatus === "unavailable") {
      return BACKEND_UNAVAILABLE_MESSAGE;
    }
    return null;
  }, [backendStatus]);

  const contextValue = useMemo<VoicePlatformContextValue>(
    () => ({
      agents,
      selectedAgent,
      selectedAgentId,
      setSelectedAgentId,
      agentsLoading,
      agentsError,
      sttProvider,
      ttsProvider,
      setSttProvider,
      setTtsProvider,
      availableSttOptions,
      availableTtsOptions,
      providerSelectionLocked,
      backendStatus,
      backendMessage,
      frontendPreviewMode,
      refreshBackendStatus,
      connectSession,
      disconnectSession: voiceSession.disconnect,
      toggleMute: voiceSession.toggleMute,
      voiceSession
    }),
    [
      agents,
      selectedAgent,
      selectedAgentId,
      agentsLoading,
      agentsError,
      sttProvider,
      ttsProvider,
      availableSttOptions,
      availableTtsOptions,
      providerSelectionLocked,
      backendStatus,
      backendMessage,
      frontendPreviewMode,
      refreshBackendStatus,
      connectSession,
      voiceSession
    ]
  );

  return <VoicePlatformContext.Provider value={contextValue}>{children}</VoicePlatformContext.Provider>;
}

export function useVoicePlatform() {
  const context = useContext(VoicePlatformContext);
  if (!context) {
    throw new Error("useVoicePlatform must be used within VoicePlatformProvider");
  }
  return context;
}
