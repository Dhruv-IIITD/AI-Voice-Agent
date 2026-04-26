import { useCallback, useEffect, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  Track,
  type RemoteParticipant,
  type RemoteTrack,
  type RemoteTrackPublication
} from "livekit-client";

import { createSession, fetchAgents } from "../lib/api-client";
import { MOCK_AGENTS, createMockSession } from "../lib/mock-data";
import type {
  AssistantState,
  ConnectionState,
  RetrievedChunk,
  SessionCreateRequest,
  SessionResponse,
  ToolCallEntry,
  TranscriptEntry,
  VoiceWorkerEvent
} from "../types";

const VOICE_EVENT_TOPIC = "voice-event";
const ENABLE_DEBUG_LOGS =
  process.env.NEXT_PUBLIC_DEBUG_VOICE_LOGS === "true" || process.env.NODE_ENV !== "production";

function makeId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function debugLog(message: string, details?: unknown) {
  if (!ENABLE_DEBUG_LOGS) {
    return;
  }
  if (details !== undefined) {
    console.log(`[voice-session] ${message}`, details);
    return;
  }
  console.log(`[voice-session] ${message}`);
}

const MOCK_AGENT_BEHAVIORS = {
  support: {
    userPrompt: "Can you help me check what kinds of questions you can answer?",
    toolName: "lookup_faq",
    toolArguments: { question: "what can you help me with?" },
    assistantReply:
      "Absolutely. I can answer pricing, integrations, and security questions, and I can also check demo order IDs like A100, B205, or C309."
  },
  scheduler: {
    userPrompt: "Can you help me figure out the current time in India and what scheduling help you offer?",
    toolName: "current_time",
    toolArguments: { timezone: "Asia/Kolkata" },
    assistantReply:
      "Absolutely. I can help with time-zone questions, quick scheduling guidance, and policy FAQs. In the full stack version I would also call the current_time tool before answering time-sensitive questions."
  },
  calculator: {
    userPrompt: "Can you calculate 24 divided by 3 plus 7 for me?",
    toolName: "calculate_expression",
    toolArguments: { expression: "24 / 3 + 7" },
    assistantReply:
      "Absolutely. The result of 24 divided by 3 plus 7 is 15, and I can keep handling follow-up arithmetic in the same session."
  }
} as const;

