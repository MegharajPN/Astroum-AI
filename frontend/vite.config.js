import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev-time proxy so the browser talks to Django on the same origin.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
