import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { getPerfilLabel } from '../utils/permissions'
import LoadingSpinner from '../components/LoadingSpinner'

export default function MeuPerfilPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    senha: ''
  })

  useEffect(() => {
    if (!user?.usuario_id) {
      setLoading(false)
      return
    }
    const load = async () => {
      setLoading(true)
      try {
        const res = await api.get(`/usuarios/${user.usuario_id}`)
        setProfile(res.data)
        setFormData({
          nome: res.data.usuario || '',
          email: res.data.email || '',
          senha: ''
        })
      } catch (e) {
        console.error(e)
        setMessage('Erro ao carregar seu perfil.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user?.usuario_id])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!user?.usuario_id) return
    setSaving(true)
    setMessage('')
    try {
      const payload = {
        nome: formData.nome.trim(),
        email: formData.email.trim() || null
      }
      if (formData.senha && formData.senha.length >= 6) {
        payload.senha = formData.senha
      }
      await api.put(`/usuarios/${user.usuario_id}`, payload)
      setMessage('Perfil atualizado com sucesso!')
      setProfile((prev) => prev ? { ...prev, ...payload } : null)
      setFormData((f) => ({ ...f, senha: '' }))
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage(err.response?.data?.message || 'Erro ao salvar.')
      setTimeout(() => setMessage(''), 5000)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (!user?.usuario_id) {
    return (
      <div className="p-6">
        <p className="text-gray-600 dark:text-gray-400">Sessão inválida. Faça login novamente.</p>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Meu perfil</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Visualize e altere seus dados de acesso (nome, e-mail e senha).
      </p>

      {profile && (
        <div className="mb-4 p-3 rounded-lg bg-gray-100 dark:bg-gray-700/50 text-sm text-gray-600 dark:text-gray-300">
          <span className="font-medium">Nível de acesso:</span> {getPerfilLabel(profile.perfil)}
          {profile.departamento?.nome && (
            <> · Setor: {profile.departamento.nome}</>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Nome de usuário *</label>
          <input
            type="text"
            value={formData.nome}
            onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
            className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            minLength={3}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">E-mail</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Nova senha (deixe em branco para não alterar)</label>
          <input
            type="password"
            value={formData.senha}
            onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
            className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            minLength={6}
            placeholder="Mínimo 6 caracteres"
          />
        </div>
        {message && (
          <p className={`text-sm ${message.includes('sucesso') ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {message}
          </p>
        )}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Voltar
          </button>
        </div>
      </form>
    </div>
  )
}
