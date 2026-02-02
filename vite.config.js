
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

// Plugin para ignorar arquivos .git e outros arquivos do sistema
const ignoreSystemFiles = () => {
  return {
    name: 'ignore-system-files',
    resolveId(id) {
      // Ignorar arquivos do Git e outros arquivos do sistema
      if (
        id.includes('.git') || 
        id.includes('/.git/') || 
        id.includes('\\.git\\') ||
        id.includes('/proc/') ||
        id.includes('/sys/') ||
        id.includes('/etc/') ||
        id.includes('/usr/') ||
        id.includes('/var/')
      ) {
        return { id: 'virtual:system-ignore', external: true }
      }
      return null
    },
    load(id) {
      // Ignorar arquivos do Git e outros arquivos do sistema
      if (
        id.includes('.git') || 
        id.includes('/.git/') || 
        id.includes('\\.git\\') ||
        id.includes('/proc/') ||
        id.includes('/sys/') ||
        id.includes('/etc/') ||
        id.includes('/usr/') ||
        id.includes('/var/')
      ) {
        return 'export default {}'
      }
      return null
    },
    configureServer(server) {
      // Interceptar requisições para arquivos do Git
      server.middlewares.use((req, res, next) => {
        if (req.url && (req.url.includes('.git') || req.url.includes('/proc/') || req.url.includes('/sys/'))) {
          res.statusCode = 404
          res.end('Not Found')
          return
        }
        next()
      })
    }
  }
}

// Resolver caminhos para ESM
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Flags para rodar por trás de proxy/HTTPS
const IS_PROXY = process.env.VITE_BEHIND_PROXY === '1' || process.env.BEHIND_PROXY === '1'
const PUBLIC_HOST = process.env.VITE_PUBLIC_HOST || '192.241.155.236'

// Configurar HMR para produção IP (HTTP)
const hmrConfig = IS_PROXY
  ? { protocol: 'ws', host: PUBLIC_HOST, clientPort: 8010 }
  : undefined

export default defineConfig({
  plugins: [
    ignoreSystemFiles(),
    react({
      jsxRuntime: 'automatic' // Usar JSX transform automático
    })
  ],
  resolve: {
    dedupe: ['react', 'react-dom'], // Garantir que há apenas uma cópia do React
    alias: {
      // Usar path.resolve em vez de require.resolve para compatibilidade ESM
      'react': path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom')
    }
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime']
  },
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    allowedHosts: [PUBLIC_HOST, 'hiprod.grupohi.com.br', '192.241.155.236', '.replit.dev', 'localhost', '172.20.0.1'],
    hmr: hmrConfig,
    fs: {
      // Permitir servir arquivos do diretório do projeto
      strict: false
    }
  }
})
