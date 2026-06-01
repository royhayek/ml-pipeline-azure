import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import type { IncomingMessage, ServerResponse } from "node:http";

// ---------------------------------------------------------------------------
// Default backend: live Azure Function App.
// Override with VITE_API_URL env var, or with USE_MOCK=1 for offline dev.
// ---------------------------------------------------------------------------
const LIVE_API = "https://func-mlpipeline-aa8229.azurewebsites.net";

function mockApiPlugin(): Plugin {
  return {
    name: "mock-api",
    configureServer(server) {
      server.middlewares.use("/api/recent", (_req: IncomingMessage, res: ServerResponse) => {
        const now = Date.now();
        const records = Array.from({ length: 12 }, (_, i) => ({
          id: `blob-${i}`,
          blob_name: `input/weather_batch_${String(i + 1).padStart(2, "0")}.csv`,
          timestamp: new Date(now - i * 4 * 60_000).toISOString(),
          model_version: i % 5 === 0 ? "2.0.0" : "1.0.0",
          record_count: Math.floor(Math.random() * 80) + 20,
          latency_ms: Math.round(200 + Math.random() * 800),
          confidence_score: parseFloat((14 + Math.random() * 12).toFixed(2)),
          hf_summary: i % 2 === 0
            ? "Mild conditions with moderate humidity and light wind across the analyzed batch."
            : "",
        }));
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify({
          data: records,
          count: records.length,
          meta: { read_region: "Switzerland North", read_latency_ms: 23.4 },
        }));
      });
    },
  };
}

const API_TARGET = process.env.VITE_API_URL || LIVE_API;
const USE_MOCK = process.env.USE_MOCK === "1";

export default defineConfig({
  plugins: [react(), ...(USE_MOCK ? [mockApiPlugin()] : [])],
  server: {
    port: 5173,
    proxy: USE_MOCK
      ? undefined
      : {
          "/api": {
            target: API_TARGET,
            changeOrigin: true,
            secure: true,
          },
        },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          "charts-vendor": ["recharts"],
          "icons-vendor": ["lucide-react"],
        },
      },
    },
  },
});
