import Link from "next/link";

import styles from "./site-header.module.css";

export function SiteHeader() {
  return (
    <header className={styles.headerShell}>
      <div className={styles.headerInner}>
        <Link className={styles.brand} href="/">
          <span className={styles.brandMark}>VA</span>
          <div className={styles.brandCopy}>
            <strong>VoiceAI Control Room</strong>
            <span>Realtime voice agents with swap-ready speech providers</span>
          </div>
        </Link>
        <div className={styles.headerMeta}>
          <span className={styles.primaryChip}>Browser voice workspace</span>
          <span className={styles.secondaryChip}>LiveKit transport</span>
        </div>
      </div>
    </header>
  );
}
