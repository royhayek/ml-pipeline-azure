import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import type { Plugin } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'

// ---------------------------------------------------------------------------
// Mock /api/recent for local dev — no Azure Functions needed
// ---------------------------------------------------------------------------
function mockApiPlugin(): Plugin {
  return {
    name: 'mock-api',
    configureServer(server) {
      server.middlewares.use(
        '/api/recent',
        (_req: IncomingMessage, res: ServerResponse) => {
          const now = Date.now()
          const records = Array.from({ length: 12 }, (_, i) => ({
            id:               `blob-${i}`,
            blob_name:        `input/weather_batch_${String(i + 1).padStart(2, '0')}.csv`,
            timestamp:        new Date(now - i * 4 * 60_000).toISOString(),
            model_version:    '1.0.0',
            record_count:     Math.floor(Math.random() * 80) + 20,
            latency_ms:       Math.round(200 + Math.random() * 800),
            confidence_score: parseFloat((14 + Math.random() * 12).toFixed(2)),
          }))
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ data: records, count: records.length }))
        },
      )
    },
  }
}

// ---------------------------------------------------------------------------
export default defineConfig({
  plugins: [react(), mockApiPlugin()],

  server: {
    port: 5173,
    // Proxy to real Functions only when explicitly set via env
    ...(process.env.FUNCTIONS_URL
      ? { proxy: { '/api': process.env.FUNCTIONS_URL } }
      : {}),
  },

  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor':  ['react', 'react-dom'],
          'charts-vendor': ['recharts'],
          'icons-vendor':  ['lucide-react'],
        },
      },
    },
  },
})
