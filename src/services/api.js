
import axios from 'axios'

// Preferred: explicit API URL via env
const ENV_API_URL = import.meta.env?.VITE_API_URL
const ENV_API_BASE_PATH = import.meta.env?.VITE_API_BASE_PATH || ''

// Force clean URL - remove any malformed parts
function cleanApiUrl(url) {
  if (!url) return url
  
  // Remove any encoded characters and malformed parts
  return url
    .replace(/hiprod-api%20:8010/g, '') // Remove the malformed part
    .replace(/\/api$/g, '') // Remove trailing /api
    .replace(/:\d+$/g, '') // Remove any port numbers
    .replace(/\/+$/, '') // Remove trailing slashes
}

function resolveBaseURL() {
  console.log('🔍 Debug API URL Resolution:')
  console.log('ENV_API_URL:', ENV_API_URL)
  console.log('ENV_API_BASE_PATH:', ENV_API_BASE_PATH)
  console.log('window.location:', window.location.href)
  
  // Force correct URL for production domain
  const { hostname } = window.location
  if (hostname === 'hiprod.grupohi.com.br') {
    console.log('✅ Forcing correct URL for production IP')
    return 'http://192.241.155.236'
  }
  
  // If VITE_API_URL is provided, use it directly (works for proxy/domain)
  if (ENV_API_URL && typeof ENV_API_URL === 'string' && ENV_API_URL.trim() !== '') {
    let baseUrl = cleanApiUrl(ENV_API_URL.replace(/\/$/, ''))
    // Only add base path if it exists and is not empty
    if (ENV_API_BASE_PATH && ENV_API_BASE_PATH.trim() !== '') {
      baseUrl += ENV_API_BASE_PATH
    }
    console.log('✅ Using ENV_API_URL, final baseUrl:', baseUrl)
    return baseUrl
  }

  // Fallbacks
  const { protocol, origin } = window.location

  // Local development defaults
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    // Prefer backend on 8010 locally
    console.log('✅ Using localhost fallback: http://localhost:8010')
    return 'http://localhost:8010'
  }

  // In production behind proxy: try same-origin (no port), optionally with base path
  // This assumes the reverse proxy routes the API under the same domain
  let baseUrl = cleanApiUrl(origin.replace(/\/$/, ''))
  if (ENV_API_BASE_PATH && ENV_API_BASE_PATH.trim() !== '') {
    baseUrl += ENV_API_BASE_PATH
  }
  console.log('✅ Using origin fallback, final baseUrl:', baseUrl)
  return baseUrl
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