export function useVoiceSession() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [assistantState, setAssistantState] = useState<AssistantState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [activeSpeakers, setActiveSpeakers] = useState(0);
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallEntry[]>([]);
  const [retrievedChunks, setRetrievedChunks] = useState<RetrievedChunk[]>([]);
  const [memorySummary, setMemorySummary] = useState("");
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const roomRef = useRef<Room | null>(null);
  const audioContainerRef = useRef<HTMLDivElement | null>(null);
  const userDraftIdRef = useRef<string | null>(null);
  const assistantDraftIdRef = useRef<string | null>(null);
  const mockTimersRef = useRef<number[]>([]);
  const userMutedRef = useRef(false);
  const assistantStateRef = useRef<AssistantState>("idle");

  useEffect(() => {
    return () => {
      debugLog("hook cleanup triggered");
      clearMockTimers();
      const currentRoom = roomRef.current;
      if (currentRoom) {
        debugLog("disconnecting room during cleanup");
        void currentRoom.disconnect();
      }
    };
  }, []);

  const fetchAgentCatalog = useCallback(async () => fetchAgents(), []);

  const clearMockTimers = useCallback(() => {
    for (const timerId of mockTimersRef.current) {
      window.clearTimeout(timerId);
    }
    mockTimersRef.current = [];
  }, []);

  const scheduleMockEvent = useCallback((delayMs: number, callback: () => void) => {
    const timerId = window.setTimeout(callback, delayMs);
    mockTimersRef.current.push(timerId);
  }, []);

  const appendTranscript = useCallback((entry: TranscriptEntry) => {
    setTranscripts((current) => [...current, entry].slice(-40));
  }, []);

  const updateTranscript = useCallback((id: string, updater: (entry: TranscriptEntry) => TranscriptEntry) => {
    setTranscripts((current) => current.map((entry) => (entry.id === id ? updater(entry) : entry)));
  }, []);

  const attachAudioTrack = useCallback((track: RemoteTrack) => {
    if (track.kind !== Track.Kind.Audio || !audioContainerRef.current) {
      return;
    }
    debugLog("attaching remote audio track", { sid: track.sid, kind: track.kind });
    const element = track.attach();
    element.autoplay = true;
    element.className = "lk-hidden-audio";
    audioContainerRef.current.appendChild(element);
  }, []);

  const detachAudioTrack = useCallback((track: RemoteTrack) => {
    if (track.kind !== Track.Kind.Audio) {
      return;
    }
    debugLog("detaching remote audio track", { sid: track.sid, kind: track.kind });
    track.detach().forEach((element) => element.remove());
  }, []);

  const syncLiveMicrophone = useCallback(
    async (room: Room | null, nextAssistantState?: AssistantState, nextUserMuted?: boolean) => {
      if (!room) {
        return;
      }

      const effectiveAssistantState = nextAssistantState ?? assistantStateRef.current;
      const effectiveUserMuted = nextUserMuted ?? userMutedRef.current;
      const shouldEnable = effectiveAssistantState === "listening" && !effectiveUserMuted;

      debugLog("syncing local microphone", {
        shouldEnable,
        assistantState: effectiveAssistantState,
        userMuted: effectiveUserMuted
      });
      await room.localParticipant.setMicrophoneEnabled(shouldEnable);
    },
    []
  );

  const handleVoiceEvent = useCallback((event: VoiceWorkerEvent) => {
    if (event.type === "assistant_delta") {
      debugLog("worker event: assistant_delta", { deltaLength: event.delta.length });
    } else {
      debugLog(`worker event: ${event.type}`, event);
    }

    if (event.type === "assistant_state") {
      assistantStateRef.current = event.state;
      setAssistantState(event.state);
      void syncLiveMicrophone(roomRef.current, event.state, userMutedRef.current);
      return;
    }

    if (event.type === "user_transcript") {
          if (event.final) {
                if (userDraftIdRef.current) {
                
                    const draftId = userDraftIdRef.current;
                updateTranscript(draftId, (entry) => ({
                    ...entry,
                    text: event.text,
                    isFinal: true,
                    provider: event.provider,
                    stt_latency_ms: event.stt_latency_ms
                }));
            userDraftIdRef.current = null;
            return;
                }

                appendTranscript({
                id: makeId("user"),
                role: "user",
                text: event.text,
                isFinal: true,
                provider: event.provider,
                stt_latency_ms: event.stt_latency_ms
                });
                return;
        }

        if (!userDraftIdRef.current) {
            userDraftIdRef.current = makeId("user-draft");
            appendTranscript({
            id: userDraftIdRef.current,
            role: "user",
            text: event.text,
            isFinal: false,
            provider: event.provider
            });
            return;
        }

        updateTranscript(userDraftIdRef.current, (entry) => ({
            ...entry,
            text: event.text,
            provider: event.provider
        }));
        return;
    }

    if (event.type === "assistant_delta") {
      if (!assistantDraftIdRef.current) {
        assistantDraftIdRef.current = makeId("assistant-draft");
        appendTranscript({
          id: assistantDraftIdRef.current,
          role: "assistant",
          text: event.delta,
          isFinal: false
        });
        return;
      }

      updateTranscript(assistantDraftIdRef.current, (entry) => ({
        ...entry,
        text: `${entry.text}${event.delta}`
      }));
      return;
    }

    if (event.type === "assistant_complete") {
      setRetrievedChunks(event.retrieved_chunks ?? []);
      setMemorySummary(event.memory_summary ?? "");
      if (assistantDraftIdRef.current) {
        const draftId = assistantDraftIdRef.current;
        updateTranscript(draftId, (entry) => ({
          ...entry,
          text: event.text,
          isFinal: true,
          llm_latency_ms: event.llm_latency_ms,
          tts_latency_ms: event.tts_latency_ms
        }));
        assistantDraftIdRef.current = null;
        return;
      }

      appendTranscript({
        id: makeId("assistant"),
        role: "assistant",
        text: event.text,
        isFinal: true,
        llm_latency_ms: event.llm_latency_ms,
        tts_latency_ms: event.tts_latency_ms
      });
      return;
    }

    if (event.type === "assistant_warning") {
      setError(event.message);
      appendTranscript({
        id: makeId("assistant-warning"),
        role: "assistant",
        text: event.message,
        isFinal: true
      });
      return;
    }

    if (event.type === "tool_call") {
      setToolCalls((current) =>
        [
          ...current,
          {
            name: event.toolName,
            arguments: event.arguments,
            resultSummary: event.resultSummary,
            createdAt: new Date().toISOString()
          }
        ].slice(-20)
      );
      appendTranscript({
        id: makeId("tool"),
        role: "tool",
        text: event.resultSummary
          ? `${event.toolName}: ${event.resultSummary}`
          : `${event.toolName}(${JSON.stringify(event.arguments)})`,
        isFinal: true
      });
    }
  }, [appendTranscript, syncLiveMicrophone, updateTranscript]);

  const disconnect = useCallback(async () => {
    debugLog("disconnect requested");
    clearMockTimers();
    const currentRoom = roomRef.current;
    if (!currentRoom) {
      debugLog("disconnect skipped because no active room exists");
      setConnectionState("idle");
      setAssistantState("disconnected");
      setIsMuted(false);
      setActiveSpeakers(0);
      setSession(null);
      setTranscripts([]);
      setToolCalls([]);
      setRetrievedChunks([]);
      setMemorySummary("");
      userMutedRef.current = false;
      assistantStateRef.current = "disconnected";
      return;
    }

    await currentRoom.disconnect();
    debugLog("room disconnected successfully");
    roomRef.current = null;
    setConnectionState("idle");
    setAssistantState("disconnected");
    setIsMuted(false);
    setActiveSpeakers(0);
    setSession(null);
    setToolCalls([]);
    setRetrievedChunks([]);
    setMemorySummary("");
    userMutedRef.current = false;
    assistantStateRef.current = "disconnected";
  }, [clearMockTimers]);

  const connectMock = useCallback(async (payload: SessionCreateRequest) => {
    debugLog("starting mock session flow", payload);
    const agent = MOCK_AGENTS.find((entry) => entry.id === payload.agent_id) ?? MOCK_AGENTS[0];
    const mockBehavior = MOCK_AGENT_BEHAVIORS[agent.id as keyof typeof MOCK_AGENT_BEHAVIORS] ?? MOCK_AGENT_BEHAVIORS.support;
    const sessionResponse = createMockSession(
      agent,
      payload.display_name,
      payload.stt_provider ?? "deepgram",
      payload.tts_provider ?? "elevenlabs"
    );

    await new Promise((resolve) => {
      scheduleMockEvent(450, () => resolve(undefined));
    });

    setSession(sessionResponse);
    setConnectionState("connected");
    setAssistantState("listening");
    setIsMuted(false);
    setActiveSpeakers(0);
    userMutedRef.current = false;
    assistantStateRef.current = "listening";
    debugLog("mock session connected", {
      sessionId: sessionResponse.session_id,
      roomName: sessionResponse.room_name,
      agentId: agent.id
    });

    scheduleMockEvent(800, () => {
      handleVoiceEvent({
        type: "user_transcript",
        text: mockBehavior.userPrompt.slice(0, 34),
        final: false,
        provider: payload.stt_provider ?? "deepgram"
      });
    });

    scheduleMockEvent(1500, () => {
      handleVoiceEvent({
        type: "user_transcript",
        text: mockBehavior.userPrompt,
        final: true,
        provider: payload.stt_provider ?? "deepgram"
      });
    });

    scheduleMockEvent(1900, () => {
      handleVoiceEvent({
        type: "assistant_state",
        state: "thinking"
      });
    });

    scheduleMockEvent(2400, () => {
      handleVoiceEvent({
        type: "tool_call",
        toolName: mockBehavior.toolName,
        arguments: mockBehavior.toolArguments
      });
    });

    let cursor = 0;
    for (const chunk of mockBehavior.assistantReply.match(/.{1,28}(\s|$)/g) ?? [mockBehavior.assistantReply]) {
      const delta = chunk;
      scheduleMockEvent(2900 + cursor * 220, () => {
        handleVoiceEvent({
          type: "assistant_delta",
          delta
        });
      });
      cursor += 1;
    }

    scheduleMockEvent(2900 + cursor * 220 + 120, () => {
      handleVoiceEvent({
        type: "assistant_complete",
        text: mockBehavior.assistantReply
      });
    });

    scheduleMockEvent(2900 + cursor * 220 + 500, () => {
      setActiveSpeakers(1);
      handleVoiceEvent({
        type: "assistant_state",
        state: "speaking"
      });
    });

    scheduleMockEvent(2900 + cursor * 220 + 2200, () => {
      setActiveSpeakers(0);
      handleVoiceEvent({
        type: "assistant_state",
        state: "listening"
      });
    });
  }, [handleVoiceEvent, scheduleMockEvent]);

  const connect = useCallback(async (payload: SessionCreateRequest, options?: { mockMode?: boolean }) => {
    debugLog("connect requested", { payload, options });
    await disconnect();

    setConnectionState("connecting");
    setAssistantState("idle");
    setError(null);
    setTranscripts([]);
    setToolCalls([]);
    setRetrievedChunks([]);
    setMemorySummary("");
    userMutedRef.current = false;
    assistantStateRef.current = "idle";
    userDraftIdRef.current = null;
    assistantDraftIdRef.current = null;

    if (options?.mockMode) {
      debugLog("entering mock mode connect flow");
      await connectMock(payload);
      return;
    }

    try {
      debugLog("creating backend session", payload);
      const sessionResponse = await createSession(payload);
      debugLog("backend session created", {
        roomName: sessionResponse.room_name,
        sessionId: sessionResponse.session_id,
        livekitUrl: sessionResponse.livekit_url,
        stt: sessionResponse.selected_stt_provider,
        tts: sessionResponse.selected_tts_provider
      });

      const room = new Room({
        adaptiveStream: true,
        dynacast: true
      });
      debugLog("livekit room object created");

      // 2. attach incoming audio from the remote assistant
      room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication, participant) => {
        debugLog("track subscribed", {
          trackSid: track.sid,
          publicationSid: publication.trackSid,
          participantIdentity: participant.identity
        });
        attachAudioTrack(track);
      });

      // 3. detach when the remote assistant stops sending audio
      room.on(
        RoomEvent.TrackUnsubscribed,
        (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
          debugLog("track unsubscribed", {
            trackSid: track.sid,
            publicationSid: publication.trackSid,
            participantIdentity: participant.identity
          });
          detachAudioTrack(track);
        }
      );

      // 4. listen for real-time events from the worker
      room.on(RoomEvent.DataReceived, (payloadBytes, _participant, _kind, topic) => {
        if (topic !== VOICE_EVENT_TOPIC) {
          return;
        }
        const raw = new TextDecoder().decode(payloadBytes);
        try {
          const parsedEvent = JSON.parse(raw) as VoiceWorkerEvent;
          debugLog("data packet received", { topic, parsedEvent });
          handleVoiceEvent(parsedEvent);
        } catch {
          debugLog("failed to parse worker data packet", { topic, raw });
        }
      });

      // 5. monitor active speakers
      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        debugLog("active speakers changed", {
          count: speakers.length,
          identities: speakers.map((speaker) => speaker.identity)
        });
        setActiveSpeakers(speakers.length);
      });

    // 6. connection
      room.on(RoomEvent.Connected, () => {
        debugLog("room connected");
      });

      // 7. disconnection
      room.on(RoomEvent.Disconnected, () => {
        debugLog("room disconnected event fired");
        userMutedRef.current = false;
        assistantStateRef.current = "disconnected";
        setConnectionState("idle");
        setAssistantState("disconnected");
        setIsMuted(false);
      });

      debugLog("connecting to livekit room", {
        url: sessionResponse.livekit_url,
        roomName: sessionResponse.room_name
      });
      await room.connect(sessionResponse.livekit_url, sessionResponse.token);
      debugLog("connected to livekit, synchronizing microphone with assistant state");
      await syncLiveMicrophone(room, "listening", false);
      debugLog("microphone synchronized");

      roomRef.current = room;
      setSession(sessionResponse);
      setConnectionState("connected");
      setAssistantState("listening");
      setIsMuted(false);
      userMutedRef.current = false;
      assistantStateRef.current = "listening";
      debugLog("session ready in frontend");
    } catch (caughtError) {
      const message =
        caughtError instanceof Error ? caughtError.message : "Unable to connect to the LiveKit room.";
      debugLog("connect failed", { message, caughtError });
      setError(message);
      setConnectionState("error");
      setAssistantState("disconnected");
    }
  }, [attachAudioTrack, connectMock, detachAudioTrack, disconnect, handleVoiceEvent, syncLiveMicrophone]);

  const toggleMute = useCallback(async () => {
    const currentRoom = roomRef.current;
    if (!currentRoom && connectionState !== "connected") {
      debugLog("toggleMute ignored because no active connection exists");
      return;
    }

    const nextMuted = !isMuted;
    userMutedRef.current = nextMuted;
    if (currentRoom) {
      debugLog("toggling live microphone", {
        nextMuted,
        assistantState: assistantStateRef.current
      });
      await syncLiveMicrophone(currentRoom, assistantStateRef.current, nextMuted);
    }
    debugLog("mute state updated", { nextMuted });
    setIsMuted(nextMuted);
  }, [connectionState, isMuted, syncLiveMicrophone]);

  return {
    activeSpeakers,
    assistantState,
    audioContainerRef,
    connect,
    connectionState,
    disconnect,
    error,
    fetchAgentCatalog,
    isConnected: connectionState === "connected",
    isMuted,
    session,
    toolCalls,
    toggleMute,
    transcripts,
    retrievedChunks,
    memorySummary
  };
}
