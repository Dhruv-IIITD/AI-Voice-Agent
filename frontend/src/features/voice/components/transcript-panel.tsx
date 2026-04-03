import type { TranscriptEntry } from "../types";

import styles from "./voice-workspace.module.css";

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
  agentName: string;
}

function roleClassName(role: TranscriptEntry["role"]) {
  if (role === "assistant") {
    return styles.transcriptBubbleAssistant;
  }

  if (role === "tool") {
    return styles.transcriptBubbleTool;
  }

  return styles.transcriptBubbleUser;
}

function roleLabel(role: TranscriptEntry["role"], agentName: string) {
  if (role === "assistant") {
    return agentName;
  }

  if (role === "tool") {
    return "Tool";
  }

  return "You";
}

export function TranscriptPanel({ entries, agentName }: TranscriptPanelProps) {
  return (
    <section className={styles.transcriptPanel}>
      <div className={styles.transcriptPanelHeader}>
        <div>
          <span className={styles.sectionEyebrow}>Transcript</span>
          <strong>Conversation</strong>
        </div>
        <span className={styles.transcriptPanelCount}>{entries.length} items</span>
      </div>

      <div className={styles.transcriptList}>
        {entries.length === 0 ? (
          <div className={styles.transcriptEmpty}>No transcript yet. Start a session to see the conversation.</div>
        ) : null}

        {entries.map((entry) => (
          <article
            key={entry.id}
            className={`${styles.transcriptBubble} ${roleClassName(entry.role)} ${
              entry.isFinal ? "" : styles.transcriptBubbleDraft
            }`}
          >
            <div className={styles.transcriptBubbleHeader}>
              <span className={styles.transcriptBubbleTitle}>{roleLabel(entry.role, agentName)}</span>
              <div className={styles.transcriptBubbleMeta}>
                {entry.provider ? <span>{entry.provider}</span> : null}
                {!entry.isFinal ? <span className={styles.transcriptDraftPill}>Streaming</span> : null}
              </div>
            </div>

            <p className={styles.transcriptBubbleBody}>{entry.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
