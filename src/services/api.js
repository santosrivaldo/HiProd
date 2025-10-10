
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
    .replace(/\/api$/g, '') // Remove trailing /api (Nginx will handle routing)
    .replace(/:\d+$/g, '') // Remove any port numbers (Nginx proxy handles this)
    .replace(/\/+$/, '') // Remove trailing slashes
}

function resolveBaseURL() {
  console.log('🔍 API URL Resolution')
  console.log('Current location:', window.location.href)
  
  const hostname = window.location.hostname
  
  // PRODUCTION: Always use IP directly
  if (hostname.includes('grupohi.com.br')) {
    console.log('🎯 PRODUCTION: Using direct IP')
    return 'http://192.241.155.236:8010'
  }
  
  // DEVELOPMENT: Use localhost
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    console.log('🔧 DEVELOPMENT: Using localhost')
    return 'http://localhost:8010'
  }
  
  // FALLBACK: Default to localhost
  console.log('🔄 FALLBACK: Using localhost')
  return 'http://localhost:8010'
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
