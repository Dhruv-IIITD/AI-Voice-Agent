"use client";

import Link from "next/link";

import { AgentCard } from "@/components/agent/agent-card";
import { ProviderSettingsCard } from "@/components/agent/provider-settings-card";
import { SessionInsightPanel } from "@/components/agent/session-insight-panel";
import { SessionStatusCard } from "@/components/agent/session-status-card";
import { TranscriptPanel } from "@/components/agent/transcript-panel";
import { VoiceGuideCard } from "@/components/agent/voice-guide-card";
import { VoiceSessionControls } from "@/components/agent/voice-session-controls";
import { EmptyState } from "@/components/common/empty-state";
import { BackendStatusBanner } from "@/components/status/backend-status-banner";
import { useVoicePlatform } from "@/features/voice/context/voice-platform-context";
import { toUserFriendlyBackendError } from "@/features/voice/lib/error-utils";

import styles from "./agent-page.module.css";

const BACKEND_STATUS_LABELS = {
  connected: "Connected",
  unavailable: "Unavailable",
  preview: "Frontend Preview Mode",
  checking: "Checking"
} as const;

const VOICE_STATUS_LABELS = {
  idle: "Inactive",
  connecting: "Connecting",
  connected: "Active",
  error: "Unavailable"
} as const;

export default function AgentPage() {
  const {
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
    connectSession,
    disconnectSession,
    toggleMute,
    voiceSession
  } = useVoicePlatform();

  const agentError = agentsError ? toUserFriendlyBackendError(agentsError, "Unable to load agent profiles.") : null;
  const sessionError = voiceSession.error
    ? toUserFriendlyBackendError(voiceSession.error, "Unable to start voice session.")
    : null;

  const selectedSttProvider = voiceSession.session?.selected_stt_provider ?? sttProvider;
  const selectedTtsProvider = voiceSession.session?.selected_tts_provider ?? ttsProvider;

  return (
    <main className="pageShell">
      {(backendStatus === "preview" || backendStatus === "unavailable") && (
        <BackendStatusBanner message={backendMessage} status={backendStatus} />
      )}

      <header className="pageHeader">
        <p className="eyebrow">Voice Workspace</p>
        <h1 className="pageTitle">Main Voice Agent</h1>
        <p className="pageSubtitle">
          Run real-time voice sessions with RAG-aware agents, inspect transcript and tool activity, and monitor
          session-level context.
        </p>
      </header>

      <section className={styles.layout}>
        <aside className={styles.sidebar}>
          <VoiceSessionControls
            assistantState={voiceSession.assistantState}
            canConnect={Boolean(selectedAgent)}
            connectionState={voiceSession.connectionState}
            isConnected={voiceSession.isConnected}
            isMuted={voiceSession.isMuted}
            onConnect={connectSession}
            onDisconnect={disconnectSession}
            onToggleMute={toggleMute}
          />

          <SessionStatusCard
            backendStatus={BACKEND_STATUS_LABELS[backendStatus]}
            selectedAgentName={selectedAgent?.name ?? "Not selected"}
            selectedSttProvider={selectedSttProvider}
            selectedTtsProvider={selectedTtsProvider}
            voiceStatus={VOICE_STATUS_LABELS[voiceSession.connectionState]}
          />

          <ProviderSettingsCard
            locked={providerSelectionLocked}
            onSttChange={setSttProvider}
            onTtsChange={setTtsProvider}
            sttOptions={availableSttOptions}
            sttProvider={sttProvider}
            ttsOptions={availableTtsOptions}
            ttsProvider={ttsProvider}
          />

          <VoiceGuideCard />

          <article className={styles.docLinkCard}>
            <p className={styles.docLinkText}>
              Document upload moved to the dedicated Knowledge Base page for cleaner workflow.
            </p>
            <Link className={`secondaryAction ${styles.docLinkButton}`} href="/documents">
              Go to Documents
            </Link>
          </article>
        </aside>

        <div className={styles.mainColumn}>
          <section className={styles.agentSelectionCard}>
            <div>
              <h2 className={styles.agentSelectionTitle}>Choose Specialized Agent</h2>
              <p className={styles.agentSelectionSubtitle}>
                Select the best profile for your conversation before starting a voice session.
              </p>
            </div>

            {agentsLoading ? (
              <EmptyState title="Loading agents..." description="Fetching available agent profiles from backend." />
            ) : null}

            {!agentsLoading && agents.length === 0 ? (
              <EmptyState title="No agents available." description="No voice agents were returned by the backend." />
            ) : null}

            {!agentsLoading && agents.length > 0 ? (
              <div className={styles.agentGrid}>
                {agents.map((agent) => (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    disabled={providerSelectionLocked}
                    onSelect={setSelectedAgentId}
                    selected={agent.id === selectedAgentId}
                  />
                ))}
              </div>
            ) : null}
          </section>

          {agentError ? <p className={styles.errorCard}>{agentError}</p> : null}
          {sessionError ? <p className={styles.errorCard}>{sessionError}</p> : null}

          <SessionInsightPanel
            memorySummary={voiceSession.memorySummary}
            retrievedChunks={voiceSession.retrievedChunks}
            toolCalls={voiceSession.toolCalls}
            transcripts={voiceSession.transcripts}
          />

          <TranscriptPanel agentName={selectedAgent?.name ?? "Agent"} entries={voiceSession.transcripts} />
        </div>
      </section>
      <div className={styles.hiddenAudio} ref={voiceSession.audioContainerRef} />
    </main>
  );
}
