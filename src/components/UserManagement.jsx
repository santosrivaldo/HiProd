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
  const [activeTab, setActiveTab] = useState('monitorados')
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({
    nome: '',
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

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [usuariosResponse, usuariosMonitoradosResponse, departamentosResponse] = await Promise.all([
        api.get('/usuarios').catch(() => ({ data: [] })),
        api.get('/usuarios-monitorados').catch(() => ({ data: [] })),
        api.get('/departamentos').catch(() => ({ data: [] }))
      ])

      setUsuarios(usuariosResponse.data || [])
      setUsuariosMonitorados(usuariosMonitoradosResponse.data || [])
      setDepartments(departamentosResponse.data || [])
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      // Set empty arrays on error
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
        await api.put(`/usuarios-monitorados/${editingUser.id}`, formData)
        setMessage('Usuário monitorado atualizado com sucesso!')
      } else {
        await api.post('/usuarios-monitorados', formData)
        setMessage('Usuário monitorado criado com sucesso!')
      }

      fetchData()
      resetForm()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao salvar usuário monitorado:', error)
      setMessage('Erro ao salvar usuário: ' + (error.response?.data?.message || error.message))
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleEditMonitorado = (usuario) => {
    setEditingUser(usuario)
    setFormData({
      nome: usuario.nome,
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
          Gerenciamento de Usuários
        </h1>
        <div className="flex space-x-3">
          {activeTab === 'monitorados' && (
            <button
              onClick={() => setShowForm(!showForm)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              {showForm ? 'Cancelar' : 'Novo Usuário Monitorado'}
            </button>
          )}
          
          {activeTab === 'sistema' && (
            <>
              <button
                onClick={() => setShowSystemForm(!showSystemForm)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                {showSystemForm ? 'Cancelar' : 'Novo Usuário'}
              </button>
              
              <button
                onClick={toggleInactiveUsers}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600"
              >
                {showInactiveUsers ? 'Ocultar Inativos' : 'Ver Inativos'}
              </button>
            </>
          )}
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-md ${message.includes('sucesso') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('monitorados')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'monitorados'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Usuários Monitorados ({usuariosMonitorados.length})
          </button>
          <button
            onClick={() => setActiveTab('sistema')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'sistema'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
          >
            Usuários do Sistema ({usuarios.length})
          </button>
        </nav>
      </div>

      {/* Form para usuários monitorados */}
      {showForm && activeTab === 'monitorados' && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {editingUser ? 'Editar Usuário Monitorado' : 'Novo Usuário Monitorado'}
          </h2>

          <form onSubmit={handleSubmitMonitorado} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Nome do Usuário
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Cargo
                </label>
                <input
                  type="text"
                  value={formData.cargo}
                  onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Departamento (setor)
                </label>
                <select
                  value={formData.departamento_id}
                  onChange={(e) => setFormData({ ...formData, departamento_id: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Selecione um departamento</option>
                  {departments.map(dept => (
                    <option key={dept.id} value={dept.id}>{dept.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Valor de contrato (R$/dia)
                </label>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Para cálculo do custo de produtividade
                </p>
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

      {/* Pendências de usuários monitorados */}
      {activeTab === 'monitorados' && (() => {
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

      {/* Lista de Usuários Monitorados */}
      {activeTab === 'monitorados' && (
        <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              Usuários Monitorados
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Usuários cujas atividades estão sendo monitoradas pelo sistema
            </p>
          </div>

          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {usuariosMonitorados.map((usuario) => (
              <li key={usuario.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className="w-10 h-10 bg-indigo-500 rounded-full flex items-center justify-center">
                          <span className="text-white font-medium text-sm">
                            {usuario.nome.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {usuario.nome}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                          {usuario.cargo || 'Sem cargo definido'}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {getDepartmentName(usuario.departamento_id)}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      usuario.ativo 
                        ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' 
                        : 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                    }`}>
                      {usuario.ativo ? 'Ativo' : 'Inativo'}
                    </span>

                    <button
                      onClick={() => handleEditMonitorado(usuario)}
                      className="text-indigo-600 hover:text-indigo-900 text-sm"
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
                Nenhum usuário monitorado encontrado. Crie o primeiro usuário para começar!
              </p>
            </div>
          )}
        </div>
      )}

      {/* Formulário de Usuários do Sistema */}
      {activeTab === 'sistema' && showSystemForm && (
        <div className="bg-white dark:bg-gray-800 shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              {editingSystemUser ? 'Editar Usuário do Sistema' : 'Novo Usuário do Sistema'}
            </h3>
            <div className="mt-6">
              <form onSubmit={handleSubmitSystemUser} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label htmlFor="system-nome" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Nome de Usuário *
                    </label>
                    <input
                      type="text"
                      id="system-nome"
                      required
                      value={systemFormData.nome}
                      onChange={(e) => setSystemFormData({ ...systemFormData, nome: e.target.value })}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Digite o nome de usuário"
                    />
                  </div>

                  <div>
                    <label htmlFor="system-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Email
                    </label>
                    <input
                      type="email"
                      id="system-email"
                      value={systemFormData.email}
                      onChange={(e) => setSystemFormData({ ...systemFormData, email: e.target.value })}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Digite o email (opcional)"
                    />
                  </div>

                  <div>
                    <label htmlFor="system-senha" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {editingSystemUser ? 'Nova Senha (deixe vazio para manter)' : 'Senha *'}
                    </label>
                    <input
                      type="password"
                      id="system-senha"
                      required={!editingSystemUser}
                      value={systemFormData.senha}
                      onChange={(e) => setSystemFormData({ ...systemFormData, senha: e.target.value })}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Digite a senha (mín. 6 caracteres)"
                      minLength={6}
                    />
                  </div>

                  <div>
                    <label htmlFor="system-departamento" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Departamento
                    </label>
                    <select
                      id="system-departamento"
                      value={systemFormData.departamento_id}
                      onChange={(e) => setSystemFormData({ ...systemFormData, departamento_id: e.target.value })}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    >
                      <option value="">Selecione um departamento</option>
                      {departments.map((dept) => (
                        <option key={dept.id} value={dept.id}>
                          {dept.nome}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={handleCancelSystemForm}
                    className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    {editingSystemUser ? 'Atualizar' : 'Criar'} Usuário
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Lista de Usuários do Sistema */}
      {activeTab === 'sistema' && (
        <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              Usuários do Sistema
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Usuários com acesso ao painel administrativo
            </p>
          </div>

          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {usuarios.map((usuario) => (
              <li key={usuario.usuario_id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                          <span className="text-white font-bold text-lg">
                            {usuario.usuario.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4 flex-1">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">
                            {usuario.usuario}
                          </p>
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                            Admin
                          </span>
                        </div>
                        {usuario.email && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                            📧 {usuario.email}
                          </p>
                        )}
                        <div className="flex items-center space-x-4 mt-1">
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            🏢 {usuario.departamento ? usuario.departamento.nome : 'Sem departamento'}
                          </p>
                          {usuario.created_at && (
                            <p className="text-xs text-gray-400 dark:text-gray-500">
                              📅 Criado em {usuario.created_at}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleEditSystemUser(usuario)}
                      className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200 dark:hover:bg-blue-800 transition-colors"
                      title="Editar usuário"
                    >
                      ✏️ Editar
                    </button>
                    
                    <button
                      onClick={() => handleResetPassword(usuario)}
                      className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-yellow-700 bg-yellow-100 hover:bg-yellow-200 dark:bg-yellow-900 dark:text-yellow-200 dark:hover:bg-yellow-800 transition-colors"
                      title="Resetar senha"
                    >
                      🔑 Reset
                    </button>
                    
                    <button
                      onClick={() => handleDeleteSystemUser(usuario)}
                      className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:text-red-200 dark:hover:bg-red-800 transition-colors"
                      title="Desativar usuário"
                    >
                      🗑️ Desativar
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

          {usuarios.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 dark:text-gray-500">
                <div className="mx-auto h-16 w-16 mb-4 text-6xl">
                  👥
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Nenhum usuário do sistema
                </h3>
                <p className="text-sm mb-4">
                  Crie o primeiro usuário administrativo para começar
                </p>
                <button
                  onClick={() => setShowSystemForm(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                >
                  Criar Primeiro Usuário
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Lista de Usuários Inativos */}
      {activeTab === 'sistema' && showInactiveUsers && (
        <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              Usuários Inativos
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Usuários desativados do sistema
            </p>
          </div>

          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {inactiveUsers.map((usuario) => (
              <li key={usuario.usuario_id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 opacity-75">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className="w-12 h-12 bg-gray-400 rounded-full flex items-center justify-center">
                          <span className="text-white font-bold text-lg">
                            {usuario.usuario.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4 flex-1">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-semibold text-gray-500 dark:text-gray-400">
                            {usuario.usuario}
                          </p>
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                            Inativo
                          </span>
                        </div>
                        {usuario.email && (
                          <p className="text-sm text-gray-400 dark:text-gray-500 truncate">
                            📧 {usuario.email}
                          </p>
                        )}
                        <div className="flex items-center space-x-4 mt-1">
                          <p className="text-xs text-gray-400 dark:text-gray-500">
                            🏢 {usuario.departamento ? usuario.departamento.nome : 'Sem departamento'}
                          </p>
                          {usuario.updated_at && (
                            <p className="text-xs text-gray-400 dark:text-gray-500">
                              🗑️ Desativado em {usuario.updated_at}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleReactivateSystemUser(usuario)}
                      className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 dark:bg-green-900 dark:text-green-200 dark:hover:bg-green-800 transition-colors"
                      title="Reativar usuário"
                    >
                      🔄 Reativar
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          {inactiveUsers.length === 0 && (
            <div className="text-center py-8">
              <p className="text-gray-500 dark:text-gray-400">
                Nenhum usuário inativo encontrado.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default UserManagement