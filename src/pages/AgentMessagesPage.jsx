import React, { useState, useEffect } from 'react'
import api from '../services/api'
import {
  MegaphoneIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'

const TIPOS = [
  { value: 'info', label: 'Informação', icon: InformationCircleIcon, color: 'text-blue-600' },
  { value: 'alerta', label: 'Alerta', icon: ExclamationTriangleIcon, color: 'text-amber-600' },
  { value: 'urgente', label: 'Urgente', icon: ExclamationCircleIcon, color: 'text-red-600' },
]
const DESTINOS = [
  { value: 'todos', label: 'Todos os usuários' },
  { value: 'usuario', label: 'Um usuário (monitorado)' },
  { value: 'departamento', label: 'Departamento' },
]

export default function AgentMessagesPage() {
  const [messages, setMessages] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [departamentos, setDepartamentos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({
    titulo: '',
    mensagem: '',
    tipo: 'info',
    destino_tipo: 'todos',
    destino_id: '',
    expires_at: '',
  })

  const loadMessages = async () => {
    try {
      const res = await api.get('/agent-messages')
      setMessages(res.data || [])
    } catch (e) {
      setMessage('Erro ao carregar mensagens: ' + (e.response?.data?.error || e.message))
    }
  }

  const loadAux = async () => {
    try {
      const [u, d] = await Promise.all([
        api.get('/usuarios-monitorados').catch(() => ({ data: [] })),
        api.get('/departamentos').catch(() => ({ data: [] })),
      ])
      setUsuarios(Array.isArray(u.data) ? u.data : [])
      setDepartamentos(d.data || [])
    } catch (_) {}
  }

  useEffect(() => {
    setLoading(true)
    loadMessages().finally(() => setLoading(false))
    loadAux()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMessage('')
    const payload = {
      titulo: form.titulo.trim(),
      mensagem: form.mensagem.trim(),
      tipo: form.tipo,
      destino_tipo: form.destino_tipo,
      destino_id: form.destino_tipo === 'todos' ? null : (form.destino_id ? Number(form.destino_id) : null),
      expires_at: form.expires_at || undefined,
    }
    try {
      if (editingId) {
        await api.put(`/agent-messages/${editingId}`, payload)
        setMessage('Mensagem atualizada.')
      } else {
        await api.post('/agent-messages', payload)
        setMessage('Mensagem criada. O agente exibirá na próxima verificação (até 10 min).')
      }
      setShowForm(false)
      setEditingId(null)
      setForm({ titulo: '', mensagem: '', tipo: 'info', destino_tipo: 'todos', destino_id: '', expires_at: '' })
      loadMessages()
      setTimeout(() => setMessage(''), 4000)
    } catch (err) {
      setMessage('Erro: ' + (err.response?.data?.error || err.message))
    }
  }

  const handleEdit = (m) => {
    setEditingId(m.id)
    setForm({
      titulo: m.titulo,
      mensagem: m.mensagem,
      tipo: m.tipo || 'info',
      destino_tipo: m.destino_tipo || 'todos',
      destino_id: m.destino_id != null ? String(m.destino_id) : '',
      expires_at: m.expires_at ? m.expires_at.slice(0, 16) : '',
    })
    setShowForm(true)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Excluir esta mensagem?')) return
    try {
      await api.delete(`/agent-messages/${id}`)
      loadMessages()
      setMessage('Mensagem excluída.')
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage('Erro ao excluir: ' + (err.response?.data?.error || err.message))
    }
  }

  const tipoInfo = (tipo) => TIPOS.find((t) => t.value === tipo) || TIPOS[0]
  const destinoLabel = (m) => {
    if (m.destino_tipo === 'todos') return 'Todos'
    if (m.destino_tipo === 'departamento') {
      const d = departamentos.find((x) => x.id === m.destino_id)
      return d ? d.nome : `Dept #${m.destino_id}`
    }
    const u = usuarios.find((x) => x.id === m.destino_id)
    return u ? u.nome : `Usuário #${m.destino_id}`
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <MegaphoneIcon className="h-8 w-8" />
          Mensagens ao agente
        </h1>
        <button
          type="button"
          onClick={() => {
            setEditingId(null)
            setForm({ titulo: '', mensagem: '', tipo: 'info', destino_tipo: 'todos', destino_id: '', expires_at: '' })
            setShowForm(!showForm)
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-xl shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Nova mensagem
        </button>
      </div>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        As mensagens são exibidas no computador do colaborador pelo agente HiProd, a cada 10 minutos. Destino: todos, um usuário ou um departamento.
      </p>

      {message && (
        <div className="mt-4 p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-800 dark:text-indigo-200">
          {message}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="mt-6 p-6 rounded-xl bg-white dark:bg-gray-800 shadow border border-gray-200 dark:border-gray-700 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Título</label>
            <input
              type="text"
              required
              value={form.titulo}
              onChange={(e) => setForm((f) => ({ ...f, titulo: e.target.value }))}
              className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm px-3 py-2"
              placeholder="Ex: Aviso importante"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Mensagem</label>
            <textarea
              required
              rows={4}
              value={form.mensagem}
              onChange={(e) => setForm((f) => ({ ...f, mensagem: e.target.value }))}
              className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm px-3 py-2"
              placeholder="Texto que aparecerá na tela do colaborador"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Tipo</label>
              <select
                value={form.tipo}
                onChange={(e) => setForm((f) => ({ ...f, tipo: e.target.value }))}
                className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
              >
                {TIPOS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Destino</label>
              <select
                value={form.destino_tipo}
                onChange={(e) => setForm((f) => ({ ...f, destino_tipo: e.target.value, destino_id: '' }))}
                className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
              >
                {DESTINOS.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>
          {form.destino_tipo === 'usuario' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Usuário monitorado</label>
              <select
                value={form.destino_id}
                onChange={(e) => setForm((f) => ({ ...f, destino_id: e.target.value }))}
                className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
              >
                <option value="">Selecione</option>
                {usuarios.map((u) => (
                  <option key={u.id} value={u.id}>{u.nome}</option>
                ))}
              </select>
            </div>
          )}
          {form.destino_tipo === 'departamento' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Departamento</label>
              <select
                value={form.destino_id}
                onChange={(e) => setForm((f) => ({ ...f, destino_id: e.target.value }))}
                className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
              >
                <option value="">Selecione</option>
                {departamentos.map((d) => (
                  <option key={d.id} value={d.id}>{d.nome}</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Expira em (opcional)</label>
            <input
              type="datetime-local"
              value={form.expires_at}
              onChange={(e) => setForm((f) => ({ ...f, expires_at: e.target.value }))}
              className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">
              {editingId ? 'Atualizar' : 'Criar mensagem'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setEditingId(null); }}
              className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      <div className="mt-8">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Mensagens cadastradas</h2>
        {loading ? (
          <p className="text-gray-500 dark:text-gray-400">Carregando...</p>
        ) : messages.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400">Nenhuma mensagem. Crie uma para ser exibida no agente.</p>
        ) : (
          <ul className="space-y-3">
            {messages.map((m) => {
              const t = tipoInfo(m.tipo)
              const Icon = t.icon
              return (
                <li
                  key={m.id}
                  className="p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Icon className={`h-5 w-5 flex-shrink-0 ${t.color}`} />
                      <span className="font-medium text-gray-900 dark:text-white">{m.titulo}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {m.destino_tipo} → {destinoLabel(m)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 line-clamp-2">{m.mensagem}</p>
                    <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                      Criada em {m.created_at} {m.created_by_nome ? `por ${m.created_by_nome}` : ''}
                      {m.expires_at ? ` · Expira ${m.expires_at}` : ''}
                    </p>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => handleEdit(m)}
                      className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="Editar"
                    >
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(m.id)}
                      className="p-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                      title="Excluir"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
