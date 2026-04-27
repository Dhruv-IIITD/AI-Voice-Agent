"use client";

import type { PropsWithChildren } from "react";

import { VoicePlatformProvider } from "@/features/voice/context/voice-platform-context";

export function AppProviders({ children }: PropsWithChildren) {
  return <VoicePlatformProvider>{children}</VoicePlatformProvider>;
}
