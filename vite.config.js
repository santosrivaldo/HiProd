
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Flags para rodar por trás de proxy/HTTPS
const IS_PROXY = process.env.VITE_BEHIND_PROXY === '1' || process.env.BEHIND_PROXY === '1'
const PUBLIC_HOST = process.env.VITE_PUBLIC_HOST || '192.241.155.236'

// Configurar HMR para produção IP (HTTP)
const hmrConfig = IS_PROXY
  ? { protocol: 'ws', host: PUBLIC_HOST, clientPort: 8010 }
  : undefined

export default defineConfig({
  plugins: [
    react({
      jsxRuntime: 'automatic' // Usar JSX transform automático
    })
  ],
  resolve: {
    dedupe: ['react', 'react-dom'], // Garantir que há apenas uma cópia do React
    alias: {
      'react': require.resolve('react'),
      'react-dom': require.resolve('react-dom')
    }
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime']
  },
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    allowedHosts: [PUBLIC_HOST, 'hiprod.grupohi.com.br', '192.241.155.236', '.replit.dev', 'localhost'],
    hmr: hmrConfig
  }
})
