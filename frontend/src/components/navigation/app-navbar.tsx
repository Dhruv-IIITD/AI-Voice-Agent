"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { BackendStatusBadge } from "@/components/status/backend-status-badge";
import { useVoicePlatform } from "@/features/voice/context/voice-platform-context";

import styles from "./app-navbar.module.css";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/agent", label: "Voice Agent" },
  { href: "/documents", label: "Documents" },
  { href: "/metrics", label: "Metrics" },
  { href: "/about", label: "Architecture" }
];

function isActivePath(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(href);
}

export function AppNavbar() {
  const pathname = usePathname();
  const { backendStatus } = useVoicePlatform();

  return (
    <header className={styles.navbarWrap}>
      <div className={styles.navbar}>
        <Link className={styles.brand} href="/">
          <span className={styles.brandMark}>AV</span>
          <div className={styles.brandCopy}>
            <strong>Agentic Voice AI</strong>
            <span>Real-time voice + RAG + observability</span>
          </div>
        </Link>

        <nav className={styles.links}>
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              className={`${styles.link} ${isActivePath(pathname, link.href) ? styles.linkActive : ""}`}
              href={link.href}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className={styles.statusWrap}>
          <BackendStatusBadge status={backendStatus} />
        </div>
      </div>
    </header>
  );
}
