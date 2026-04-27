import { useEffect, useRef } from "react";

import { EmptyState } from "@/components/common/empty-state";
import type { TranscriptEntry } from "@/features/voice/types";

import styles from "./transcript-panel.module.css";

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
  agentName: string;
}

function speakerLabel(role: TranscriptEntry["role"], agentName: string) {
  if (role === "assistant") {
    return agentName;
  }
  if (role === "tool") {
    return "Tool";
  }
  return "You";
}

function entryClass(role: TranscriptEntry["role"]) {
  if (role === "assistant") {
    return styles.entryAssistant;
  }
  if (role === "tool") {
    return styles.entryTool;
  }
  return styles.entryUser;
}

export function TranscriptPanel({ entries, agentName }: TranscriptPanelProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h3 className={styles.title}>Transcript</h3>
        <span className={styles.count}>{entries.length} messages</span>
      </header>

      <div className={styles.list}>
        {entries.length === 0 ? (
          <EmptyState
            title="No transcript yet."
            description="Start a voice session to see live user speech, agent replies, and tool events."
          />
        ) : null}

        {entries.map((entry) => (
          <article
            key={entry.id}
            className={`${styles.entry} ${entryClass(entry.role)} ${entry.isFinal ? "" : styles.entryStreaming}`}
          >
            <div className={styles.entryHeader}>
              <span className={styles.speaker}>{speakerLabel(entry.role, agentName)}</span>
              {entry.provider ? <span className={styles.meta}>{entry.provider}</span> : null}
              {entry.stt_latency_ms ? <span className={styles.meta}>STT {entry.stt_latency_ms}ms</span> : null}
              {entry.llm_latency_ms ? <span className={styles.meta}>LLM {entry.llm_latency_ms}ms</span> : null}
              {entry.tts_latency_ms ? <span className={styles.meta}>TTS {entry.tts_latency_ms}ms</span> : null}
              {!entry.isFinal ? <span className={styles.meta}>Streaming</span> : null}
            </div>
            <p className={styles.body}>{entry.text}</p>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
