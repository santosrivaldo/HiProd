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
import TokenManagement from './components/TokenManagement'
import ScreenshotPage from './pages/ScreenshotPage'
import FacePresencePage from './pages/FacePresencePage'
import ScreenTimelinePage from './pages/ScreenTimelinePage'
import KeylogSearchPage from './pages/KeylogSearchPage'
import UserDetailPage from './pages/UserDetailPage'
import ScreenPreviewPage from './pages/ScreenPreviewPage'
import DvrPage from './pages/DvrPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'

function AppContent() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()
  const isStandaloneView = location.pathname === '/preview' || location.pathname === '/dvr'
  const isAuthCallback = location.pathname === '/auth/callback'

  if (loading && !isAuthCallback) {
    return <LoadingSpinner size="xl" text="Carregando..." fullScreen />
  }

  if (isAuthCallback) {
    return (
      <Routes>
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
      </Routes>
    )
  }

  if (!isAuthenticated) {
    return <Login />
  }

  // Preview e DVR: guia só com a tela (estilo VNC), sem sidebar/layout
  if (isStandaloneView) {
    return (
      <Routes>
        <Route path="/preview" element={<ScreenPreviewPage />} />
        <Route path="/dvr" element={<DvrPage />} />
      </Routes>
    )
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/users" element={<UserManagement />} />
        <Route path="/tags" element={<TagManagement />} />
        <Route path="/activities" element={<ActivityManagement />} />
        <Route path="/schedules" element={<WorkScheduleManagement />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/tokens" element={<TokenManagement />} />
        <Route path="/screenshots/:activityId" element={<ScreenshotPage />} />
        <Route path="/face-presence" element={<FacePresencePage />} />
        <Route path="/timeline" element={<ScreenTimelinePage />} />
        <Route path="/dvr" element={<DvrPage />} />
        <Route path="/keylog" element={<KeylogSearchPage />} />
        <Route path="/users/:id" element={<UserDetailPage />} />
        <Route path="/preview" element={<ScreenPreviewPage />} />
      </Routes>
    </Layout>
  )
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <div className="min-h-full h-full min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
            <AppContent />
          </div>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App