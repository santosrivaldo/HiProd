
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: ['30639375-c8ee-4839-b62a-4cdd5cf7f23e-00-29im557edjni.worf.replit.dev', '.replit.dev']
  }
})
