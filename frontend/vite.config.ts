import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// rawal-ai-agent — Vite config.
// VITE_API_URL is the production backend origin (Render). VITE_BACKEND_URL is the local dev proxy target.
const backend = process.env.VITE_BACKEND_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: backend, changeOrigin: true, ws: true },
    },
  },
  preview: {
    host: true,
    port: 4173,
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          editor: ["@monaco-editor/react"],
          terminal: ["@xterm/xterm", "@xterm/addon-fit", "@xterm/addon-web-links"],
          markdown: ["react-markdown", "remark-gfm", "rehype-highlight"],
        },
      },
    },
  },
});
