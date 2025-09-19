
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Flags para rodar por trás de proxy/HTTPS
const IS_PROXY = process.env.VITE_BEHIND_PROXY === '1' || process.env.BEHIND_PROXY === '1'
const PUBLIC_HOST = process.env.VITE_PUBLIC_HOST || 'hiprod.grupohi.com.br'

// Configurar HMR somente quando estiver atrás de proxy HTTPS
const hmrConfig = IS_PROXY
  ? { protocol: 'wss', host: PUBLIC_HOST, clientPort: 443 }
  : undefined

export default defineConfig({
  plugins: [react()],
  server: {
    host: 'hiprod.grupohi.com.br',
    port: 5000,
    strictPort: true,
    allowedHosts: [PUBLIC_HOST, 'hiprod.grupohi.com.br', '.replit.dev', 'localhost'],
    hmr: hmrConfig
  }
})
