import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')

    if (token && storedUser) {
      // Verificar se o token ainda é válido
      verifyToken(token)
    } else {
      setLoading(false)
    }
  }, [])

  const verifyToken = async (token) => {
    try {
      const response = await api.post('/verify-token', { token })
      if (response.data && response.data.valid) {
        const userData = {
          usuario_id: response.data.usuario_id,
          usuario: response.data.usuario
        }
        setUser(userData)
        setIsAuthenticated(true)
        localStorage.setItem('user', JSON.stringify(userData))
      } else {
        // Token inválido, limpar dados
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        setUser(null)
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error('Erro na verificação do token:', error)
      // Erro na verificação, limpar dados
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      setUser(null)
      setIsAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }

  const login = async (username, password) => {
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
        // Erro HTTP
        console.error('Status:', error.response.status)
        console.error('Data:', error.response.data)
        errorMessage = error.response.data?.message || `Erro ${error.response.status}`
      } else if (error.request) {
        // Erro de rede
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
  }

  const register = async (username, password, confirmPassword) => {
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
  }

  const logout = () => {
    setUser(null)
    setIsAuthenticated(false)
    localStorage.removeItem('user')
    localStorage.removeItem('token')
  }

  const value = {
    user,
    isAuthenticated,
    login,
    register,
    logout,
    loading
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}