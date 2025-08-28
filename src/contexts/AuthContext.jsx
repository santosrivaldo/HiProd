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
      const response = await api.post('/login', {
        nome: username,
        senha: password
      })

      if (response.data && response.data.token) {
        const userData = {
          usuario_id: response.data.usuario_id,
          usuario: response.data.usuario
        }

        setUser(userData)
        setIsAuthenticated(true)
        localStorage.setItem('user', JSON.stringify(userData))
        localStorage.setItem('token', response.data.token)

        return { success: true }
      } else {
        return { 
          success: false, 
          error: 'Resposta inválida do servidor' 
        }
      }
    } catch (error) {
      console.error('Erro no login:', error)
      return { 
        success: false, 
        error: error.response?.data?.message || error.message || 'Erro no login' 
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