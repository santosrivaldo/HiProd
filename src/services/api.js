
import axios from 'axios'

const api = axios.create({
  baseURL: window.location.hostname === 'localhost' 
    ? 'http://192.241.155.236:8010' 
    : `${window.location.protocol}//${window.location.hostname}:8010`,
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
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor para lidar com respostas de erro
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Só tratar erro 401 se não for das rotas de auth
    if (error.response?.status === 401 && 
        !error.config.url?.includes('/login') && 
        !error.config.url?.includes('/register') &&
        !error.config.url?.includes('/verify-token')) {
      
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
