"use client";

import { useEffect, useMemo, useState } from "react";

import { MetricsCards, type MetricsSnapshot } from "@/components/metrics/metrics-cards";
import { BackendStatusBanner } from "@/components/status/backend-status-banner";
import { useVoicePlatform } from "@/features/voice/context/voice-platform-context";
import { fetchBackendMetrics, type MetricsResponse } from "@/features/voice/lib/api-client";
import { toUserFriendlyBackendError } from "@/features/voice/lib/error-utils";
import { buildSessionMetricsSnapshot } from "@/features/voice/lib/session-metrics";

import styles from "./metrics-page.module.css";

function hasSessionEvents(metrics: MetricsSnapshot) {
  return (
    metrics.totalLatencyMs !== null ||
    metrics.sttLatencyMs !== null ||
    metrics.llmLatencyMs !== null ||
    metrics.ttsLatencyMs !== null ||
    metrics.toolsCalled.length > 0 ||
    metrics.retrievedChunksCount > 0
  );
}

function mapBackendMetrics(payload: MetricsResponse): MetricsSnapshot {
  return {
    totalLatencyMs: payload.total_latency_ms ?? null,
    sttLatencyMs: payload.stt_latency_ms ?? null,
    ragRetrievalLatencyMs: payload.rag_retrieval_latency_ms ?? null,
    toolExecutionLatencyMs: payload.tool_execution_latency_ms ?? null,
    llmLatencyMs: payload.llm_latency_ms ?? null,
    ttsLatencyMs: payload.tts_latency_ms ?? null,
    selectedSttProvider: payload.selected_stt_provider ?? null,
    selectedTtsProvider: payload.selected_tts_provider ?? null,
    toolsCalled: payload.tools_called ?? [],
    retrievedChunksCount: payload.retrieved_chunks_count ?? 0
  };
}

export default function MetricsPage() {
  const { backendStatus, backendMessage, voiceSession } = useVoicePlatform();
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [sourceLabel, setSourceLabel] = useState("No metrics source");
  const [error, setError] = useState<string | null>(null);
  const [backendEndpointUnavailable, setBackendEndpointUnavailable] = useState(false);

  const fallbackSessionMetrics = useMemo(
    () =>
      buildSessionMetricsSnapshot({
        transcripts: voiceSession.transcripts,
        session: voiceSession.session,
        toolCalls: voiceSession.toolCalls,
        retrievedChunks: voiceSession.retrievedChunks
      }),
    [voiceSession.retrievedChunks, voiceSession.session, voiceSession.toolCalls, voiceSession.transcripts]
  );

  useEffect(() => {
    let active = true;

    async function loadMetrics() {
      if (!backendEndpointUnavailable) {
        try {
          const backendMetrics = await fetchBackendMetrics();
          if (!active) {
            return;
          }
          if (backendMetrics) {
            setMetrics(mapBackendMetrics(backendMetrics));
            setSourceLabel("Backend metrics endpoint");
            setError(null);
            return;
          }
          setBackendEndpointUnavailable(true);
        } catch (caughtError) {
          if (!active) {
            return;
          }
          setError(toUserFriendlyBackendError(caughtError, "Unable to load backend metrics endpoint."));
          setBackendEndpointUnavailable(true);
        }
      }

      if (!active) {
        return;
      }

      if (hasSessionEvents(fallbackSessionMetrics)) {
        setMetrics(fallbackSessionMetrics);
        setSourceLabel("Live session events in frontend");
      } else {
        setMetrics(null);
        setSourceLabel("No metrics source");
      }
    }

    void loadMetrics();
    return () => {
      active = false;
    };
  }, [backendEndpointUnavailable, fallbackSessionMetrics]);

  return (
    <main className="pageShell">
      {(backendStatus === "preview" || backendStatus === "unavailable") && (
        <BackendStatusBanner message={backendMessage} status={backendStatus} />
      )}

      <header className="pageHeader">
        <p className="eyebrow">Observability</p>
        <h1 className="pageTitle">Latency Metrics</h1>
        <p className="pageSubtitle">
          Inspect latency across STT, retrieval, tools, LLM, and TTS for real-time voice sessions.
        </p>
      </header>

      <section className={`sectionCard ${styles.section}`}>
        <h2 className="sectionTitle">Session Metrics</h2>
        <p className={styles.source}>Current source: {sourceLabel}</p>
        {error ? <p className={styles.errorCard}>{error}</p> : null}
        <MetricsCards metrics={metrics} sourceLabel={sourceLabel} />
      </section>
    </main>
  );
}
