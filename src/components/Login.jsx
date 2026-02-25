import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'

export default function Login() {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPasswordLogin, setShowPasswordLogin] = useState(false)
  const { login, loginWithSSO } = useAuth()

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSSO = async () => {
    setError('')
    setLoading(true)
    try {
      const res = await api.get('/sso/url')
      if (res.data && res.data.url) {
        window.location.href = res.data.url
        return
      }
    } catch (_) {}
    setLoading(false)
    setShowPasswordLogin(false)
  }

  const handleSSOWithEmail = async (e) => {
    e.preventDefault()
    const email = formData.email.trim()
    if (!email || !email.includes('@')) {
      setError('Informe seu e-mail corporativo (ex: nome@grupohi.com.br)')
      return
    }
    setLoading(true)
    setError('')
    const result = await loginWithSSO(email)
    setLoading(false)
    if (!result.success) setError(result.error || 'Falha no login SSO')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.username.trim() || !formData.password.trim()) {
      setError('Preencha usuário e senha')
      return
    }
    setLoading(true)
    setError('')
    const result = await login(formData.username.trim(), formData.password)
    setLoading(false)
    if (!result.success) {
      setError(result.error?.toLowerCase().includes('credenciais') ? 'Usuário ou senha incorretos' : result.error)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center app-bg py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="glass-card p-8">
          <div>
            <h2 className="text-center text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
              Activity Tracker
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
              Faça login para acessar o dashboard
            </p>
          </div>

          {/* SSO em prioridade */}
          {!showPasswordLogin ? (
            <div className="mt-8 space-y-4">
              <button
                type="button"
                onClick={handleSSO}
                disabled={loading}
                className="w-full flex justify-center items-center py-2.5 px-4 rounded-xl border border-indigo-500/50 bg-indigo-600/90 text-white hover:bg-indigo-600 focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-50 font-medium"
              >
                {loading ? 'Redirecionando...' : 'Entrar com SSO (Microsoft)'}
              </button>

              <form onSubmit={handleSSOWithEmail} className="space-y-2">
                <input
                  type="email"
                  name="email"
                  placeholder="Ou use seu e-mail corporativo (ex: nome@grupohi.com.br)"
                  value={formData.email}
                  onChange={handleChange}
                  className="glass-input w-full px-3 py-2 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-indigo-500/50"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 rounded-lg text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
                >
                  Entrar com e-mail
                </button>
              </form>

              <p className="text-center">
                <button
                  type="button"
                  onClick={() => setShowPasswordLogin(true)}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  Entrar com usuário e senha
                </button>
              </p>
            </div>
          ) : (
            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
              <div className="space-y-4">
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  className="glass-input w-full px-3 py-2.5 rounded-lg placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/50 sm:text-sm"
                  placeholder="Nome de usuário"
                  value={formData.username}
                  onChange={handleChange}
                />
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  className="glass-input w-full px-3 py-2.5 rounded-lg placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500/50 sm:text-sm"
                  placeholder="Senha"
                  value={formData.password}
                  onChange={handleChange}
                />
              </div>
              {error && (
                <div className="text-red-600 dark:text-red-400 text-sm text-center">{error}</div>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 text-sm font-medium rounded-xl text-white bg-indigo-600 hover:bg-indigo-500 focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-50"
              >
                {loading ? 'Entrando...' : 'Entrar'}
              </button>
              <p className="text-center">
                <button
                  type="button"
                  onClick={() => { setShowPasswordLogin(false); setError(''); }}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  Voltar para login SSO
                </button>
              </p>
            </form>
          )}

          {error && !showPasswordLogin && (
            <div className="mt-4 text-red-600 dark:text-red-400 text-sm text-center">{error}</div>
          )}

          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Usuários: nome = e-mail (ex: rivaldo.santos = rivaldo.santos@grupohi.com.br)
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
