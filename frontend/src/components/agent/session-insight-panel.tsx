import type { RetrievedChunk, ToolCallEntry, TranscriptEntry } from "@/features/voice/types";

import { EmptyState } from "../common/empty-state";
import styles from "./session-insight-panel.module.css";

interface SessionInsightPanelProps {
  transcripts: TranscriptEntry[];
  toolCalls: ToolCallEntry[];
  retrievedChunks: RetrievedChunk[];
  memorySummary: string;
}

export function SessionInsightPanel({
  transcripts,
  toolCalls,
  retrievedChunks,
  memorySummary
}: SessionInsightPanelProps) {
  const recentTurns = [...transcripts].reverse().slice(0, 6);
  const recentTools = [...toolCalls].reverse().slice(0, 6);
  const chunks = retrievedChunks.slice(0, 6);

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>Session Insights</h3>
          <p className={styles.subtitle}>Memory summary, tools called, and retrieved RAG chunks</p>
        </div>
      </header>

      <div className={styles.grid}>
        <article className={styles.card}>
          <h4 className={styles.cardTitle}>Recent Turns</h4>
          {recentTurns.length === 0 ? (
            <p className={styles.line}>No conversation turns yet.</p>
          ) : (
            recentTurns.map((entry) => (
              <p className={styles.line} key={entry.id}>
                <strong>{entry.role}:</strong> {entry.text}
              </p>
            ))
          )}
        </article>

        <article className={styles.card}>
          <h4 className={styles.cardTitle}>Tools Called</h4>
          {recentTools.length === 0 ? (
            <p className={styles.line}>No tools called yet.</p>
          ) : (
            recentTools.map((tool) => (
              <p className={styles.line} key={`${tool.createdAt}-${tool.name}`}>
                <strong>{tool.name}</strong> {tool.resultSummary ? `- ${tool.resultSummary}` : ""}
              </p>
            ))
          )}
        </article>

        <article className={styles.card}>
          <h4 className={styles.cardTitle}>Retrieved Chunks</h4>
          {chunks.length === 0 ? (
            <p className={styles.line}>No RAG chunks retrieved yet.</p>
          ) : (
            chunks.map((chunk, index) => (
              <p className={styles.line} key={`${chunk.document_id}-${chunk.chunk_index}-${index}`}>
                <strong>{chunk.filename}</strong>: {chunk.snippet || chunk.content}
              </p>
            ))
          )}
        </article>
      </div>

      {memorySummary ? (
        <p className={styles.summary}>
          <strong>Memory Summary:</strong> {memorySummary}
        </p>
      ) : (
        <EmptyState
          title="Session memory will appear here."
          description="Ask a few follow-up questions in the same voice session to build a running memory summary."
        />
      )}
    </section>
  );
}
