import type { SttProvider, TtsProvider } from "@/features/voice/types";

import styles from "./provider-settings-card.module.css";

interface ProviderSettingsCardProps {
  sttProvider: SttProvider;
  ttsProvider: TtsProvider;
  sttOptions: Array<{ label: string; value: SttProvider }>;
  ttsOptions: Array<{ label: string; value: TtsProvider }>;
  locked: boolean;
  onSttChange: (provider: SttProvider) => void;
  onTtsChange: (provider: TtsProvider) => void;
}

export function ProviderSettingsCard({
  sttProvider,
  ttsProvider,
  sttOptions,
  ttsOptions,
  locked,
  onSttChange,
  onTtsChange
}: ProviderSettingsCardProps) {
  return (
    <section className={styles.card}>
      <div>
        <h3 className={styles.title}>Provider Settings</h3>
        <p className={styles.description}>
          Select speech providers before connecting. Provider selection is locked while a live session is active.
        </p>
      </div>

      <div className={styles.fields}>
        <label className={styles.field}>
          <span className={styles.label}>STT Provider</span>
          <select
            className={styles.select}
            disabled={locked}
            onChange={(event) => onSttChange(event.target.value as SttProvider)}
            value={sttProvider}
          >
            {sttOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span className={styles.label}>TTS Provider</span>
          <select
            className={styles.select}
            disabled={locked}
            onChange={(event) => onTtsChange(event.target.value as TtsProvider)}
            value={ttsProvider}
          >
            {ttsOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className={styles.note}>{locked ? "Disconnect to change providers." : "You can change providers now."}</p>
    </section>
  );
}
