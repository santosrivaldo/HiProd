import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react'
import api from '../services/api'

const AuthContext = createContext({
  user: null,
  isAuthenticated: false,
  login: () => Promise.resolve({ success: false }),
  register: () => Promise.resolve({ success: false }),
  logout: () => {},
  loading: true
})

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined || context === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token')
      const storedUser = localStorage.getItem('user')

      if (token && storedUser) {
        try {
          const userData = JSON.parse(storedUser)
          // Verificar se o token ainda é válido
          await verifyToken(token, userData)
        } catch (error) {
          console.error('Erro ao parsear dados do usuário:', error)
          clearAuthData()
        }
      } else {
        setLoading(false)
      }
    }

    // Event listener para logout forçado
    const handleLogout = () => {
      console.log('Logout forçado recebido')
      clearAuthData()
    }

    window.addEventListener('auth:logout', handleLogout)
    initAuth()

    return () => {
      window.removeEventListener('auth:logout', handleLogout)
    }
  }, [])

  const clearAuthData = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setIsAuthenticated(false)
    setLoading(false)
  }

  const verifyToken = async (token, userData) => {
    try {
      // Fazer requisição sem interceptor para evitar loop
      const baseURL = window.location.hostname === 'localhost' 
        ? 'http://localhost:5000' 
        : `${window.location.protocol}//${window.location.hostname}:5000`
      
      const response = await fetch(`${baseURL}/verify-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token })
      })

      const data = await response.json()
      
      if (response.ok && data.valid) {
        const validUserData = {
          usuario_id: data.usuario_id,
          usuario: data.usuario
        }
        setUser(validUserData)
        setIsAuthenticated(true)
        localStorage.setItem('user', JSON.stringify(validUserData))
      } else {
        console.log('Token inválido ou expirado')
        clearAuthData()
      }
    } catch (error) {
      console.error('Erro na verificação do token:', error)
      clearAuthData()
    } finally {
      setLoading(false)
    }
  }

  const login = useCallback(async (username, password) => {
    try {
      console.log('Iniciando login...', { username })
      
      const response = await api.post('/login', {
        nome: username,
        senha: password
      })

      console.log('Resposta do login:', response.status, response.data)

      if (response.data && response.data.token) {
        const userData = {
          usuario_id: response.data.usuario_id,
          usuario: response.data.usuario
        }

        // Aguardar um pouco antes de definir o estado
        await new Promise(resolve => setTimeout(resolve, 100))

        setUser(userData)
        setIsAuthenticated(true)
        localStorage.setItem('user', JSON.stringify(userData))
        localStorage.setItem('token', response.data.token)

        console.log('Login bem-sucedido:', userData)
        return { success: true }
      } else {
        console.error('Resposta inválida:', response.data)
        return { 
          success: false, 
          error: 'Resposta inválida do servidor' 
        }
      }
    } catch (error) {
      console.error('Erro no login:', error)
      
      let errorMessage = 'Erro no login'
      
      if (error.response) {
        console.error('Status:', error.response.status)
        console.error('Data:', error.response.data)
        errorMessage = error.response.data?.message || `Erro ${error.response.status}`
      } else if (error.request) {
        console.error('Erro de rede:', error.request)
        errorMessage = 'Erro de conexão com o servidor'
      } else {
        console.error('Erro geral:', error.message)
        errorMessage = error.message
      }
      
      return { 
        success: false, 
        error: errorMessage
      }
    }
  }, [])

  const register = useCallback(async (username, password, confirmPassword) => {
    if (password !== confirmPassword) {
      return { success: false, error: 'Senhas não coincidem' }
    }

    try {
      const response = await api.post('/register', {
        nome: username,
        senha: password
      })

      const userData = {
        usuario_id: response.data.usuario_id,
        usuario: response.data.usuario
      }

      setUser(userData)
      setIsAuthenticated(true)
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('token', response.data.token)

      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.message || 'Erro no registro' 
      }
    }
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    setIsAuthenticated(false)
    localStorage.removeItem('user')
    localStorage.removeItem('token')
  }, [])

  const value = useMemo(() => ({
    user,
    isAuthenticated,
    login,
    register,
    logout,
    loading
  }), [user, isAuthenticated, loading])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}