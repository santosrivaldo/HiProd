import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { formatBrasiliaDate } from '../utils/timezoneUtils'
import LoadingSpinner from '../components/LoadingSpinner'
import { MagnifyingGlassIcon, FilmIcon } from '@heroicons/react/24/outline'

export default function KeylogSearchPage() {
  const [q, setQ] = useState('')
  const [userId, setUserId] = useState('')
  const [departamentoId, setDepartamentoId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [users, setUsers] = useState([])
  const [departamentos, setDepartamentos] = useState([])
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const loadUsers = useCallback(async () => {
    try {
      const res = await api.get('/usuarios-monitorados')
      setUsers(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error(e)
    }
  }, [])
  const loadDepartamentos = useCallback(async () => {
    try {
      const res = await api.get('/departamentos')
      const list = res.data?.departamentos ?? res.data ?? []
      setDepartamentos(Array.isArray(list) ? list : [])
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => { loadUsers() }, [loadUsers])
  useEffect(() => { loadDepartamentos() }, [loadDepartamentos])

  const search = async (e) => {
    e?.preventDefault()
    setLoading(true)
    setSearched(true)
    setResults([])
    try {
      const params = new URLSearchParams()
      if (q.trim()) params.set('q', q.trim())
      if (userId) params.set('usuario_monitorado_id', userId)
      if (departamentoId) params.set('departamento_id', departamentoId)
      if (dateFrom) params.set('date_from', dateFrom)
      if (dateTo) params.set('date_to', dateTo)
      params.set('limit', '100')
      const res = await api.get(`/keylog/search?${params.toString()}`)
      setResults(res.data?.results ?? [])
    } catch (e) {
      console.error(e)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Busca por texto digitado (keylog)
      </h1>
      <form onSubmit={search} className="glass-card p-4 mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Palavra ou frase</label>
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ex: relatório, senha..."
              className="input-field w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Usuário</label>
            <select
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="input-field w-full"
            >
              <option value="">Todos</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.nome}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Departamento</label>
            <select
              value={departamentoId}
              onChange={(e) => setDepartamentoId(e.target.value)}
              className="input-field w-full"
            >
              <option value="">Todos</option>
              {departamentos.map((d) => (
                <option key={d.id} value={d.id}>{d.nome}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Data de</label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input-field w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Data até</label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input-field w-full" />
          </div>
        </div>
        <button type="submit" className="btn-primary inline-flex items-center gap-2" disabled={loading}>
          <MagnifyingGlassIcon className="w-5 h-5" />
          Buscar
        </button>
      </form>

      {loading && <LoadingSpinner size="md" className="my-4" />}
      {!loading && searched && (
        <div className="glass-card overflow-hidden">
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 text-sm text-gray-500 dark:text-gray-400">
            {results.length} resultado(s)
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Data/Hora</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Usuário</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Janela / App</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Texto</th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400">Tela</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {results.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {formatBrasiliaDate(r.captured_at, 'datetime')}
                    </td>
                    <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white">{r.usuario_monitorado_nome}</td>
                    <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 max-w-xs truncate" title={r.window_title}>
                      {r.window_title || r.application || '—'}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 max-w-md">
                      <span className="line-clamp-2">{r.text_content || '—'}</span>
                    </td>
                    <td className="px-4 py-2 text-center">
                      {r.date && (
                        <Link
                          to={`/timeline?userId=${r.usuario_monitorado_id}&date=${r.date}&at=${encodeURIComponent(r.captured_at || '')}`}
                          className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:underline"
                          title="Ver tela neste momento"
                        >
                          <FilmIcon className="w-4 h-4" /> Tela
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {results.length === 0 && (
            <p className="p-6 text-center text-gray-500 dark:text-gray-400">Nenhum resultado encontrado.</p>
          )}
        </div>
      )}
    </div>
  )
}
