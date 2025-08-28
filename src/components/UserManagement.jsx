import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format } from 'date-fns'

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
    departamento_id: ''
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [usuariosRes, monitoradosRes, departmentsRes] = await Promise.all([
        api.get('/usuarios'),
        api.get('/usuarios-monitorados'),
        api.get('/departamentos')
      ])

      setUsuarios(usuariosRes.data || [])
      setUsuariosMonitorados(monitoradosRes.data || [])
      setDepartments(departmentsRes.data || [])
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      setMessage('Erro ao carregar dados')
    } finally {
      setLoading(false)
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
      departamento_id: usuario.departamento_id || ''
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
      departamento_id: ''
    })
    setEditingUser(null)
    setShowForm(false)
  }

  const getDepartmentName = (departamentoId) => {
    const dept = departments.find(d => d.id === departamentoId)
    return dept ? dept.nome : 'Sem Departamento'
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
        {activeTab === 'monitorados' && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {showForm ? 'Cancelar' : 'Novo Usuário Monitorado'}
          </button>
        )}
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
                  Departamento
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
                    Criado em: {format(new Date(usuario.created_at), 'dd/MM/yyyy HH:mm')}
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
                        <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                          <span className="text-white font-medium text-sm">
                            {usuario.usuario.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {usuario.usuario}
                        </p>
                        {usuario.email && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                            {usuario.email}
                          </p>
                        )}
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {usuario.departamento ? usuario.departamento.nome : 'Sem departamento'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <select
                      value={usuario.departamento_id || ''}
                      onChange={(e) => handleUpdateUsuarioDepartment(usuario.usuario_id, e.target.value)}
                      className="text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">Sem departamento</option>
                      {departments.map(dept => (
                        <option key={dept.id} value={dept.id}>{dept.nome}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {usuario.created_at && (
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    Criado em: {format(new Date(usuario.created_at), 'dd/MM/yyyy HH:mm')}
                  </div>
                )}
              </li>
            ))}
          </ul>

          {usuarios.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 dark:text-gray-400">
                Nenhum usuário do sistema encontrado.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default UserManagement