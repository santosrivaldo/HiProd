import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format } from 'date-fns'
import { MagnifyingGlassIcon, FunnelIcon, PrinterIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'
import useIntersectionObserver from '../hooks/useIntersectionObserver'
import { exportToCSV, printData, formatTime } from '../utils/exportUtils'

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
  const [loadingMore, setLoadingMore] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [userFilter, setUserFilter] = useState('all')
  const [users, setUsers] = useState([])
  const [message, setMessage] = useState('')
  const [agruparAtividades, setAgruparAtividades] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [totalCount, setTotalCount] = useState(0)
  
  const [loadMoreRef, isLoadMoreVisible] = useIntersectionObserver()

  useEffect(() => {
    fetchData(1, true)
  }, [agruparAtividades])

  useEffect(() => {
    applyFilters()
  }, [activities, searchTerm, dateFilter, typeFilter, userFilter])

  const fetchData = async (page = 1, reset = false) => {
    try {
      if (page === 1) {
        setLoading(true)
      } else {
        setLoadingMore(true)
      }

      const pageSize = 50
      const promises = [
        api.get(`/atividades?limite=${pageSize}&pagina=${page}&agrupar=${agruparAtividades}`)
      ]

      // Buscar usuários apenas na primeira página
      if (page === 1) {
        promises.push(api.get('/usuarios'))
      }

      const responses = await Promise.all(promises)
      const activitiesRes = responses[0]
      
      const newActivities = activitiesRes.data || []
      const total = activitiesRes.headers['x-total-count'] || newActivities.length

      if (page === 1 || reset) {
        setActivities(newActivities)
        setCurrentPage(1)
        if (responses.length > 1) {
          setUsers(responses[1].data || [])
        }
      } else {
        setActivities(prev => [...prev, ...newActivities])
        setCurrentPage(page)
      }

      setTotalCount(total)
      setHasMore(newActivities.length === pageSize)

    } catch (error) {
      console.error('Error fetching data:', error)
      if (page === 1) {
        setActivities([])
        setUsers([])
      }
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  const loadMoreActivities = useCallback(() => {
    if (hasMore && !loadingMore && !loading) {
      fetchData(currentPage + 1, false)
    }
  }, [hasMore, loadingMore, loading, currentPage])

  // Detectar quando o usuário chega ao final da lista
  useEffect(() => {
    if (isLoadMoreVisible && hasMore && !loadingMore) {
      loadMoreActivities()
    }
  }, [isLoadMoreVisible, hasMore, loadingMore, loadMoreActivities])

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

  const handleExportCSV = () => {
    const exportData = filteredActivities.map(activity => ({
      'Data/Hora': format(new Date(activity.horario), 'dd/MM/yyyy HH:mm:ss'),
      'Usuário Monitorado': activity.usuario_monitorado_nome || 'N/A',
      'Cargo': activity.cargo || 'N/A',
      'Janela Ativa': activity.active_window,
      'Categoria': activity.categoria || 'Não Classificado',
      'Ociosidade': formatTime(activity.ociosidade),
      'Classificação': getActivityType(activity).label,
      'Eventos Agrupados': agruparAtividades ? (activity.eventos_agrupados || 1) : 1
    }))

    exportToCSV(exportData, 'atividades')
  }

  const handlePrint = () => {
    const columns = [
      {
        header: 'Data/Hora',
        accessor: (row) => format(new Date(row.horario), 'dd/MM/yyyy HH:mm:ss')
      },
      {
        header: 'Usuário Monitorado',
        accessor: (row) => row.usuario_monitorado_nome || 'N/A'
      },
      {
        header: 'Cargo',
        accessor: (row) => row.cargo || 'N/A'
      },
      {
        header: 'Janela Ativa',
        accessor: (row) => row.active_window
      },
      {
        header: 'Categoria',
        accessor: (row) => row.categoria || 'Não Classificado'
      },
      {
        header: 'Ociosidade',
        accessor: (row) => formatTime(row.ociosidade)
      },
      {
        header: 'Classificação',
        accessor: (row) => getActivityType(row).label,
        className: (row) => {
          const type = getActivityType(row).type
          return type
        }
      }
    ]

    if (agruparAtividades) {
      columns.push({
        header: 'Eventos Agrupados',
        accessor: (row) => row.eventos_agrupados || 1
      })
    }

    printData('Relatório de Atividades', filteredActivities, columns)
  }

  if (loading) {
    return <LoadingSpinner size="xl" text="Carregando atividades..." fullScreen />
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
            Mostrando {filteredActivities.length} de {totalCount > 0 ? totalCount : activities.length} registros
            {hasMore && (
              <span className="ml-2 text-indigo-600 dark:text-indigo-400">
                (carregando mais automaticamente...)
              </span>
            )}
          </div>
          <div className="flex items-center space-x-4">
            <label className="flex items-center text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={agruparAtividades}
                onChange={(e) => {
                  setAgruparAtividades(e.target.checked)
                }}
                className="form-checkbox h-4 w-4 text-indigo-600"
                disabled={loading}
              />
              <span className="ml-2">Agrupar Atividades</span>
            </label>
            <div className="flex space-x-2">
              <button
                onClick={handleExportCSV}
                disabled={loading || filteredActivities.length === 0}
                className="inline-flex items-center px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                Exportar CSV
              </button>
              <button
                onClick={handlePrint}
                disabled={loading || filteredActivities.length === 0}
                className="inline-flex items-center px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                <PrinterIcon className="h-4 w-4 mr-2" />
                Imprimir
              </button>
              <button
                onClick={() => fetchData(1, true)}
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Atualizando...' : 'Atualizar'}
              </button>
            </div>
          </div>
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
                  {agruparAtividades && (
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Eventos Agrupados
                    </th>
                  )}
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
                        <div className="flex flex-col space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${activityType.color}`}>
                              {activityType.label}
                            </span>
                            <select
                              value={activity.produtividade || 'neutral'}
                              onChange={(e) => updateActivityClassification(activity.id, e.target.value)}
                              className="text-xs border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-1 focus:ring-indigo-500"
                            >
                              <option value="productive">Produtivo</option>
                              <option value="nonproductive">Não Produtivo</option>
                              <option value="neutral">Neutro</option>
                              <option value="unclassified">Não Classificado</option>
                            </select>
                          </div>
                          {activity.categoria && activity.categoria !== 'unclassified' && activity.categoria !== 'Não Classificado' && (
                            <div className="flex items-center">
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-indigo-100 text-indigo-800 dark:bg-indigo-800 dark:text-indigo-200">
                                🏷️ {activity.categoria}
                              </span>
                            </div>
                          )}
                        </div>
                      </td>
                      {agruparAtividades && (
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            {activity.eventos_agrupados || 1} eventos
                          </span>
                        </td>
                      )}
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
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

          {/* Loading indicator for infinite scroll */}
          {loadingMore && (
            <div className="flex justify-center py-6">
              <LoadingSpinner size="md" text="Carregando mais atividades..." />
            </div>
          )}

          {/* Intersection observer target */}
          {hasMore && !loadingMore && (
            <div ref={loadMoreRef} className="h-4 flex justify-center py-4">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Role para baixo para carregar mais...
              </div>
            </div>
          )}

          {!hasMore && activities.length > 0 && (
            <div className="text-center py-6">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                ✅ Todas as atividades foram carregadas ({activities.length} total)
              </p>
            </div>
          )}

          {filteredActivities.length === 0 && !loadingMore && (
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