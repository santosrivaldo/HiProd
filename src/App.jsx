import React, { useState, useEffect } from 'react'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import Layout from './components/Layout'
import { useAuth } from './contexts/AuthContext'
import LoadingSpinner from './components/LoadingSpinner'

function AppContent() {
  const auth = useAuth()

  if (!auth) {
    return <div>Erro: AuthContext não disponível</div>
  }

  const { isAuthenticated, loading } = auth

  if (loading) {
    return <LoadingSpinner size="xl" text="Carregando..." fullScreen />
  }

  return isAuthenticated ? <Layout /> : <Login />
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <AppContent />
        </div>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App