import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/chat': 'http://localhost:8002',
      '/tts': 'http://localhost:8002',
      '/session': 'http://localhost:8002',
      '/health': 'http://localhost:8002',
    }
  }
})
