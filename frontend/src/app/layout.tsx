import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/layout/site-header";

import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans"
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono"
});

export const metadata: Metadata = {
  title: "VoiceAI Control Room",
  description:
    "Browser-based voice AI console with LiveKit transport, switchable speech providers, and specialized agents."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${dmSans.variable} ${jetBrainsMono.variable}`}>
        <div className="appBackdrop">
          <SiteHeader />
          <div className="pageFrame">{children}</div>
        </div>
      </body>
    </html>
  );
}
