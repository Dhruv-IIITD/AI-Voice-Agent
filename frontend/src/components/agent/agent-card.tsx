import type { CSSProperties } from "react";

import type { AgentProfile } from "@/features/voice/lib/agent-profiles";

import styles from "./agent-card.module.css";

interface AgentCardProps {
  agent: AgentProfile;
  selected: boolean;
  disabled?: boolean;
  onSelect: (agentId: string) => void;
}

export function AgentCard({ agent, selected, disabled, onSelect }: AgentCardProps) {
  return (
    <button
      className={`${styles.card} ${selected ? styles.selected : ""}`}
      disabled={disabled}
      onClick={() => onSelect(agent.id)}
      style={{ "--agent-accent": agent.accent_color } as CSSProperties}
      type="button"
    >
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <h3 className={styles.title}>{agent.name}</h3>
          <p className={styles.description}>{agent.description}</p>
        </div>
        <span className={styles.state}>{selected ? "Selected" : "Available"}</span>
      </div>

      <div className={styles.toolList}>
        {agent.suggested_tools.map((tool) => (
          <span key={tool} className={styles.tool}>
            {tool}
          </span>
        ))}
      </div>
    </button>
  );
}
