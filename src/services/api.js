
import axios from 'axios'

const api = axios.create({
  baseURL: window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : `${window.location.protocol}//${window.location.hostname}:5000`,
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
    if (error.response?.status === 401 && !error.config.url?.includes('/login') && !error.config.url?.includes('/verify-token')) {
      console.log('Token expirado, removendo credenciais...')
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // Evitar loop infinito - não recarregar se já estiver na página de login
      if (window.location.pathname !== '/login') {
        window.location.reload()
      }
    }
    return Promise.reject(error)
  }
)

export default api
