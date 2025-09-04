import React, { useState, useEffect } from 'react'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import Layout from './components/Layout'
import { useAuth } from './contexts/AuthContext'
import LoadingSpinner from './components/LoadingSpinner'
import UserManagement from './components/UserManagement'
import TagManagement from './components/TagManagement'
import ActivityManagement from './components/ActivityManagement'
import WorkScheduleManagement from './components/WorkScheduleManagement'
import Settings from './components/Settings'
import { Routes, Route } from 'react-router-dom'


function AppContent() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <LoadingSpinner size="xl" text="Carregando..." fullScreen />
  }

  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/users" element={<UserManagement />} />
      <Route path="/tags" element={<TagManagement />} />
      <Route path="/activities" element={<ActivityManagement />} />
      <Route path="/schedules" element={<WorkScheduleManagement />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  )
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