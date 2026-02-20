
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
const IS_HTTPS = process.env.VITE_HTTPS === '1' || process.env.HTTPS === '1' || 
                 process.env.NODE_ENV === 'production' // Assumir HTTPS em produção
const PUBLIC_HOST = process.env.VITE_PUBLIC_HOST || 'hiprod.grupohi.com.br'

// Desabilitar HMR quando a página for servida por HTTPS para evitar Mixed Content (ws:// bloqueado)
// O navegador bloqueia WebSocket inseguro (ws://) em páginas carregadas por HTTPS; exige wss://
const isProductionOrHttps = IS_HTTPS || IS_PROXY || PUBLIC_HOST.includes('grupohi.com.br')
const hmrConfig = isProductionOrHttps
  ? false
  : undefined

export default defineConfig({
  plugins: [
    ignoreSystemFiles(),
    react({
      jsxRuntime: 'automatic' // Usar JSX transform automático
    })
  ],
  resolve: {
    dedupe: ['react', 'react-dom', 'react/jsx-runtime'], // Garantir que há apenas uma cópia do React
    alias: {
      // Forçar resolução única do React - usar caminho absoluto
      'react': path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
      'react/jsx-runtime': path.resolve(__dirname, 'node_modules/react/jsx-runtime.js'),
      'react/jsx-dev-runtime': path.resolve(__dirname, 'node_modules/react/jsx-dev-runtime.js')
    },
    // Forçar resolução correta do React
    conditions: ['import', 'module', 'browser', 'default']
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime'],
    exclude: [], // Não excluir nada
    force: true // Forçar re-otimização para garantir uma única cópia
  },
  // Garantir que React é sempre resolvido corretamente
  esbuild: {
    jsx: 'automatic',
    // Garantir que React é tratado como external apenas quando necessário
    jsxImportSource: 'react'
  },
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    // Não habilitar HTTPS no servidor Vite se estiver atrás de proxy reverso
    // O proxy reverso (Nginx) já lida com HTTPS
    https: false,
    allowedHosts: [PUBLIC_HOST, 'hiprod.grupohi.com.br', '192.241.155.236', '.replit.dev', 'localhost', '172.20.0.1'],
    // Desabilitar HMR em produção HTTPS para evitar problemas de WebSocket
    hmr: IS_HTTPS ? false : hmrConfig,
    fs: {
      // Permitir servir arquivos do diretório do projeto
      strict: false
    },
    // Evitar ENOSPC: não observar pastas com muitos arquivos (uploads, node_modules, .git)
    watch: {
      ignored: ['**/uploads/**', '**/node_modules/**', '**/.git/**', '**/dist/**', '**/build/**']
    }
  },
  // Configurar para produção HTTPS
  build: {
    // Garantir que o build funciona em HTTPS
    rollupOptions: {
      output: {
        // Evitar problemas com mixed content
        assetFileNames: 'assets/[name].[hash].[ext]',
        // Manter React em um único chunk para evitar múltiplas cópias
        manualChunks: (id) => {
          // Agrupar React e dependências relacionadas em um único chunk
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'react-vendor'
          }
          // Outras dependências em chunks separados
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        }
      }
    },
    // Garantir que há apenas uma cópia do React no build
    commonjsOptions: {
      include: [/node_modules/],
      transformMixedEsModules: true
    }
  }
})
