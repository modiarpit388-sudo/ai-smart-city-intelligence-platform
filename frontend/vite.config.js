import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development the React app runs on :5173 and proxies API calls to Flask on :5000.
// `npm run build` writes the production bundle straight into ../backend/static so that
// Flask can serve the whole platform from a single port.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:5000' } },
  build: { outDir: '../backend/static', emptyOutDir: true, chunkSizeWarningLimit: 1500 },
})
