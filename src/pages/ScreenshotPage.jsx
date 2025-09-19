import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  PhotoIcon, 
  ArrowLeftIcon, 
  ArrowRightIcon,
  FunnelIcon
} from '@heroicons/react/24/outline'
import api from '../services/api'
import { formatBrasiliaDate } from '../utils/timezoneUtils'

const ScreenshotPage = () => {
  const { activityId } = useParams()
  const navigate = useNavigate()
  
  const [screenshot, setScreenshot] = useState(null)
  const [activity, setActivity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [allActivities, setAllActivities] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showFilters, setShowFilters] = useState(false)
  const [filterUser, setFilterUser] = useState('all')
  const [filterDate, setFilterDate] = useState('')
  const [users, setUsers] = useState([])

  // Carregar dados iniciais
  useEffect(() => {
    loadInitialData()
  }, [])

  // Carregar screenshot quando activityId mudar
  useEffect(() => {
    if (activityId) {
      loadScreenshot(activityId)
    }
  }, [activityId])

  const loadInitialData = async () => {
    try {
      // Carregar usuários
      const usersResponse = await api.get('/usuarios-monitorados')
      if (usersResponse.data) {
        setUsers(usersResponse.data)
      }

      // Carregar atividades com screenshots
      const activitiesResponse = await api.get('/atividades?limite=1000&agrupar=false')
      if (activitiesResponse.data) {
        const activitiesWithScreenshots = activitiesResponse.data.filter(a => a.has_screenshot)
        setAllActivities(activitiesWithScreenshots)
        
        // Encontrar índice da atividade atual
        const index = activitiesWithScreenshots.findIndex(a => a.id === parseInt(activityId))
        if (index !== -1) {
          setCurrentIndex(index)
        }
      }
    } catch (error) {
      console.error('Erro ao carregar dados iniciais:', error)
    }
  }

  const loadScreenshot = async (id) => {
    if (!id) return

    setLoading(true)
    setError(null)
    setScreenshot(null)

    try {
      // Carregar dados da atividade
      const activityResponse = await api.get(`/atividade/${id}`)
      if (activityResponse.data) {
        setActivity(activityResponse.data)
      }

      // Carregar screenshot
      const response = await api.get(`/atividade/screenshot/${id}`, {
        responseType: 'blob'
      })

      if (response.data) {
        // Converter blob para base64
        const reader = new FileReader()
        reader.onload = () => {
          const base64 = reader.result.split(',')[1]
          setScreenshot(base64)
          setLoading(false)
        }
        reader.onerror = () => {
          setError('Erro ao processar imagem')
          setLoading(false)
        }
        reader.readAsDataURL(response.data)
      } else {
        setError('Screenshot não encontrado')
        setLoading(false)
      }
    } catch (error) {
      console.error('Erro ao carregar screenshot:', error)
      setError('Erro ao carregar screenshot')
      setLoading(false)
    }
  }

  const goToPrevious = () => {
    if (currentIndex > 0) {
      const prevActivity = allActivities[currentIndex - 1]
      navigate(`/screenshots/${prevActivity.id}`)
    }
  }

  const goToNext = () => {
    if (currentIndex < allActivities.length - 1) {
      const nextActivity = allActivities[currentIndex + 1]
      navigate(`/screenshots/${nextActivity.id}`)
    }
  }

  const goToActivity = (activity) => {
    navigate(`/screenshots/${activity.id}`)
  }

  const goBack = () => {
    navigate(-1)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      goBack()
    } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
      goToPrevious()
    } else if (e.key === 'ArrowRight' && currentIndex < allActivities.length - 1) {
      goToNext()
    }
  }

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [currentIndex, allActivities.length])

  // Filtrar atividades
  const filteredActivities = allActivities.filter(activity => {
    if (filterUser !== 'all' && activity.usuario_monitorado_id !== parseInt(filterUser)) {
      return false
    }
    if (filterDate && activity.horario) {
      const activityDate = new Date(activity.horario).toISOString().split('T')[0]
      return activityDate === filterDate
    }
    return true
  })

  const currentActivity = allActivities[currentIndex]
  const hasPrevious = currentIndex > 0
  const hasNext = currentIndex < allActivities.length - 1

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={goBack}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Voltar"
              >
                <ArrowLeftIcon className="w-6 h-6" />
              </button>
              
              <div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Visualizador de Screenshots
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {currentActivity ? `${currentIndex + 1} de ${allActivities.length} screenshots` : 'Carregando...'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {/* Filtros */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Filtros"
              >
                <FunnelIcon className="w-5 h-5" />
              </button>

              {/* Navegação */}
              <div className="flex items-center space-x-1">
                <button
                  onClick={goToPrevious}
                  disabled={!hasPrevious}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Anterior (←)"
                >
                  <ArrowLeftIcon className="w-5 h-5" />
                </button>
                <button
                  onClick={goToNext}
                  disabled={!hasNext}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Próximo (→)"
                >
                  <ArrowRightIcon className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* Filtros */}
          {showFilters && (
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Usuário
                  </label>
                  <select
                    value={filterUser}
                    onChange={(e) => setFilterUser(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="all">Todos os usuários</option>
                    {users.map(user => (
                      <option key={user.id} value={user.id}>
                        {user.nome}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Data
                  </label>
                  <input
                    type="date"
                    value={filterDate}
                    onChange={(e) => setFilterDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex h-screen">
        {/* Sidebar com lista de atividades */}
        <div className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Screenshots Disponíveis
            </h3>
            
            <div className="space-y-2">
              {filteredActivities.map((activity, index) => (
                <div
                  key={activity.id}
                  onClick={() => goToActivity(activity)}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    activity.id === parseInt(activityId)
                      ? 'bg-blue-100 dark:bg-blue-900 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <PhotoIcon className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {activity.active_window}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {activity.usuario_monitorado_nome} • {formatBrasiliaDate(activity.horario, 'datetime')}
                      </p>
                      {activity.domain && (
                        <p className="text-xs text-blue-600 dark:text-blue-400">
                          🌐 {activity.domain}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Área principal com screenshot */}
        <div className="flex-1 flex items-center justify-center bg-gray-100 dark:bg-gray-900">
          {loading && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Carregando screenshot...
              </p>
            </div>
          )}

          {error && (
            <div className="text-center">
              <PhotoIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                {error}
              </p>
              <button
                onClick={() => loadScreenshot(activityId)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Tentar novamente
              </button>
            </div>
          )}

          {screenshot && !loading && (
            <div className="max-w-full max-h-full p-4">
              <img
                src={`data:image/jpeg;base64,${screenshot}`}
                alt="Screenshot da atividade"
                className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ScreenshotPage
