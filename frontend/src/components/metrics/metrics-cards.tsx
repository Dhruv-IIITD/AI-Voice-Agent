import { EmptyState } from "@/components/common/empty-state";

import styles from "./metrics-cards.module.css";

export interface MetricsSnapshot {
  totalLatencyMs: number | null;
  sttLatencyMs: number | null;
  ragRetrievalLatencyMs: number | null;
  toolExecutionLatencyMs: number | null;
  llmLatencyMs: number | null;
  ttsLatencyMs: number | null;
  selectedSttProvider: string | null;
  selectedTtsProvider: string | null;
  toolsCalled: string[];
  retrievedChunksCount: number;
}

interface MetricsCardsProps {
  metrics: MetricsSnapshot | null;
  sourceLabel: string;
}

function formatMs(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return "--";
  }
  return `${Math.round(value)} ms`;
}

function formatList(values: string[]) {
  if (values.length === 0) {
    return "None";
  }
  return values.join(", ");
}

export function MetricsCards({ metrics, sourceLabel }: MetricsCardsProps) {
  if (!metrics) {
    return (
      <EmptyState
        title="Start a voice session to collect latency metrics."
        description="Observability cards will populate after transcript, tool, and retrieval events are captured."
      />
    );
  }

  return (
    <section className={styles.shell}>
      <div className={styles.grid}>
        <article className={styles.card}>
          <p className={styles.label}>Total Latency</p>
          <p className={styles.value}>{formatMs(metrics.totalLatencyMs)}</p>
          <p className={styles.subValue}>End-to-end observed in frontend session</p>
        </article>
        <article className={styles.card}>
          <p className={styles.label}>STT Latency</p>
          <p className={styles.value}>{formatMs(metrics.sttLatencyMs)}</p>
          <p className={styles.subValue}>Speech-to-text turn timing</p>
        </article>
        <article className={styles.card}>
          <p className={styles.label}>RAG Retrieval</p>
          <p className={styles.value}>{formatMs(metrics.ragRetrievalLatencyMs)}</p>
          <p className={styles.subValue}>Chunk retrieval stage</p>
        </article>
        <article className={styles.card}>
          <p className={styles.label}>Tool Execution</p>
          <p className={styles.value}>{formatMs(metrics.toolExecutionLatencyMs)}</p>
          <p className={styles.subValue}>Tool runtime duration</p>
        </article>
        <article className={styles.card}>
          <p className={styles.label}>LLM Latency</p>
          <p className={styles.value}>{formatMs(metrics.llmLatencyMs)}</p>
          <p className={styles.subValue}>Model generation latency</p>
        </article>
        <article className={styles.card}>
          <p className={styles.label}>TTS Latency</p>
          <p className={styles.value}>{formatMs(metrics.ttsLatencyMs)}</p>
          <p className={styles.subValue}>Speech synthesis timing</p>
        </article>
      </div>

      <article className={styles.tableCard}>
        <div className={styles.row}>
          <p className={styles.rowLabel}>Selected STT Provider</p>
          <p className={styles.rowValue}>{metrics.selectedSttProvider ?? "--"}</p>
        </div>
        <div className={styles.row}>
          <p className={styles.rowLabel}>Selected TTS Provider</p>
          <p className={styles.rowValue}>{metrics.selectedTtsProvider ?? "--"}</p>
        </div>
        <div className={styles.row}>
          <p className={styles.rowLabel}>Tools Called</p>
          <p className={styles.rowValue}>{formatList(metrics.toolsCalled)}</p>
        </div>
        <div className={styles.row}>
          <p className={styles.rowLabel}>Retrieved Chunks Count</p>
          <p className={styles.rowValue}>{metrics.retrievedChunksCount}</p>
        </div>
        <div className={styles.row}>
          <p className={styles.rowLabel}>Data Source</p>
          <p className={styles.rowValue}>{sourceLabel}</p>
        </div>
      </article>
    </section>
  );
}
