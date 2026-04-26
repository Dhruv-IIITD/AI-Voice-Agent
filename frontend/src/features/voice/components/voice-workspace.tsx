"use client";

import { type CSSProperties, useCallback, useEffect, useMemo, useState } from "react";

import { useVoiceSession } from "../hooks/use-voice-session";
import { deleteDocument, fetchDocuments, uploadDocument } from "../lib/api-client";
import { STT_OPTIONS, TTS_OPTIONS } from "../lib/constants";
import { MOCK_AGENTS } from "../lib/mock-data";
import type { AgentSummary, AssistantState, DocumentSummary, SttProvider, TtsProvider } from "../types";
import { AgentSelector } from "./agent-selector";
import { SessionControls } from "./session-controls";
import { TranscriptPanel } from "./transcript-panel";
import styles from "./voice-workspace.module.css";

const PROVIDER_LABELS = new Map<string, string>(
  [...STT_OPTIONS, ...TTS_OPTIONS].map((option) => [option.value, option.label])
);

const SIDEBAR_ITEMS = [
  { label: "Voice Chat", short: "VC", active: true },
  { label: "Providers", short: "PR", active: false },
  { label: "Transcript", short: "TR", active: false }
];

const WAVEFORM_BARS = Array.from({ length: 20 }, (_, index) => index);

const ASSISTANT_LABELS: Record<AssistantState, string> = {
  idle: "Inactive",
  listening: "Listening",
  thinking: "Processing",
  speaking: "Speaking",
  disconnected: "Disconnected"
};

function providerLabel(provider: string | undefined) {
  if (!provider) {
    return "Unavailable";
  }

  return PROVIDER_LABELS.get(provider) ?? provider;
}

function shortProviderLabel(provider: string) {
  return provider
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();
}

