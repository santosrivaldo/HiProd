
import axios from 'axios'

// Preferred: explicit API URL via env
const ENV_API_URL = import.meta.env?.VITE_API_URL
const ENV_API_BASE_PATH = import.meta.env?.VITE_API_BASE_PATH || '' // e.g. '/api'

function resolveBaseURL() {
  // If VITE_API_URL is provided, use it directly (works for proxy/domain)
  if (ENV_API_URL && typeof ENV_API_URL === 'string' && ENV_API_URL.trim() !== '') {
    // Allow optional base path chaining
    return ENV_API_URL.replace(/\/$/, '') + ENV_API_BASE_PATH
  }

  // Fallbacks
  const { protocol, hostname, origin } = window.location

  // Local development defaults
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    // Prefer backend on 8000 locally
    return 'http://localhost:8000'
  }

  // In production behind proxy: try same-origin (no port), optionally with base path
  // This assumes the reverse proxy routes the API under the same domain
  return origin.replace(/\/$/, '') + ENV_API_BASE_PATH
}

const api = axios.create({
  baseURL: resolveBaseURL(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para adicionar token automaticamente
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Interceptor para lidar com respostas de erro
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Só tratar erro 401 se não for das rotas de auth
    if (
      error.response?.status === 401 &&
      !error.config.url?.includes('/login') &&
      !error.config.url?.includes('/register') &&
      !error.config.url?.includes('/verify-token')
    ) {
      console.log('Token expirado, removendo credenciais...')
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // Emitir evento customizado para AuthContext lidar com logout
      window.dispatchEvent(new CustomEvent('auth:logout'))
    }
    return Promise.reject(error)
  }
)

export default api
