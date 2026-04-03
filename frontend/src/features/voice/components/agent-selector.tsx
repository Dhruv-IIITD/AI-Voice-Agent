import { type CSSProperties } from "react";

import type { AgentSummary } from "../types";

import styles from "./voice-workspace.module.css";

interface AgentSelectorProps {
  agents: AgentSummary[];
  selectedAgentId: string;
  onSelect: (agentId: string) => void;
  disabled?: boolean;
}

function getAgentGlyph(agentId: string) {
  if (agentId === "support") {
    return "SU";
  }

  if (agentId === "scheduler") {
    return "TM";
  }

  if (agentId === "calculator") {
    return "FX";
  }

  return agentId.slice(0, 2).toUpperCase();
}

export function AgentSelector({ agents, selectedAgentId, onSelect, disabled }: AgentSelectorProps) {
  return (
    <div className={styles.agentGrid}>
      {agents.map((agent) => {
        const selected = agent.id === selectedAgentId;

        return (
          <button
            key={agent.id}
            className={`${styles.agentCard} ${selected ? styles.agentCardSelected : ""}`}
            disabled={disabled}
            onClick={() => onSelect(agent.id)}
            style={{ "--agent-accent": agent.accent_color } as CSSProperties}
            type="button"
          >
            <div className={styles.agentCardTopRow}>
              <span className={styles.agentGlyph}>{getAgentGlyph(agent.id)}</span>
              <div className={styles.agentCardHeading}>
                <strong>{agent.name}</strong>
                <span className={styles.agentCardDescription}>{agent.description}</span>
              </div>
              <span className={styles.agentSelectionState}>{selected ? "Selected" : "Ready"}</span>
            </div>

            <div className={styles.pillRow}>
              {agent.tool_names.map((toolName) => (
                <span key={toolName} className={styles.pill}>
                  {toolName}
                </span>
              ))}
            </div>
          </button>
        );
      })}
    </div>
  );
}
