import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format } from 'date-fns'
import { parseBrasiliaDate, formatBrasiliaDate } from '../utils/timezoneUtils'
import { EyeIcon, PhotoIcon } from '@heroicons/react/24/outline'
import { 
  MagnifyingGlassIcon, 
  FunnelIcon, 
  PrinterIcon, 
  ArrowDownTrayIcon,
  TagIcon,
  SparklesIcon,
  PlusIcon,
  ChartBarIcon,
  ComputerDesktopIcon
} from '@heroicons/react/24/outline'
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
  const [showTagSuggestions, setShowTagSuggestions] = useState(false)
  const [tagAnalysis, setTagAnalysis] = useState(null)
  const [suggestedTags, setSuggestedTags] = useState([])
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [existingTags, setExistingTags] = useState([])
  const navigate = useNavigate()
  
  // Hook de intersection observer com tratamento de erro
  let loadMoreRef, isLoadMoreVisible
  try {
    [loadMoreRef, isLoadMoreVisible] = useIntersectionObserver()
  } catch (error) {
    console.warn('Erro ao inicializar useIntersectionObserver, usando fallback:', error)
    // Fallback: criar ref manualmente
    loadMoreRef = { current: null }
    isLoadMoreVisible = false
  }

  // Função para buscar tags existentes
  const fetchExistingTags = useCallback(async () => {
    try {
      const response = await api.get('/tags')
      setExistingTags(response.data || [])
    } catch (error) {
      console.error('Erro ao buscar tags existentes:', error)
      setExistingTags([])
    }
  }, [])

  // Função para buscar atividades
  const fetchData = useCallback(async (page = 1, reset = false) => {
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
      if (error.response) {
        console.error('Response error:', error.response.status, error.response.data)
      }
      if (page === 1) {
        setActivities([])
        setUsers([])
      }
      // Mostrar mensagem de erro ao usuário
      setMessage('Erro ao carregar atividades. Tente novamente.')
      setTimeout(() => setMessage(''), 5000)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [agruparAtividades])

  // Carregar dados iniciais
  useEffect(() => {
    fetchData(1, true)
    fetchExistingTags()
  }, [fetchData, fetchExistingTags])

  // Aplicar filtros quando atividades ou filtros mudarem
  useEffect(() => {
    applyFilters()
  }, [applyFilters])

  const loadMoreActivities = useCallback(() => {
    if (hasMore && !loadingMore && !loading) {
      fetchData(currentPage + 1, false)
    }
  }, [hasMore, loadingMore, loading, currentPage, fetchData])

  // Detectar quando o usuário chega ao final da lista
  useEffect(() => {
    if (isLoadMoreVisible && hasMore && !loadingMore) {
      loadMoreActivities()
    }
  }, [isLoadMoreVisible, hasMore, loadingMore, loadMoreActivities])

  const applyFilters = useCallback(() => {
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
  }, [activities, searchTerm, dateFilter, typeFilter, userFilter])

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

  const analyzeActivityPatterns = async () => {
    setLoadingAnalysis(true)
    try {
      // Analisar padrões nas atividades carregadas
      const patterns = analyzePatterns(filteredActivities)
      setTagAnalysis(patterns)
      
      // Gerar sugestões de tags baseadas nos padrões
      const suggestions = generateTagSuggestions(patterns, existingTags)
      setSuggestedTags(suggestions)
      
      setShowTagSuggestions(true)
      setMessage('Análise de padrões concluída! Verifique as sugestões de tags.')
      setTimeout(() => setMessage(''), 5000)
    } catch (error) {
      console.error('Erro ao analisar padrões:', error)
      setMessage('Erro ao analisar padrões das atividades')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setLoadingAnalysis(false)
    }
  }

  const analyzePatterns = (activities) => {
    const patterns = {
      domains: {},
      applications: {},
      keywords: {},
      timePatterns: {},
      userBehavior: {}
    }

    activities.forEach(activity => {
      // Análise de domínios
      const domain = extractDomainFromWindow(activity.active_window)
      if (domain) {
        patterns.domains[domain] = (patterns.domains[domain] || 0) + 1
      }

      // Análise de aplicações
      const app = extractApplicationFromWindow(activity.active_window)
      if (app) {
        patterns.applications[app] = (patterns.applications[app] || 0) + 1
      }

      // Análise de palavras-chave
      const keywords = extractKeywordsFromWindow(activity.active_window)
      keywords.forEach(keyword => {
        patterns.keywords[keyword] = (patterns.keywords[keyword] || 0) + 1
      })

      // Análise temporal
      const hour = parseBrasiliaDate(activity.horario).getHours()
      const timeSlot = getTimeSlot(hour)
      patterns.timePatterns[timeSlot] = (patterns.timePatterns[timeSlot] || 0) + 1

      // Análise por usuário
      const userId = activity.usuario_monitorado_id
      if (!patterns.userBehavior[userId]) {
        patterns.userBehavior[userId] = {
          name: activity.usuario_monitorado_nome,
          productive: 0,
          nonproductive: 0,
          neutral: 0,
          total: 0
        }
      }
      
      patterns.userBehavior[userId].total++
      const produtividade = activity.produtividade || 'neutral'
      if (patterns.userBehavior[userId][produtividade] !== undefined) {
        patterns.userBehavior[userId][produtividade]++
      }
    })

    return patterns
  }

  const generateTagSuggestions = (patterns, existingTags) => {
    const suggestions = []
    const existingTagNames = existingTags.map(tag => tag.nome.toLowerCase())

    // Sugestões baseadas em domínios populares
    Object.entries(patterns.domains)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .forEach(([domain, count]) => {
        const tagName = domain.replace(/\./g, '-')
        if (!existingTagNames.includes(tagName.toLowerCase()) && count > 2) {
          suggestions.push({
            nome: tagName,
            tipo: 'domain',
            descricao: `Atividades relacionadas ao domínio ${domain}`,
            cor: '#3B82F6',
            produtividade: 'neutral',
            confidence: Math.min(count / 10, 1),
            pattern: domain,
            occurrences: count
          })
        }
      })

    // Sugestões baseadas em aplicações
    Object.entries(patterns.applications)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .forEach(([app, count]) => {
        const tagName = app.toLowerCase().replace(/\s+/g, '-')
        if (!existingTagNames.includes(tagName) && count > 2) {
          let produtividade = 'neutral'
          if (app.includes('Code') || app.includes('Development')) {
            produtividade = 'productive'
          } else if (app.includes('Social') || app.includes('Game')) {
            produtividade = 'nonproductive'
          }

          suggestions.push({
            nome: tagName,
            tipo: 'application',
            descricao: `Atividades na aplicação ${app}`,
            cor: produtividade === 'productive' ? '#10B981' : produtividade === 'nonproductive' ? '#EF4444' : '#F59E0B',
            produtividade,
            confidence: Math.min(count / 10, 1),
            pattern: app,
            occurrences: count
          })
        }
      })

    // Sugestões baseadas em palavras-chave
    Object.entries(patterns.keywords)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .forEach(([keyword, count]) => {
        if (!existingTagNames.includes(keyword.toLowerCase()) && count > 3 && keyword.length > 3) {
          suggestions.push({
            nome: keyword,
            tipo: 'keyword',
            descricao: `Atividades relacionadas a "${keyword}"`,
            cor: '#8B5CF6',
            produtividade: 'neutral',
            confidence: Math.min(count / 20, 1),
            pattern: keyword,
            occurrences: count
          })
        }
      })

    return suggestions.sort((a, b) => b.confidence - a.confidence)
  }

  const extractDomainFromWindow = (activeWindow) => {
    if (!activeWindow) return null
    
    const urlMatch = activeWindow.match(/https?:\/\/([^\/\s]+)/)
    if (urlMatch) {
      return urlMatch[1]
    }
    
    const domainPatterns = [
      /- ([a-zA-Z0-9-]+\.[a-zA-Z]{2,})/,
      /\(([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\)/,
      /([a-zA-Z0-9-]+\.[a-zA-Z]{2,})/
    ]
    
    for (const pattern of domainPatterns) {
      const match = activeWindow.match(pattern)
      if (match) {
        return match[1]
      }
    }
    
    return null
  }

  const extractApplicationFromWindow = (activeWindow) => {
    if (!activeWindow) return null
    
    const knownApps = {
      'chrome': 'Google Chrome',
      'firefox': 'Firefox',
      'edge': 'Microsoft Edge',
      'code': 'VS Code',
      'visual studio': 'Visual Studio',
      'notepad': 'Notepad',
      'explorer': 'Windows Explorer',
      'teams': 'Microsoft Teams',
      'outlook': 'Outlook',
      'word': 'Microsoft Word',
      'excel': 'Microsoft Excel',
      'powerpoint': 'PowerPoint',
      'slack': 'Slack',
      'discord': 'Discord',
      'whatsapp': 'WhatsApp',
      'telegram': 'Telegram'
    }
    
    const lowerWindow = activeWindow.toLowerCase()
    
    for (const [key, value] of Object.entries(knownApps)) {
      if (lowerWindow.includes(key)) {
        return value
      }
    }
    
    const appMatch = activeWindow.match(/^([^-–]+)/)
    if (appMatch) {
      const appName = appMatch[1].trim()
      if (appName.length > 0 && appName.length < 50) {
        return appName
      }
    }
    
    return null
  }

  const extractKeywordsFromWindow = (activeWindow) => {
    if (!activeWindow) return []
    
    const text = activeWindow.toLowerCase()
    const commonWords = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those', 'a', 'an', 'it', 'he', 'she', 'they', 'we', 'you', 'i', 'me', 'him', 'her', 'them', 'us']
    
    const words = text.match(/\b[a-zA-Z]{4,}\b/g) || []
    
    return words.filter(word => 
      !commonWords.includes(word) && 
      word.length >= 4 && 
      word.length <= 20 &&
      !/^\d+$/.test(word)
    )
  }

  const getTimeSlot = (hour) => {
    if (hour >= 6 && hour < 12) return 'manhã'
    if (hour >= 12 && hour < 18) return 'tarde'
    if (hour >= 18 && hour < 22) return 'noite'
    return 'madrugada'
  }

  const createTagFromSuggestion = async (suggestion) => {
    try {
      const tagData = {
        nome: suggestion.nome,
        descricao: suggestion.descricao,
        cor: suggestion.cor,
        produtividade: suggestion.produtividade
      }

      await api.post('/tags', tagData)
      
      // Atualizar lista de tags existentes
      await fetchExistingTags()
      
      // Remover da lista de sugestões
      setSuggestedTags(prev => prev.filter(s => s.nome !== suggestion.nome))
      
      setMessage(`Tag "${suggestion.nome}" criada com sucesso!`)
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Erro ao criar tag:', error)
      setMessage(`Erro ao criar tag "${suggestion.nome}"`)
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
      'Data/Hora Inicial': formatBrasiliaDate(activity.horario, 'datetime'),
      'Data/Hora Final': agruparAtividades && activity.ultimo_horario 
        ? formatBrasiliaDate(activity.ultimo_horario, 'datetime')
        : formatBrasiliaDate(activity.horario, 'datetime'),
      'Usuário Monitorado': activity.usuario_monitorado_nome || 'N/A',
      'Cargo': activity.cargo || 'N/A',
      'Janela Ativa': activity.active_window,
      'Categoria': activity.categoria || 'Não Classificado',
      'Ociosidade': formatTime(activity.ociosidade),
      'Classificação': getActivityType(activity).label,
      'Eventos Agrupados': agruparAtividades ? (activity.eventos_agrupados || 1) : 1,
      'Duração Total': formatTime(activity.duracao || activity.duracao_total || 0),
      'Domínio': activity.domain || 'N/A',
      'Aplicação': activity.application || 'N/A'
    }))

    exportToCSV(exportData, 'atividades_agrupadas')
  }

  const handleViewScreenshot = (activityId) => {
    navigate(`/screenshots/${activityId}`)
  }

  const handlePrint = () => {
    const columns = [
      {
        header: 'Data/Hora',
        accessor: (row) => formatBrasiliaDate(row.horario, 'datetime')
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
                onClick={analyzeActivityPatterns}
                disabled={loadingAnalysis || filteredActivities.length === 0}
                className="inline-flex items-center px-3 py-2 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                <SparklesIcon className="h-4 w-4 mr-2" />
                {loadingAnalysis ? 'Analisando...' : 'Analisar Padrões'}
              </button>
              <button
                onClick={() => setShowTagSuggestions(!showTagSuggestions)}
                disabled={suggestedTags.length === 0}
                className="inline-flex items-center px-3 py-2 bg-yellow-600 text-white text-sm font-medium rounded-md hover:bg-yellow-700 disabled:opacity-50"
              >
                <TagIcon className="h-4 w-4 mr-2" />
                Sugestões de Tags ({suggestedTags.length})
              </button>
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

      {/* Painel de Sugestões de Tags */}
      {showTagSuggestions && suggestedTags.length > 0 && (
        <div className="mb-6 bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Sugestões de Tags Baseadas em Padrões
              </h3>
              <button
                onClick={() => setShowTagSuggestions(false)}
                className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400"
              >
                ✕
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {suggestedTags.map((suggestion, index) => (
                <div 
                  key={index}
                  className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <div 
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: suggestion.cor }}
                      ></div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {suggestion.nome}
                      </h4>
                    </div>
                    <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-1 rounded">
                      {suggestion.tipo}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {suggestion.descricao}
                  </p>
                  
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-3">
                    <span>Padrão: {suggestion.pattern}</span>
                    <span>{suggestion.occurrences} ocorrências</span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      suggestion.produtividade === 'productive' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200'
                        : suggestion.produtividade === 'nonproductive'
                        ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-200'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-200'
                    }`}>
                      {suggestion.produtividade}
                    </span>
                    
                    <button
                      onClick={() => createTagFromSuggestion(suggestion)}
                      className="inline-flex items-center px-2 py-1 bg-indigo-600 text-white text-xs font-medium rounded hover:bg-indigo-700"
                    >
                      <PlusIcon className="h-3 w-3 mr-1" />
                      Criar Tag
                    </button>
                  </div>
                  
                  <div className="mt-2">
                    <div className="bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                      <div 
                        className="bg-indigo-600 h-2 rounded-full" 
                        style={{ width: `${suggestion.confidence * 100}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Confiança: {Math.round(suggestion.confidence * 100)}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Painel de Análise de Padrões */}
      {tagAnalysis && showTagSuggestions && (
        <div className="mb-6 bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Análise de Padrões das Atividades
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <ChartBarIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  <h4 className="font-medium text-blue-900 dark:text-blue-100">
                    Domínios Únicos
                  </h4>
                </div>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {Object.keys(tagAnalysis.domains).length}
                </p>
              </div>
              
              <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <ComputerDesktopIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
                  <h4 className="font-medium text-green-900 dark:text-green-100">
                    Aplicações
                  </h4>
                </div>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {Object.keys(tagAnalysis.applications).length}
                </p>
              </div>
              
              <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <TagIcon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                  <h4 className="font-medium text-purple-900 dark:text-purple-100">
                    Palavras-chave
                  </h4>
                </div>
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {Object.keys(tagAnalysis.keywords).length}
                </p>
              </div>
              
              <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <SparklesIcon className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                  <h4 className="font-medium text-yellow-900 dark:text-yellow-100">
                    Tags Sugeridas
                  </h4>
                </div>
                <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                  {suggestedTags.length}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

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
                        <div className="flex flex-col">
                          <span>{formatBrasiliaDate(activity.horario, 'datetime')}</span>
                          {agruparAtividades && activity.ultimo_horario && activity.ultimo_horario !== activity.horario && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              até {formatBrasiliaDate(activity.ultimo_horario, 'time')}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {activity.usuario_monitorado_nome || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {activity.cargo || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        <div className="max-w-xs">
                          <div className="truncate" title={activity.active_window}>
                            {activity.active_window}
                          </div>
                          {agruparAtividades && activity.eventos_agrupados > 1 && (
                            <div className="flex items-center mt-1 space-x-2">
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                📊 {activity.eventos_agrupados} ocorrências
                              </span>
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                                ⏱️ {formatTime(activity.duracao || activity.duracao_total)}
                              </span>
                            </div>
                          )}
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
                        <div className="flex items-center space-x-2">
                          {activity.has_screenshot && (
                            <button
                              onClick={() => handleViewScreenshot(activity.id)}
                              className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
                              title="Ver Screenshot"
                            >
                              <PhotoIcon className="w-4 h-4 mr-1" />
                              Screenshot
                            </button>
                          )}
                          <button 
                            onClick={() => deleteActivity(activity.id)}
                            className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                          >
                            Excluir
                          </button>
                        </div>
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