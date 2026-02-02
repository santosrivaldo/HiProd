
import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'

const TokenManagement = () => {
  const { user } = useAuth()
  const [tokens, setTokens] = useState([])
  const [endpoints, setEndpoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingToken, setEditingToken] = useState(null)
  const [message, setMessage] = useState('')
  const [newToken, setNewToken] = useState(null)
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
    expires_days: '',
    permissions: []
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [tokensResponse, endpointsResponse] = await Promise.all([
        api.get('/api-tokens').catch(() => ({ data: [] })),
        api.get('/api-tokens/endpoints').catch(() => ({ data: [] }))
      ])

      setTokens(tokensResponse.data || [])
      setEndpoints(endpointsResponse.data || [])
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      setTokens([])
      setEndpoints([])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      const data = {
        ...formData,
        expires_days: formData.expires_days ? parseInt(formData.expires_days) : null,
        permissions: formData.permissions.filter(p => p.endpoint && p.method)
      }

      if (editingToken) {
        await api.put(`/api-tokens/${editingToken.id}`, data)
        setMessage('Token atualizado com sucesso!')
      } else {
        const response = await api.post('/api-tokens', data)
        if (response.data && response.data.token) {
          setNewToken(response.data.token)
          setMessage('')
        } else {
          setMessage('Token criado, mas não foi retornado. Verifique os logs do servidor.')
        }
      }

      fetchData()
      resetForm()
      setTimeout(() => setMessage(''), 5000)
    } catch (error) {
      console.error('Erro ao salvar token:', error)
      setMessage('Erro ao salvar token: ' + (error.response?.data?.message || error.message))
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleEdit = (token) => {
    setEditingToken(token)
    setFormData({
      nome: token.nome,
      descricao: token.descricao || '',
      expires_days: '',
      permissions: token.permissions || []
    })
    setShowForm(true)
    setNewToken(null)
  }

  const handleDelete = async (tokenId) => {
    if (!window.confirm('Tem certeza que deseja excluir este token?')) {
      return
    }

    try {
      await api.delete(`/api-tokens/${tokenId}`)
      setMessage('Token excluído com sucesso!')
      fetchData()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao excluir token:', error)
      setMessage('Erro ao excluir token: ' + (error.response?.data?.message || error.message))
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleToggle = async (tokenId, currentStatus) => {
    try {
      await api.post(`/api-tokens/${tokenId}/toggle`)
      setMessage(`Token ${currentStatus ? 'desativado' : 'ativado'} com sucesso!`)
      fetchData()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao alterar status do token:', error)
      setMessage('Erro ao alterar status: ' + (error.response?.data?.message || error.message))
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const resetForm = () => {
    setFormData({
      nome: '',
      descricao: '',
      expires_days: '',
      permissions: []
    })
    setEditingToken(null)
    setShowForm(false)
    setNewToken(null)
  }

  const addPermission = () => {
    setFormData({
      ...formData,
      permissions: [...formData.permissions, { endpoint: '', method: 'GET' }]
    })
  }

  const addQuickPermission = (endpoint, method = 'GET') => {
    // Verificar se já existe
    if (formData.permissions.some(p => p.endpoint === endpoint && p.method === method)) {
      return
    }
    
    setFormData({
      ...formData,
      permissions: [...formData.permissions, { endpoint, method }]
    })
  }

  const removePermission = (index) => {
    setFormData({
      ...formData,
      permissions: formData.permissions.filter((_, i) => i !== index)
    })
  }

  const updatePermission = (index, field, value) => {
    const newPermissions = [...formData.permissions]
    newPermissions[index] = { ...newPermissions[index], [field]: value }
    setFormData({ ...formData, permissions: newPermissions })
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setMessage('Token copiado para a área de transferência!')
    setTimeout(() => setMessage(''), 3000)
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600 dark:text-gray-400">Carregando...</div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Gerenciamento de Tokens de API
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Crie e gerencie tokens de API com permissões restritivas por endpoint
          </p>
        </div>
        <button
          onClick={() => {
            resetForm()
            setShowForm(true)
          }}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700"
        >
          Criar Novo Token
        </button>
      </div>

      {message && (
        <div className={`mb-4 p-4 rounded-md ${
          message.includes('Erro') 
            ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200' 
            : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200'
        }`}>
          {message}
        </div>
      )}

      {newToken && (
        <div className="mb-4 p-6 bg-yellow-50 dark:bg-yellow-900/30 border-2 border-yellow-400 dark:border-yellow-600 rounded-lg">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-2xl">🔑</span>
                <p className="font-bold text-lg text-yellow-900 dark:text-yellow-100">
                  Token de API Gerado com Sucesso!
                </p>
              </div>
              <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-3">
                ⚠️ <strong>IMPORTANTE:</strong> Este token será exibido apenas uma vez. Copie e guarde em local seguro!
              </p>
              <div className="relative">
                <code className="block p-4 bg-white dark:bg-gray-800 border border-yellow-300 dark:border-yellow-700 rounded-md text-sm font-mono break-all select-all">
                  {newToken}
                </code>
                <button
                  onClick={() => {
                    copyToClipboard(newToken)
                    setMessage('Token copiado para a área de transferência!')
                  }}
                  className="mt-3 w-full bg-yellow-600 hover:bg-yellow-700 text-white font-semibold px-4 py-2 rounded-md transition-colors"
                >
                  📋 Copiar Token
                </button>
              </div>
            </div>
            <button
              onClick={() => setNewToken(null)}
              className="text-yellow-600 dark:text-yellow-400 hover:text-yellow-800 dark:hover:text-yellow-200 text-xl font-bold"
              title="Fechar"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {showForm && (
        <div className="mb-6 bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            {editingToken ? 'Editar Token' : 'Criar Novo Token'}
          </h2>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Nome do Token *
                </label>
                <input
                  type="text"
                  required
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Ex: Token para integração externa"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Descrição
                </label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  rows="3"
                  placeholder="Descrição do token..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Expira em (dias) - Deixe vazio para não expirar
                </label>
                <input
                  type="number"
                  min="1"
                  value={formData.expires_days}
                  onChange={(e) => setFormData({ ...formData, expires_days: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Ex: 30"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Permissões por Endpoint *
                  </label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => addQuickPermission('/atividades/*', '*')}
                      className="text-xs bg-blue-200 dark:bg-blue-800 text-blue-700 dark:text-blue-300 px-2 py-1 rounded hover:bg-blue-300 dark:hover:bg-blue-700"
                      title="Adicionar acesso a todas as atividades"
                    >
                      + Atividades
                    </button>
                    <button
                      type="button"
                      onClick={() => addQuickPermission('/api/v1/*', '*')}
                      className="text-xs bg-green-200 dark:bg-green-800 text-green-700 dark:text-green-300 px-2 py-1 rounded hover:bg-green-300 dark:hover:bg-green-700"
                      title="Adicionar acesso a todos os endpoints V1"
                    >
                      + V1 API
                    </button>
                    <button
                      type="button"
                      onClick={addPermission}
                      className="text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-3 py-1 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                    >
                      + Adicionar
                    </button>
                  </div>
                </div>

                {formData.permissions.length === 0 && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                    Adicione pelo menos uma permissão
                  </p>
                )}

                {formData.permissions.map((perm, index) => (
                  <div key={index} className="flex gap-2 mb-2 items-start">
                    <div className="flex-1">
                      <select
                        value={perm.endpoint}
                        onChange={(e) => updatePermission(index, 'endpoint', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        required
                      >
                        <option value="">Selecione um endpoint...</option>
                        <optgroup label="Endpoints Específicos">
                          {endpoints.filter(ep => !ep.endpoint.includes('*')).map((ep) => (
                            <option key={`${ep.endpoint}-${ep.method}`} value={ep.endpoint}>
                              {ep.endpoint} ({ep.method}) - {ep.description}
                            </option>
                          ))}
                        </optgroup>
                        <optgroup label="Wildcards (Acesso a Múltiplos Endpoints)">
                          {endpoints.filter(ep => ep.endpoint.includes('*')).map((ep) => (
                            <option key={`${ep.endpoint}-${ep.method}`} value={ep.endpoint}>
                              {ep.endpoint} ({ep.method}) - {ep.description}
                            </option>
                          ))}
                        </optgroup>
                      </select>
                    </div>
                    <div className="w-32">
                      <select
                        value={perm.method}
                        onChange={(e) => updatePermission(index, 'method', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        required
                      >
                        <option value="GET">GET</option>
                        <option value="POST">POST</option>
                        <option value="PUT">PUT</option>
                        <option value="PATCH">PATCH</option>
                        <option value="DELETE">DELETE</option>
                        <option value="*">TODOS (*)</option>
                      </select>
                    </div>
                    <button
                      type="button"
                      onClick={() => removePermission(index)}
                      className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                      title="Remover permissão"
                    >
                      ✕
                    </button>
                  </div>
                ))}

                {endpoints.length > 0 && (
                  <details className="mt-2">
                    <summary className="text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
                      Ver endpoints disponíveis
                    </summary>
                    <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded">
                      {endpoints.map((ep, idx) => (
                        <div key={idx} className="text-sm text-gray-700 dark:text-gray-300 mb-1">
                          <code className="bg-gray-200 dark:bg-gray-800 px-2 py-1 rounded">
                            {ep.method} {ep.endpoint}
                          </code>
                          <span className="ml-2 text-gray-500 dark:text-gray-400">
                            - {ep.description}
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>

            <div className="mt-6 flex gap-2">
              <button
                type="submit"
                className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700"
              >
                {editingToken ? 'Atualizar' : 'Criar Token'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-md hover:bg-gray-400 dark:hover:bg-gray-500"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Descrição
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Permissões
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Último Uso
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {tokens.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                  Nenhum token criado ainda
                </td>
              </tr>
            ) : (
              tokens.map((token) => (
                <tr key={token.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {token.nome}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {token.descricao || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex flex-wrap gap-1">
                      {token.permissions?.slice(0, 3).map((perm, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs"
                        >
                          {perm.method} {perm.endpoint}
                        </span>
                      ))}
                      {token.permissions?.length > 3 && (
                        <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
                          +{token.permissions.length - 3} mais
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        token.ativo
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}
                    >
                      {token.ativo ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {token.last_used_at || 'Nunca'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(token)}
                        className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleToggle(token.id, token.ativo)}
                        className={`${
                          token.ativo
                            ? 'text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300'
                            : 'text-green-600 dark:text-green-400 hover:text-green-900 dark:hover:text-green-300'
                        }`}
                      >
                        {token.ativo ? 'Desativar' : 'Ativar'}
                      </button>
                      <button
                        onClick={() => handleDelete(token.id)}
                        className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300"
                      >
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default TokenManagement