export function VoiceWorkspace() {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [sttProvider, setSttProvider] = useState<SttProvider>("deepgram");
  const [ttsProvider, setTtsProvider] = useState<TtsProvider>("elevenlabs");
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [frontendOnlyMode, setFrontendOnlyMode] = useState(false);
  const [modeNotice, setModeNotice] = useState<string | null>(null);
  const [utilityCollapsed, setUtilityCollapsed] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [uploadingDocument, setUploadingDocument] = useState(false);

  const voiceSession = useVoiceSession();
  const { fetchAgentCatalog } = voiceSession;

  useEffect(() => {
    let active = true;

    async function loadAgents() {
      try {
        const response = await fetchAgentCatalog();
        if (!active) {
          return;
        }

        setAgents(response);
        setSelectedAgentId(response[0]?.id ?? "");
      } catch (caughtError) {
        if (!active) {
          return;
        }

        setAgents(MOCK_AGENTS);
        setSelectedAgentId(MOCK_AGENTS[0]?.id ?? "");
        setFrontendOnlyMode(true);
        setModeNotice(
          caughtError instanceof Error
            ? `Backend unavailable, so the app is running in frontend-only preview mode. ${caughtError.message}`
            : "Backend unavailable, so the app is running in frontend-only preview mode."
        );
      } finally {
        if (active) {
          setLoadingAgents(false);
        }
      }
    }

    void loadAgents();
    return () => {
      active = false;
    };
  }, [fetchAgentCatalog]);

  const loadDocuments = useCallback(async () => {
    setLoadingDocuments(true);
    try {
      const uploadedDocuments = await fetchDocuments();
      setDocuments(uploadedDocuments);
      setDocumentsError(null);
    } catch (caughtError) {
      setDocumentsError(
        caughtError instanceof Error ? caughtError.message : "Failed to load uploaded documents."
      );
    } finally {
      setLoadingDocuments(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId);
  const availableSttOptions = useMemo(
    () =>
      selectedAgent
        ? STT_OPTIONS.filter((option) => selectedAgent.stt_options.includes(option.value))
        : STT_OPTIONS,
    [selectedAgent]
  );
  const availableTtsOptions = useMemo(
    () =>
      selectedAgent
        ? TTS_OPTIONS.filter((option) => selectedAgent.tts_options.includes(option.value))
        : TTS_OPTIONS,
    [selectedAgent]
  );

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

    // handles our connection to the backend
    async function handleConnect() {
        if (!selectedAgentId) {
            return;
        }

        await voiceSession.connect(
        {
            agent_id: selectedAgentId,
            display_name: "Browser User",
            stt_provider: sttProvider,
            tts_provider: ttsProvider
        },
        { mockMode: frontendOnlyMode }
        );
    }

  async function handleDocumentUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.currentTarget.value = "";
    if (!file) {
      return;
    }

    setUploadingDocument(true);
    try {
      const uploadedDocument = await uploadDocument(file);
      setDocuments((current) => [uploadedDocument, ...current.filter((entry) => entry.document_id !== uploadedDocument.document_id)]);
      setDocumentsError(null);
    } catch (caughtError) {
      setDocumentsError(
        caughtError instanceof Error ? caughtError.message : "Failed to upload document."
      );
    } finally {
      setUploadingDocument(false);
    }
  }

  async function handleDeleteDocument(documentId: string) {
    try {
      await deleteDocument(documentId);
      setDocuments((current) => current.filter((entry) => entry.document_id !== documentId));
      setDocumentsError(null);
    } catch (caughtError) {
      setDocumentsError(
        caughtError instanceof Error ? caughtError.message : "Failed to delete document."
      );
    }
  }

  const providerSelectionLocked =
    voiceSession.connectionState === "connecting" || voiceSession.connectionState === "connected";
  const liveModeLabel = frontendOnlyMode ? "Frontend preview" : "Live backend session";
  const currentRoomName = voiceSession.session?.room_name ?? (frontendOnlyMode ? "mock-room" : "waiting-room");
  const sessionSttProvider = providerLabel(voiceSession.session?.selected_stt_provider ?? sttProvider);
  const sessionTtsProvider = providerLabel(voiceSession.session?.selected_tts_provider ?? ttsProvider);
  const statusLabel =
    voiceSession.connectionState === "connecting"
      ? "Connecting"
      : voiceSession.connectionState === "error"
        ? "Error"
        : voiceSession.isConnected
          ? "Connected"
          : "Ready";
  const statusClassName =
    voiceSession.connectionState === "connecting"
      ? styles.statePillBusy
      : voiceSession.connectionState === "error"
        ? styles.statePillError
        : voiceSession.isConnected
          ? styles.statePillLive
          : styles.statePillIdle;
  const utilityStatus = voiceSession.isConnected
    ? "LiveKit connected"
    : frontendOnlyMode
      ? "Frontend preview"
      : "Ready to connect";
  const activityStatus = voiceSession.isConnected ? ASSISTANT_LABELS[voiceSession.assistantState] : "Inactive";
  const recentTranscript = [...voiceSession.transcripts].slice(-4).reverse();
  const recentToolCalls = [...voiceSession.toolCalls].slice(-4).reverse();
  const recentChunks = voiceSession.retrievedChunks.slice(0, 3);

  return (
    <main className="pageShell">
    
      <section className={styles.dashboardShell}>
    
        <aside className={`${styles.utilitySidebar} ${utilityCollapsed ? styles.utilitySidebarCollapsed : ""}`}>
          <div className={styles.utilityTopRow}>
            <div className={styles.utilityBrand}>
              <span className={styles.utilityBrandMark}>VA</span>
              {!utilityCollapsed ? (
                <div className={styles.utilityBrandCopy}>
                  <strong>VoiceAI</strong>
                </div>
              ) : null}
            </div>

            {/* <button
              aria-label={utilityCollapsed ? "Open sidebar" : "Close sidebar"}
              className={styles.sidebarToggle}
              onClick={() => setUtilityCollapsed((current) => !current)}
              type="button"
            >
              {utilityCollapsed ? ">" : "<"}
            </button> */}
          </div>

          {!utilityCollapsed ? (
            <>
              <div className={styles.utilityConnection}>
                <span className={styles.utilityConnectionDot} />
                <div>
                  <strong>{utilityStatus}</strong>
                  <span>{providerSelectionLocked ? "Reconnect to edit providers" : "Connect Backend to start"}</span>
                </div>
              </div>

              <div className={styles.utilityNav}>
                {SIDEBAR_ITEMS.map((item) => (
                  <div
                    key={item.label}
                    className={`${styles.utilityNavItem} ${item.active ? styles.utilityNavItemActive : ""}`}
                  >
                    <span className={styles.utilityNavMark}>{item.short}</span>
                    <strong>{item.label}</strong>
                  </div>
                ))}
              </div>

              <section className={styles.utilitySection}>
                <div className={styles.utilitySectionHeader}>
                  <span className={styles.sectionEyebrow}>Providers</span>
                  <span className={styles.utilityMiniPill}>{providerSelectionLocked ? "Locked" : "Editable"}</span>
                </div>

                <label className={styles.compactField}>
                  <span>STT</span>
                  <select
                    disabled={providerSelectionLocked}
                    onChange={(event) => setSttProvider(event.target.value as SttProvider)}
                    value={sttProvider}
                  >
                    {availableSttOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className={styles.compactField}>
                  <span>TTS</span>
                  <select
                    disabled={providerSelectionLocked}
                    onChange={(event) => setTtsProvider(event.target.value as TtsProvider)}
                    value={ttsProvider}
                  >
                    {availableTtsOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </section>

              <section className={styles.utilitySection}>
                <div className={styles.utilityMetaRow}>
                  <span>Agent</span>
                  <strong>{selectedAgent?.name ?? "Not selected"}</strong>
                </div>
                <div className={styles.utilityMetaRow}>
                  <span>Room</span>
                  <strong>{currentRoomName}</strong>
                </div>
                <div className={styles.utilityMetaRow}>
                  <span>Mode</span>
                  <strong>{liveModeLabel}</strong>
                </div>
              </section>

              {modeNotice ? <div className={styles.noticeCompact}>{modeNotice}</div> : null}
            </>
          ) : (
            <div className={styles.utilityCollapsedStack}>
              <span className={styles.collapsedBadge} title="Voice chat">
                VC
              </span>
              <span className={styles.collapsedBadge} title={`STT ${sessionSttProvider}`}>
                {shortProviderLabel(sessionSttProvider)}
              </span>
              <span className={styles.collapsedBadge} title={`TTS ${sessionTtsProvider}`}>
                {shortProviderLabel(sessionTtsProvider)}
              </span>
            </div>
          )}
        </aside>

        <aside className={styles.controlSidebar}>
          <div className={styles.controlHeader}>
            <div>
              <span className={styles.sectionEyebrow}>Select Agent</span>
              <strong>{loadingAgents ? "Loading agents" : "Choose an agent"}</strong>
            </div>
            <span className={`${styles.statePill} ${statusClassName}`}>{statusLabel}</span>
          </div>

          {selectedAgent ? (
            <div className={styles.selectionSummary} style={{ "--agent-accent": selectedAgent.accent_color } as CSSProperties}>
              <span className={styles.selectionSummaryName}>{selectedAgent.name}</span>
              <div className={styles.selectionSummaryTools}>
                {selectedAgent.tool_names.map((toolName) => (
                  <span key={toolName} className={styles.selectionSummaryTool}>
                    {toolName}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className={styles.agentListWrap}>
            {loadingAgents ? <div className={styles.compactEmpty}>Loading agents...</div> : null}
            {!loadingAgents && agents.length === 0 ? <div className={styles.compactEmpty}>No agents available.</div> : null}
            {!loadingAgents && agents.length > 0 ? (
              <AgentSelector
                agents={agents}
                disabled={providerSelectionLocked}
                onSelect={setSelectedAgentId}
                selectedAgentId={selectedAgentId}
              />
            ) : null}

            <section className={styles.documentsPanel}>
              <div className={styles.documentsHeader}>
                <span className={styles.sectionEyebrow}>RAG Documents</span>
                <span className={styles.documentsCount}>{documents.length}</span>
              </div>

              <label className={styles.documentUploadLabel}>
                <input
                  accept=".txt,.pdf"
                  className={styles.documentUploadInput}
                  disabled={uploadingDocument}
                  onChange={handleDocumentUpload}
                  type="file"
                />
                {uploadingDocument ? "Uploading..." : "Upload .txt / .pdf"}
              </label>

              {loadingDocuments ? <div className={styles.compactEmpty}>Loading documents...</div> : null}
              {!loadingDocuments && documents.length === 0 ? (
                <div className={styles.compactEmpty}>No uploaded documents yet.</div>
              ) : null}

              {documentsError ? <div className={styles.errorState}>{documentsError}</div> : null}

              {!loadingDocuments && documents.length > 0 ? (
                <div className={styles.documentList}>
                  {documents.map((document) => (
                    <article className={styles.documentItem} key={document.document_id}>
                      <div className={styles.documentMeta}>
                        <strong>{document.filename}</strong>
                        <span>{document.chunk_count} chunks</span>
                        <span>{new Date(document.uploaded_at).toLocaleString()}</span>
                      </div>
                      <button
                        className={styles.documentDeleteButton}
                        onClick={() => void handleDeleteDocument(document.document_id)}
                        type="button"
                      >
                        Delete
                      </button>
                    </article>
                  ))}
                </div>
              ) : null}
            </section>
          </div>

          <SessionControls
            activeSpeakers={voiceSession.activeSpeakers}
            assistantState={voiceSession.assistantState}
            canConnect={Boolean(selectedAgentId)}
            connectionState={voiceSession.connectionState}
            isConnected={voiceSession.isConnected}
            isMuted={voiceSession.isMuted}
            onConnect={handleConnect}
            onDisconnect={voiceSession.disconnect}
            onToggleMute={voiceSession.toggleMute}
          />

          {voiceSession.error ? <div className={styles.errorState}>{voiceSession.error}</div> : null}
          <div className={styles.hiddenAudio} ref={voiceSession.audioContainerRef} />
        </aside>

        <section className={styles.mainPanel}>
          <header className={styles.mainHeader}>
            <div className={styles.headerCenter}>
                <h1 className={styles.mainTitle}>AI Voice Agent</h1>
                <p className={styles.mainSubtitle}>
                Browser-based real-time voice session via LiveKit
                </p>
            </div>

            <span className={styles.messageCounter}>
                {voiceSession.transcripts.length} messages
            </span>
        </header>

          <section className={styles.activityPanel}>
            <div className={styles.activityPanelHeader}>
              <span className={styles.sectionEyebrow}>Audio Activity</span>
              <span className={styles.activityState}>{activityStatus}</span>
            </div>

            <div
              className={styles.waveformShell}
              data-assistant-state={voiceSession.assistantState}
              data-connection-state={voiceSession.connectionState}
            >
              {WAVEFORM_BARS.map((bar) => (
                <span
                  key={bar}
                  className={styles.waveformBar}
                  style={
                    {
                      "--bar-delay": `${bar * 0.06}s`,
                      "--bar-scale": `${0.34 + ((bar % 5) + 1) * 0.12}`
                    } as CSSProperties
                  }
                />
              ))}
            </div>

            <div className={styles.metricGrid}>
              <div className={styles.metricTile}>
                <span>STT</span>
                <strong>{sessionSttProvider}</strong>
              </div>
              <div className={styles.metricTile}>
                <span>TTS</span>
                <strong>{sessionTtsProvider}</strong>
              </div>
              <div className={styles.metricTile}>
                <span>Agent</span>
                <strong>{selectedAgent?.name ?? "Not selected"}</strong>
              </div>
              <div className={styles.metricTile}>
                <span>Room</span>
                <strong>{currentRoomName}</strong>
              </div>
            </div>
          </section>

          <section className={styles.sessionInsights}>
            <div className={styles.sessionInsightsHeader}>
              <span className={styles.sectionEyebrow}>Session Insights</span>
              <strong>Memory + Tools + RAG</strong>
            </div>

            <div className={styles.insightsGrid}>
              <article className={styles.insightCard}>
                <span className={styles.insightTitle}>Recent Transcript</span>
                {recentTranscript.length === 0 ? (
                  <p className={styles.insightEmpty}>No transcript yet.</p>
                ) : (
                  recentTranscript.map((entry) => (
                    <p className={styles.insightLine} key={entry.id}>
                      <strong>{entry.role}:</strong> {entry.text}
                    </p>
                  ))
                )}
              </article>

              <article className={styles.insightCard}>
                <span className={styles.insightTitle}>Tools Called</span>
                {recentToolCalls.length === 0 ? (
                  <p className={styles.insightEmpty}>No tools used in this session.</p>
                ) : (
                  recentToolCalls.map((item) => (
                    <p className={styles.insightLine} key={`${item.createdAt}-${item.name}`}>
                      <strong>{item.name}</strong> {item.resultSummary ? `- ${item.resultSummary}` : ""}
                    </p>
                  ))
                )}
              </article>

              <article className={styles.insightCard}>
                <span className={styles.insightTitle}>Retrieved Chunks</span>
                {recentChunks.length === 0 ? (
                  <p className={styles.insightEmpty}>No document chunks retrieved yet.</p>
                ) : (
                  recentChunks.map((chunk, index) => (
                    <p className={styles.insightLine} key={`${chunk.document_id}-${chunk.chunk_index}-${index}`}>
                      <strong>{chunk.filename}</strong>: {chunk.snippet || chunk.content}
                    </p>
                  ))
                )}
              </article>
            </div>

            {voiceSession.memorySummary ? (
              <p className={styles.memorySummary}>
                <strong>Memory Summary:</strong> {voiceSession.memorySummary}
              </p>
            ) : null}
          </section>

          <TranscriptPanel agentName={selectedAgent?.name ?? "Assistant"} entries={voiceSession.transcripts} />
        </section>
      </section>
    </main>
  );
}
