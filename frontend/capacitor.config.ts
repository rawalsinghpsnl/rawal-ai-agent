import type { CapacitorConfig } from "@capacitor/cli";

// rawal-ai-agent — Capacitor Android shell.
// SPDX-License-Identifier: MIT
// Production-hardened: no cleartext, no mixed content, no wildcard navigation,
// no WebView debugging. For local dev against http://<lan-ip>:8000, temporarily
// set cleartext:true + allowNavigation to that exact origin — never ship "*" .
const config: CapacitorConfig = {
  appId: "com.rawal.ai.agent",
  appName: "rawal-ai-agent",
  webDir: "dist",
  server: {
    androidScheme: "https",
    cleartext: false,
    allowNavigation: [],
  },
  plugins: {
    CapacitorHttp: {
      enabled: true,
    },
    Filesystem: {
      // Enables saving files to mobile external storage (Documents/RawalAiAgent)
    },
  },
  android: {
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: false,
  },
};

export default config;
