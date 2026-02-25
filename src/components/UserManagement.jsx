import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format } from 'date-fns'
import { formatBrasiliaDate } from '../utils/timezoneUtils'

const UserManagement = () => {
  const { user } = useAuth()
  const [usuarios, setUsuarios] = useState([])
  const [usuariosMonitorados, setUsuariosMonitorados] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab] = useState('usuarios')
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    senha: '',
    perfil: 'colaborador',
    cargo: '',
    departamento_id: '',
    valor_contrato: ''
  })
  
  // Estado para usuários do sistema
  const [systemFormData, setSystemFormData] = useState({
    nome: '',
    email: '',
    senha: '',
    departamento_id: ''
  })
  const [editingSystemUser, setEditingSystemUser] = useState(null)
  const [showSystemForm, setShowSystemForm] = useState(false)
  const [showInactiveUsers, setShowInactiveUsers] = useState(false)
  const [inactiveUsers, setInactiveUsers] = useState([])
  const [syncingPhotos, setSyncingPhotos] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [usuariosMonitoradosResponse, departamentosResponse] = await Promise.all([
        api.get('/usuarios-monitorados').catch(() => ({ data: [] })),
        api.get('/departamentos').catch(() => ({ data: [] }))
      ])
      const list = usuariosMonitoradosResponse.data || []
      setUsuariosMonitorados(list)
      setUsuarios(list)
      setDepartments(departamentosResponse.data || [])
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      setUsuarios([])
      setUsuariosMonitorados([])
      setDepartments([])
    } finally {
      setLoading(false)
    }
  }

  const fetchInactiveUsers = async () => {
    try {
      const response = await api.get('/usuarios/inativos')
      setInactiveUsers(response.data || [])
    } catch (error) {
      console.error('Erro ao carregar usuários inativos:', error)
      setInactiveUsers([])
    }
  }

  const handleSubmitMonitorado = async (e) => {
    e.preventDefault()

    try {
      if (editingUser) {
        await api.put(`/usuarios-monitorados/${editingUser.id}`, {
          nome: formData.nome,
          cargo: formData.cargo,
          departamento_id: formData.departamento_id || null,
          valor_contrato: formData.valor_contrato || null,
          perfil: formData.perfil,
          email: formData.email
        })
        setMessage('Usuário atualizado com sucesso!')
      } else {
        if (!formData.senha || formData.senha.length < 6) {
          setMessage('Senha é obrigatória (mín. 6 caracteres) para novo usuário.')
          setTimeout(() => setMessage(''), 4000)
          return
        }
        await api.post('/usuarios', {
          nome: formData.nome,
          email: formData.email || undefined,
          senha: formData.senha,
          perfil: formData.perfil,
          departamento_id: formData.departamento_id || null,
          cargo: formData.cargo || undefined,
          valor_contrato: formData.valor_contrato || null
        })
        setMessage('Usuário criado com sucesso!')
      }

      fetchData()
      resetForm()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao salvar usuário:', error)
      setMessage('Erro ao salvar: ' + (error.response?.data?.message || error.message))
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleEditMonitorado = (usuario) => {
    setEditingUser(usuario)
    setFormData({
      nome: usuario.nome,
      email: usuario.email || '',
      senha: '',
      perfil: usuario.perfil || 'colaborador',
      cargo: usuario.cargo || '',
      departamento_id: usuario.departamento_id || '',
      valor_contrato: usuario.valor_contrato != null && usuario.valor_contrato !== '' ? String(usuario.valor_contrato) : ''
    })
    setShowForm(true)
  }

  const handleUpdateUsuarioDepartment = async (usuarioId, departamentoId) => {
    try {
      await api.patch(`/usuarios/${usuarioId}/departamento`, {
        departamento_id: departamentoId
      })
      setMessage('Departamento do usuário atualizado com sucesso!')
      fetchData()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao atualizar departamento:', error)
      setMessage('Erro ao atualizar departamento')
      setTimeout(() => setMessage(''), 3000)
    }
  }

  const resetForm = () => {
    setFormData({
      nome: '',
      email: '',
      senha: '',
      perfil: 'colaborador',
      cargo: '',
      departamento_id: '',
      valor_contrato: ''
    })
    setEditingUser(null)
    setShowForm(false)
  }

  const getDepartmentName = (departamentoId) => {
    const dept = departments.find(d => d.id === departamentoId)
    return dept ? dept.nome : 'Sem Departamento'
  }

  // ========================================
  // CRUD PARA USUÁRIOS DO SISTEMA
  // ========================================

  const handleSubmitSystemUser = async (e) => {
    e.preventDefault()

    try {
      if (editingSystemUser) {
        // Atualizar usuário existente
        await api.put(`/usuarios/${editingSystemUser.usuario_id}`, systemFormData)
        setMessage('Usuário atualizado com sucesso!')
      } else {
        // Criar novo usuário
        await api.post('/usuarios', systemFormData)
        setMessage('Usuário criado com sucesso!')
      }

      // Resetar formulário e recarregar dados
      setSystemFormData({ nome: '', email: '', senha: '', departamento_id: '' })
      setEditingSystemUser(null)
      setShowSystemForm(false)
      await fetchData()

      // Limpar mensagem após 3 segundos
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao salvar usuário:', error)
      setMessage(error.response?.data?.message || 'Erro ao salvar usuário')
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleEditSystemUser = (usuario) => {
    setEditingSystemUser(usuario)
    setSystemFormData({
      nome: usuario.usuario,
      email: usuario.email || '',
      senha: '', // Não preencher senha por segurança
      departamento_id: usuario.departamento_id || ''
    })
    setShowSystemForm(true)
  }

  const handleDeleteSystemUser = async (usuario) => {
    if (!window.confirm(`Tem certeza que deseja desativar o usuário ${usuario.usuario}?`)) {
      return
    }

    try {
      await api.delete(`/usuarios/${usuario.usuario_id}`)
      setMessage(`Usuário ${usuario.usuario} foi desativado com sucesso!`)
      await fetchData()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao deletar usuário:', error)
      setMessage(error.response?.data?.message || 'Erro ao deletar usuário')
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleReactivateSystemUser = async (usuario) => {
    try {
      await api.patch(`/usuarios/${usuario.usuario_id}/reativar`)
      setMessage(`Usuário ${usuario.usuario} foi reativado com sucesso!`)
      await fetchData()
      await fetchInactiveUsers()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao reativar usuário:', error)
      setMessage(error.response?.data?.message || 'Erro ao reativar usuário')
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleResetPassword = async (usuario) => {
    const novaSenha = window.prompt(`Digite a nova senha para ${usuario.usuario}:`)
    if (!novaSenha) return

    if (novaSenha.length < 6) {
      setMessage('Senha deve ter pelo menos 6 caracteres!')
      setTimeout(() => setMessage(''), 3000)
      return
    }

    try {
      await api.patch(`/usuarios/${usuario.usuario_id}/reset-senha`, { nova_senha: novaSenha })
      setMessage(`Senha do usuário ${usuario.usuario} foi resetada com sucesso!`)
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao resetar senha:', error)
      setMessage(error.response?.data?.message || 'Erro ao resetar senha')
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleCancelSystemForm = () => {
    setShowSystemForm(false)
    setEditingSystemUser(null)
    setSystemFormData({ nome: '', email: '', senha: '', departamento_id: '' })
  }

  const toggleInactiveUsers = async () => {
    if (!showInactiveUsers) {
      await fetchInactiveUsers()
    }
    setShowInactiveUsers(!showInactiveUsers)
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Usuários
        </h1>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={async () => {
              setSyncingPhotos(true)
              try {
                const { data } = await api.post('/bitrix-sync-photos')
                setMessage(data?.updated !== undefined ? `Fotos atualizadas: ${data.updated} colaborador(es).` : 'Fotos sincronizadas.')
                fetchData()
              } catch (err) {
                setMessage('Erro ao sincronizar fotos: ' + (err.response?.data?.error || err.message))
              } finally {
                setSyncingPhotos(false)
              }
              setTimeout(() => setMessage(''), 4000)
            }}
            disabled={syncingPhotos}
            className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
          >
            {syncingPhotos ? 'Sincronizando…' : 'Sincronizar fotos (Bitrix)'}
          </button>
          <button
            onClick={() => {
              if (showForm) {
                resetForm()
              } else {
                setEditingUser(null)
                setFormData({ nome: '', email: '', senha: '', perfil: 'colaborador', cargo: '', departamento_id: '', valor_contrato: '' })
                setShowForm(true)
              }
            }}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {showForm ? 'Cancelar' : 'Novo usuário'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-md ${message.includes('sucesso') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message}
        </div>
      )}

      {/* Formulário único: novo ou editar usuário */}
      {showForm && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {editingUser ? 'Editar usuário' : 'Novo usuário'}
          </h2>

          <form onSubmit={handleSubmitMonitorado} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Nome *</label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">E-mail</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="nome@empresa.com"
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              {!editingUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Senha * (mín. 6 caracteres)</label>
                  <input
                    type="password"
                    value={formData.senha}
                    onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    minLength={6}
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Nível de acesso (perfil)</label>
                <select
                  value={formData.perfil}
                  onChange={(e) => setFormData({ ...formData, perfil: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="colaborador">Colaborador</option>
                  <option value="supervisor">Supervisor</option>
                  <option value="coordenador">Coordenador</option>
                  <option value="head">Head</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Cargo</label>
                <input
                  type="text"
                  value={formData.cargo}
                  onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Departamento</label>
                <select
                  value={formData.departamento_id}
                  onChange={(e) => setFormData({ ...formData, departamento_id: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Selecione</option>
                  {departments.map(dept => (
                    <option key={dept.id} value={dept.id}>{dept.nome}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Valor de contrato (R$/dia)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.valor_contrato}
                  onChange={(e) => setFormData({ ...formData, valor_contrato: e.target.value })}
                  placeholder="Ex: 166.67"
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                {editingUser ? 'Atualizar' : 'Criar'} Usuário
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Pendências */}
      {(() => {
        const comPendencias = (usuariosMonitorados || []).filter(u => u.pendencias && u.pendencias.length > 0)
        const labelPendencia = (p) => {
          if (p === 'dados_cadastrais') return 'Dados cadastrais (cargo)'
          if (p === 'setor') return 'Setor'
          if (p === 'valor_contrato') return 'Valor de contrato (custo produtividade)'
          return p
        }
        return comPendencias.length > 0 ? (
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-2">
              Pendências de usuários monitorados
            </h3>
            <p className="text-xs text-amber-700 dark:text-amber-300 mb-3">
              Falta de dados cadastrais, setor ou valor de contrato (usado no custo de produtividade). Clique em Editar para preencher.
            </p>
            <ul className="space-y-2">
              {comPendencias.map((usuario) => (
                <li key={usuario.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium text-gray-900 dark:text-white">{usuario.nome}</span>
                  <span className="text-amber-700 dark:text-amber-300">—</span>
                  {usuario.pendencias.map((p) => (
                    <span key={p} className="inline-flex items-center px-2 py-0.5 rounded bg-amber-200 dark:bg-amber-800 text-amber-900 dark:text-amber-100 text-xs">
                      {labelPendencia(p)}
                    </span>
                  ))}
                  <button
                    type="button"
                    onClick={() => handleEditMonitorado(usuario)}
                    className="text-indigo-600 dark:text-indigo-400 hover:underline text-xs font-medium"
                  >
                    Editar
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null
      })()}

      {/* Lista unificada de usuários (mesma pessoa; diferença = perfil) */}
      <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
            Usuários ({usuariosMonitorados.length})
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Colaboradores com acesso ao sistema; a diferença entre eles é o nível de acesso (perfil).
          </p>
        </div>

        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {usuariosMonitorados.map((usuario) => (
            <li key={usuario.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 relative w-10 h-10 rounded-full overflow-hidden bg-indigo-500 flex items-center justify-center">
                      {usuario.foto_url && (
                        <img
                          src={usuario.foto_url}
                          alt=""
                          className="absolute inset-0 w-full h-full object-cover"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      )}
                      <span className="text-white font-medium text-sm relative z-[0]">
                        {usuario.nome.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {usuario.nome}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate" title={usuario.email_display || `${usuario.nome}@grupohi.com.br`}>
                        {usuario.email_display || usuario.email || `${usuario.nome}@grupohi.com.br`}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                        {usuario.cargo || 'Sem cargo'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {getDepartmentName(usuario.departamento_id)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 flex-shrink-0">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200 capitalize">
                    {usuario.perfil || 'colaborador'}
                  </span>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    usuario.ativo
                      ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                      : 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                  }`}>
                    {usuario.ativo ? 'Ativo' : 'Inativo'}
                  </span>
                  <button
                    onClick={() => handleEditMonitorado(usuario)}
                    className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 text-sm font-medium"
                  >
                    Editar
                  </button>
                </div>
              </div>

              {usuario.created_at && (
                <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Criado em: {formatBrasiliaDate(usuario.created_at, 'datetime')}
                </div>
              )}
            </li>
          ))}
        </ul>

        {usuariosMonitorados.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400">
              Nenhum usuário cadastrado. Clique em &quot;Novo usuário&quot; para começar.
            </p>
          </div>
        )}
      </div>

    </div>
  )
}

export default UserManagement