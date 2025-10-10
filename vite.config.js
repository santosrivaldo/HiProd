
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Flags para rodar por trás de proxy/HTTPS
const IS_PROXY = process.env.VITE_BEHIND_PROXY === '1' || process.env.BEHIND_PROXY === '1'
const PUBLIC_HOST = process.env.VITE_PUBLIC_HOST || '192.241.155.236'

// Configurar HMR somente quando estiver atrás de proxy HTTPS
const hmrConfig = IS_PROXY
  ? { protocol: 'ws', host: PUBLIC_HOST, clientPort: 80 }
  : undefined

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    allowedHosts: [PUBLIC_HOST, 'hiprod.grupohi.com.br', '192.241.155.236', '.replit.dev', 'localhost'],
    hmr: hmrConfig
  }
})
