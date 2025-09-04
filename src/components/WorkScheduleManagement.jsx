
import React, { useState, useEffect } from 'react'
import api from '../services/api'
import LoadingSpinner from './LoadingSpinner'
import { ClockIcon, PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline'

export default function WorkScheduleManagement() {
  const [escalas, setEscalas] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [editingEscala, setEditingEscala] = useState(null)
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
    horario_inicio_trabalho: '08:00',
    horario_fim_trabalho: '18:00',
    dias_trabalho: '1,2,3,4,5'
  })

  const diasSemana = [
    { value: '1', label: 'Segunda' },
    { value: '2', label: 'Terça' },
    { value: '3', label: 'Quarta' },
    { value: '4', label: 'Quinta' },
    { value: '5', label: 'Sexta' },
    { value: '6', label: 'Sábado' },
    { value: '7', label: 'Domingo' }
  ]

  useEffect(() => {
    loadEscalas()
    loadUsuarios()
  }, [])

  const loadEscalas = async () => {
    setLoading(true)
    try {
      const response = await api.get('/escalas')
      setEscalas(response.data || [])
    } catch (error) {
      console.error('Erro ao carregar escalas:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadUsuarios = async () => {
    try {
      const response = await api.get('/usuarios-monitorados')
      setUsuarios(response.data || [])
    } catch (error) {
      console.error('Erro ao carregar usuários:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      if (editingEscala) {
        await api.put(`/escalas/${editingEscala.id}`, formData)
      } else {
        await api.post('/escalas', formData)
      }
      
      await loadEscalas()
      resetForm()
      setShowCreateModal(false)
    } catch (error) {
      console.error('Erro ao salvar escala:', error)
      alert('Erro ao salvar escala: ' + (error.response?.data?.message || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (escalaId) => {
    if (!confirm('Tem certeza que deseja excluir esta escala?')) return
    
    setLoading(true)
    try {
      await api.delete(`/escalas/${escalaId}`)
      await loadEscalas()
    } catch (error) {
      console.error('Erro ao excluir escala:', error)
      alert('Erro ao excluir escala: ' + (error.response?.data?.message || error.message))
    } finally {
      setLoading(false)
    }
  }

  const assignEscalaToUser = async (usuarioId, escalaId) => {
    setLoading(true)
    try {
      await api.put(`/usuarios-monitorados/${usuarioId}`, {
        escala_trabalho_id: escalaId
      })
      
      await loadUsuarios()
      alert('Escala atribuída com sucesso!')
    } catch (error) {
      console.error('Erro ao atribuir escala:', error)
      alert('Erro ao atribuir escala: ' + (error.response?.data?.message || error.message))
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      nome: '',
      descricao: '',
      horario_inicio_trabalho: '08:00',
      horario_fim_trabalho: '18:00',
      dias_trabalho: '1,2,3,4,5'
    })
    setEditingEscala(null)
  }

  const openEditModal = (escala) => {
    setEditingEscala(escala)
    setFormData({
      nome: escala.nome,
      descricao: escala.descricao || '',
      horario_inicio_trabalho: escala.horario_inicio_trabalho?.substring(0, 5) || '08:00',
      horario_fim_trabalho: escala.horario_fim_trabalho?.substring(0, 5) || '18:00',
      dias_trabalho: escala.dias_trabalho || '1,2,3,4,5'
    })
    setShowCreateModal(true)
  }

  const handleDiasChange = (diaValue) => {
    const diasArray = formData.dias_trabalho.split(',').filter(d => d)
    const index = diasArray.indexOf(diaValue)
    
    if (index > -1) {
      diasArray.splice(index, 1)
    } else {
      diasArray.push(diaValue)
    }
    
    setFormData({
      ...formData,
      dias_trabalho: diasArray.sort().join(',')
    })
  }

  const formatDiasSemana = (diasString) => {
    if (!diasString) return 'Nenhum'
    
    const dias = diasString.split(',')
    return dias.map(dia => {
      const diaObj = diasSemana.find(d => d.value === dia)
      return diaObj ? diaObj.label : dia
    }).join(', ')
  }

  const calcularHorasTrabalho = (inicio, fim) => {
    const [horaInicio, minutoInicio] = inicio.split(':').map(Number)
    const [horaFim, minutoFim] = fim.split(':').map(Number)
    
    const inicioMinutos = horaInicio * 60 + minutoInicio
    const fimMinutos = horaFim * 60 + minutoFim
    
    let totalMinutos = fimMinutos - inicioMinutos
    if (totalMinutos < 0) totalMinutos += 24 * 60 // Para horários que passam da meia-noite
    
    // Subtrair 1 hora de almoço se for mais de 6 horas de trabalho
    if (totalMinutos > 6 * 60) {
      totalMinutos -= 60
    }
    
    const horas = Math.floor(totalMinutos / 60)
    const minutos = totalMinutos % 60
    
    return `${horas}h${minutos > 0 ? ` ${minutos}m` : ''}`
  }

  if (loading && escalas.length === 0) {
    return <LoadingSpinner size="xl" text="Carregando escalas..." fullScreen />
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Gerenciamento de Escalas
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Configure e gerencie as escalas de trabalho dos colaboradores
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowAssignModal(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 flex items-center space-x-2"
          >
            <ClockIcon className="h-4 w-4" />
            <span>Atribuir Escalas</span>
          </button>
          <button
            onClick={() => {
              resetForm()
              setShowCreateModal(true)
            }}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 flex items-center space-x-2"
          >
            <PlusIcon className="h-4 w-4" />
            <span>Nova Escala</span>
          </button>
        </div>
      </div>

      {/* Lista de Escalas */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Escalas Cadastradas
          </h2>
        </div>
        
        {escalas.length === 0 ? (
          <div className="text-center py-12">
            <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
              Nenhuma escala cadastrada
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Crie sua primeira escala de trabalho
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Nome
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Horário
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Dias da Semana
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Carga Horária
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {escalas.map((escala) => (
                  <tr key={escala.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {escala.nome}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {escala.descricao}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {escala.horario_inicio_trabalho?.substring(0, 5)} - {escala.horario_fim_trabalho?.substring(0, 5)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                      {formatDiasSemana(escala.dias_trabalho)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {calcularHorasTrabalho(
                        escala.horario_inicio_trabalho?.substring(0, 5) || '08:00',
                        escala.horario_fim_trabalho?.substring(0, 5) || '18:00'
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-2">
                        <button
                          onClick={() => openEditModal(escala)}
                          className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(escala.id)}
                          className="text-red-600 hover:text-red-900 dark:text-red-400"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal de Criação/Edição */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              {editingEscala ? 'Editar Escala' : 'Nova Escala'}
            </h3>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Nome da Escala
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Descrição
                </label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Horário Início
                  </label>
                  <input
                    type="time"
                    value={formData.horario_inicio_trabalho}
                    onChange={(e) => setFormData({ ...formData, horario_inicio_trabalho: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Horário Fim
                  </label>
                  <input
                    type="time"
                    value={formData.horario_fim_trabalho}
                    onChange={(e) => setFormData({ ...formData, horario_fim_trabalho: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Dias da Semana
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {diasSemana.map((dia) => (
                    <label key={dia.value} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.dias_trabalho.split(',').includes(dia.value)}
                        onChange={() => handleDiasChange(dia.value)}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                        {dia.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    resetForm()
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:opacity-50"
                >
                  {loading ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Atribuição */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-[600px] shadow-lg rounded-md bg-white dark:bg-gray-800 max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              Atribuir Escalas aos Colaboradores
            </h3>
            
            <div className="space-y-4">
              {usuarios.map((usuario) => (
                <div key={usuario.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {usuario.nome}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {usuario.cargo || 'Sem cargo definido'}
                    </div>
                  </div>
                  <select
                    value={usuario.escala_trabalho_id || ''}
                    onChange={(e) => {
                      const escalaId = e.target.value ? parseInt(e.target.value) : null
                      assignEscalaToUser(usuario.id, escalaId)
                    }}
                    className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                  >
                    <option value="">Sem escala</option>
                    {escalas.map((escala) => (
                      <option key={escala.id} value={escala.id}>
                        {escala.nome}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowAssignModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-md"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
