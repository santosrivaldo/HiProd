import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'

/**
 * Página de callback após login SSO (Microsoft etc.).
 * Recebe ?token=... na URL, valida o token e redireciona para o dashboard.
 */
export default function AuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { completeSSOCallback } = useAuth()
  const [error, setError] = useState(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const ssoError = searchParams.get('sso_error')

    if (ssoError) {
      setError(ssoError === '2' ? 'Usuário não cadastrado. Contate o administrador.' : 'Falha no login SSO.')
      setTimeout(() => navigate('/', { replace: true }), 3000)
      return
    }

    if (!token) {
      setError('Token não recebido.')
      setTimeout(() => navigate('/', { replace: true }), 2000)
      return
    }

    let cancelled = false
    completeSSOCallback(token).then((result) => {
      if (cancelled) return
      if (result.success) {
        navigate('/', { replace: true })
      } else {
        setError(result.error || 'Falha ao validar login.')
        setTimeout(() => navigate('/', { replace: true }), 3000)
      }
    })
    return () => { cancelled = true }
  }, [searchParams, navigate, completeSSOCallback])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center app-bg">
        <div className="text-center text-red-600 dark:text-red-400">
          <p>{error}</p>
          <p className="text-sm mt-2 text-gray-500 dark:text-gray-400">Redirecionando...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center app-bg">
      <LoadingSpinner size="xl" text="Concluindo login SSO..." fullScreen />
    </div>
  )
}
