import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";

import { AppNavbar } from "@/components/navigation/app-navbar";
import { AppProviders } from "@/components/providers/app-providers";

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
  title: "Agentic Voice AI",
  description:
    "Real-Time Agentic Voice AI platform for document-grounded voice conversations with tools, memory, and latency observability."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${dmSans.variable} ${jetBrainsMono.variable}`}>
        <AppProviders>
          <div className="appBackdrop">
            <AppNavbar />
            <div className="pageFrame">{children}</div>
          </div>
        </AppProviders>
      </body>
    </html>
  );
}
