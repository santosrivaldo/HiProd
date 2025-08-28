import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format } from 'date-fns'
import { MagnifyingGlassIcon, FunnelIcon } from '@heroicons/react/24/outline'

const activityTypes = [
  { value: 'all', label: 'Todos' },
  { value: 'productive', label: 'Produtivo' },
  { value: 'nonproductive', label: 'Não Produtivo' },
  { value: 'neutral', label: 'Neutro' },
  { value: 'unclassified', label: 'Não Classificado' },
  { value: 'idle', label: 'Ocioso' }
]

export default function ActivityManagement() {
  const { user } = useAuth()
  const [activities, setActivities] = useState([])
  const [filteredActivities, setFilteredActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [userFilter, setUserFilter] = useState('all')
  const [users, setUsers] = useState([])
  const [message, setMessage] = useState('')

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [activities, searchTerm, dateFilter, typeFilter, userFilter])

  const fetchData = async () => {
    try {
      const [activitiesRes, usersRes] = await Promise.all([
        api.get('/atividades'),
        api.get('/usuarios')
      ])

      setActivities(activitiesRes.data || [])
      setUsers(usersRes.data || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching data:', error)
      setActivities([])
      setUsers([])
      setLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...activities]

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(activity =>
        activity.active_window.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (activity.usuario_monitorado_nome && activity.usuario_monitorado_nome.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (activity.cargo && activity.cargo.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    }

    // Date filter
    if (dateFilter) {
      filtered = filtered.filter(activity =>
        activity.horario.startsWith(dateFilter)
      )
    }

    // Type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter(activity => {
        const activityType = getActivityType(activity)
        return activityType.type === typeFilter
      })
    }

    // User filter
    if (userFilter !== 'all') {
      filtered = filtered.filter(activity =>
        activity.usuario_id === userFilter
      )
    }

    setFilteredActivities(filtered)
  }

  const getActivityType = (activity) => {
    // Check if activity has classification from API
    if (activity.categoria && activity.produtividade) {
      switch (activity.produtividade) {
        case 'productive':
          return { type: 'productive', label: 'Produtivo', color: 'bg-green-100 text-green-800' }
        case 'nonproductive':
          return { type: 'nonproductive', label: 'Não Produtivo', color: 'bg-red-100 text-red-800' }
        case 'neutral':
          return { type: 'neutral', label: 'Neutro', color: 'bg-blue-100 text-blue-800' }
        default:
          return { type: 'unclassified', label: 'Não Classificado', color: 'bg-yellow-100 text-yellow-800' }
      }
    }

    // Fallback to idle classification
    if (activity.ociosidade >= 600) {
      return { type: 'idle', label: 'Ocioso', color: 'bg-gray-100 text-gray-800' }
    }

    return { type: 'unclassified', label: 'Não Classificado', color: 'bg-yellow-100 text-yellow-800' }
  }

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const updateActivityClassification = async (activityId, newProductivity) => {
    try {
      await api.patch(`/atividades/${activityId}`, {
        produtividade: newProductivity
      })

      // Atualizar estado local
      setActivities(activities.map(activity => 
        activity.id === activityId 
          ? { ...activity, produtividade: newProductivity }
          : activity
      ))

      setMessage('Classificação atualizada com sucesso!')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao atualizar classificação:', error)
      setMessage('Erro ao atualizar classificação')
      setTimeout(() => setMessage(''), 3000)
    }
  }

  const updateActivityCategory = async (activityId, newCategory) => {
    try {
      await api.patch(`/atividades/${activityId}`, {
        categoria: newCategory
      })

      // Atualizar estado local
      setActivities(activities.map(activity => 
        activity.id === activityId 
          ? { ...activity, categoria: newCategory }
          : activity
      ))

      setMessage('Categoria atualizada com sucesso!')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao atualizar categoria:', error)
      setMessage('Erro ao atualizar categoria')
      setTimeout(() => setMessage(''), 3000)
    }
  }

  const deleteActivity = async (activityId) => {
    if (window.confirm('Tem certeza que deseja excluir esta atividade?')) {
      try {
        await api.delete(`/atividades/${activityId}`)

        // Refresh activities after deletion
        await fetchData()
      } catch (error) {
        console.error('Error deleting activity:', error)
        alert('Erro ao excluir atividade')
      }
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-500"></div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Gerenciamento de Atividades
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Visualize e gerencie todas as atividades registradas
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Buscar por janela ativa, usuário ou cargo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Date Filter */}
          <div>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Type Filter */}
          <div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            >
              {activityTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* User Filter */}
          <div>
            <select
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="all">Todos os usuários</option>
              {users.map(user => (
                <option key={user.usuario_id} value={user.usuario_id}>
                  {user.usuario}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Mostrando {filteredActivities.length} de {activities.length} registros
          </div>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
          >
            Atualizar
          </button>
        </div>
      </div>

      {/* Activities Table */}
      <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
        <div className="px-4 py-5 sm:p-6">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Data/Hora
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Usuário Monitorado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Cargo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Janela Ativa
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Categoria
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Ociosidade
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Classificação
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredActivities.map((activity, index) => {
                  const activityType = getActivityType(activity)

                  return (
                    <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {format(new Date(activity.horario), 'dd/MM/yyyy HH:mm:ss')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {activity.usuario_monitorado_nome || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {activity.cargo || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        <div className="max-w-xs truncate" title={activity.active_window}>
                          {activity.active_window}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        <div className="flex items-center space-x-2">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            activity.categoria === 'productive' ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' :
                            activity.categoria === 'nonproductive' ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100' :
                            activity.categoria === 'neutral' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100' :
                            'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100'
                          }`}>
                            {activity.categoria || 'unclassified'}
                          </span>
                          <input
                            type="text"
                            value={activity.categoria || ''}
                            onChange={(e) => updateActivityCategory(activity.id, e.target.value)}
                            onBlur={(e) => updateActivityCategory(activity.id, e.target.value)}
                            className="text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-1 focus:ring-indigo-500 w-24"
                            placeholder="Categoria"
                          />
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {formatTime(activity.ociosidade)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${activityType.color}`}>
                            {activityType.label}
                          </span>
                          <select
                            value={activity.produtividade || 'unclassified'}
                            onChange={(e) => updateActivityClassification(activity.id, e.target.value)}
                            className="text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-1 focus:ring-indigo-500"
                          >
                            <option value="productive">Produtivo</option>
                            <option value="nonproductive">Não Produtivo</option>
                            <option value="neutral">Neutro</option>
                            <option value="unclassified">Não Classificado</option>
                          </select>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button 
                          onClick={() => deleteActivity(activity.id)}
                          className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                        >
                          Excluir
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {filteredActivities.length === 0 && (
            <div className="text-center py-12">
              <FunnelIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
                Nenhuma atividade encontrada
              </h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Tente ajustar os filtros para ver mais resultados.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}