import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'

const TagManagement = () => {
  const { user } = useAuth()
  const [tags, setTags] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingTag, setEditingTag] = useState(null)
  const [message, setMessage] = useState('')
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
    cor: '#6B7280',
    produtividade: 'neutral',
    departamento_id: '',
    palavras_chave: ['']
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [tagsRes, departmentsRes] = await Promise.all([
        api.get('/tags'),
        api.get('/departamentos')
      ])

      setTags(tagsRes.data || [])
      setDepartments(departmentsRes.data || [])
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      setMessage('Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      const dataToSend = {
        ...formData,
        palavras_chave: formData.palavras_chave
          .filter(palavra => palavra.trim())
          .map(palavra => ({ palavra: palavra.trim(), peso: 1 }))
      }

      if (editingTag) {
        await api.put(`/tags/${editingTag.id}`, dataToSend)
        setMessage('Tag atualizada com sucesso!')
      } else {
        await api.post('/tags', dataToSend)
        setMessage('Tag criada com sucesso!')
      }

      fetchData()
      resetForm()
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao salvar tag:', error)
      setMessage('Erro ao salvar tag: ' + (error.response?.data?.message || error.message))
      setTimeout(() => setMessage(''), 5000)
    }
  }

  const handleEdit = (tag) => {
    setEditingTag(tag)
    setFormData({
      nome: tag.nome,
      descricao: tag.descricao || '',
      cor: tag.cor,
      produtividade: tag.produtividade,
      departamento_id: tag.departamento_id || '',
      palavras_chave: tag.palavras_chave?.map(p => p.palavra) || ['']
    })
    setShowForm(true)
  }

  const handleDelete = async (tagId) => {
    if (window.confirm('Tem certeza que deseja excluir esta tag?')) {
      try {
        await api.delete(`/tags/${tagId}`)
        setMessage('Tag excluída com sucesso!')
        fetchData()
        setTimeout(() => setMessage(''), 3000)
      } catch (error) {
        console.error('Erro ao excluir tag:', error)
        setMessage('Erro ao excluir tag')
        setTimeout(() => setMessage(''), 3000)
      }
    }
  }

  const resetForm = () => {
    setFormData({
      nome: '',
      descricao: '',
      cor: '#6B7280',
      produtividade: 'neutral',
      departamento_id: '',
      palavras_chave: ['']
    })
    setEditingTag(null)
    setShowForm(false)
  }

  const addPalavraChave = () => {
    setFormData({
      ...formData,
      palavras_chave: [...formData.palavras_chave, '']
    })
  }

  const removePalavraChave = (index) => {
    setFormData({
      ...formData,
      palavras_chave: formData.palavras_chave.filter((_, i) => i !== index)
    })
  }

  const updatePalavraChave = (index, value) => {
    const newPalavras = [...formData.palavras_chave]
    newPalavras[index] = value
    setFormData({
      ...formData,
      palavras_chave: newPalavras
    })
  }

  const getProdutividadeColor = (produtividade) => {
    switch (produtividade) {
      case 'productive': return 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
      case 'nonproductive': return 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
      case 'neutral': return 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100'
    }
  }

  const getProdutividadeLabel = (produtividade) => {
    switch (produtividade) {
      case 'productive': return 'Produtivo'
      case 'nonproductive': return 'Não Produtivo'
      case 'neutral': return 'Neutro'
      default: return 'Desconhecido'
    }
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
          Gerenciamento de Tags
        </h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          {showForm ? 'Cancelar' : 'Nova Tag'}
        </button>
      </div>

      {message && (
        <div className={`p-4 rounded-md ${message.includes('sucesso') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message}
        </div>
      )}

      {showForm && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {editingTag ? 'Editar Tag' : 'Nova Tag'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Nome da Tag
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
                  Produtividade
                </label>
                <select
                  value={formData.produtividade}
                  onChange={(e) => setFormData({ ...formData, produtividade: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="productive">Produtivo</option>
                  <option value="nonproductive">Não Produtivo</option>
                  <option value="neutral">Neutro</option>
                </select>
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
                  <option value="">Global (Todos os Departamentos)</option>
                  {departments.map(dept => (
                    <option key={dept.id} value={dept.id}>{dept.nome}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Cor
                </label>
                <input
                  type="color"
                  value={formData.cor}
                  onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
                  className="mt-1 block w-full h-10 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Descrição
              </label>
              <textarea
                value={formData.descricao}
                onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                rows={3}
                className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Palavras-chave
              </label>
              {formData.palavras_chave.map((palavra, index) => (
                <div key={index} className="flex items-center space-x-2 mb-2">
                  <input
                    type="text"
                    value={palavra}
                    onChange={(e) => updatePalavraChave(index, e.target.value)}
                    placeholder="Digite uma palavra-chave"
                    className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  {formData.palavras_chave.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removePalavraChave(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addPalavraChave}
                className="mt-2 text-sm text-indigo-600 hover:text-indigo-800"
              >
                + Adicionar palavra-chave
              </button>
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
                {editingTag ? 'Atualizar' : 'Criar'} Tag
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Lista de Tags */}
      <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
          {tags && tags.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-600">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Nome
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Produtividade
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Departamento
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Palavras-chave
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {tags.map((tag) => (
                  <tr key={tag.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div 
                          className="w-4 h-4 rounded-full mr-3"
                          style={{ backgroundColor: tag.cor }}
                        />
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {tag.nome}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        tag.produtividade === 'productive' 
                          ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' 
                          : tag.produtividade === 'nonproductive'
                          ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                          : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'
                      }`}>
                        {tag.produtividade === 'productive' ? 'Produtiva' : 
                         tag.produtividade === 'nonproductive' ? 'Não Produtiva' : 'Neutra'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {tag.departamento_nome || 'Global'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {tag.palavras_chave?.length > 0 
                        ? tag.palavras_chave.map(p => p.palavra).join(', ')
                        : 'Nenhuma'
                      }
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        tag.ativo 
                          ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' 
                          : 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100'
                      }`}>
                        {tag.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleEdit(tag)}
                        className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 mr-4"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(tag.id)}
                        className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300"
                      >
                        Excluir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12 bg-white dark:bg-gray-800">
              <div className="text-gray-400 dark:text-gray-500">
                <svg className="mx-auto h-12 w-12 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a.997.997 0 01-1.414 0l-7-7A1.997 1.997 0 013 12V7a4 4 0 014-4z" />
                </svg>
                <p className="text-sm font-medium">Nenhuma tag encontrada</p>
                <p className="text-xs mt-1">Crie sua primeira tag para classificar atividades automaticamente</p>
              </div>
            </div>
          )}
        </div>
    </div>
  )
}

export default TagManagement