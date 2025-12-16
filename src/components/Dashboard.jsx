import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format, subDays, startOfDay, endOfDay, parseISO } from 'date-fns'
import { parseBrasiliaDate, formatBrasiliaDate } from '../utils/timezoneUtils'
import { PhotoIcon } from '@heroicons/react/24/outline'
import { 
  ChartBarIcon, 
  ArrowPathIcon, 
  GlobeAltIcon,
  ComputerDesktopIcon,
  ClockIcon,
  CalendarDaysIcon,
  UserIcon,
  SparklesIcon,
  FunnelIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'
import MetricCard from './charts/MetricCard'
import AdvancedChart from './charts/AdvancedChart'
import AdvancedFilters from './filters/AdvancedFilters'
import AIInsights from './ai/AIInsights'
import CompactStats from './dashboard/CompactStats'

const COLORS = {
  productive: '#10B981',
  nonproductive: '#EF4444',
  neutral: '#F59E0B',
  idle: '#6B7280'
}

const CHART_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', 
  '#06B6D4', '#F97316', '#84CC16', '#EC4899', '#6B7280'
]

// Cálculo consistente da duração (segundos)
const getActivityDurationSeconds = (activity) => {
  if (!activity) return 0
  const total = activity.duracao_total
  const single = activity.duracao
  if (typeof total === 'number' && !isNaN(total) && total > 0) return total
  if (typeof single === 'number' && !isNaN(single) && single > 0) return single
  const grouped = activity.eventos_agrupados
  if (typeof grouped === 'number' && grouped > 0) return grouped * 10
  return 0
}

// Parse seguro de data
const safeParseDate = (dateString) => {
  if (!dateString) return null
  try {
    // Tentar parse direto
    const date = new Date(dateString)
    if (!isNaN(date.getTime())) return date
    
    // Tentar parseBrasiliaDate
    const brasiliaDate = parseBrasiliaDate(dateString)
    if (brasiliaDate && !isNaN(brasiliaDate.getTime())) return brasiliaDate
    
    return null
  } catch (e) {
    return null
  }
}

// Extrair domínio
const extractDomainFromWindow = (activeWindow) => {
  if (!activeWindow) return 'Sistema Local'
  const urlMatch = activeWindow.match(/https?:\/\/([^\/\s]+)/)
  if (urlMatch) return urlMatch[1]
  const domainPatterns = [
    /- ([a-zA-Z0-9-]+\.[a-zA-Z]{2,})/,
    /\(([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\)/,
    /([a-zA-Z0-9-]+\.[a-zA-Z]{2,})/
  ]
  for (const pattern of domainPatterns) {
    const match = activeWindow.match(pattern)
    if (match) return match[1]
  }
  return 'Sistema Local'
}

// Extrair aplicação
const extractApplicationFromWindow = (activeWindow) => {
  if (!activeWindow) return 'Aplicação Desconhecida'
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
    if (lowerWindow.includes(key)) return value
  }
  const appMatch = activeWindow.match(/^([^-–]+)/)
  if (appMatch) {
    const appName = appMatch[1].trim()
    if (appName.length > 0 && appName.length < 50) return appName
  }
  return 'Aplicação Desconhecida'
}

export default function Dashboard() {
  const { user } = useAuth()
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dateRange, setDateRange] = useState(7)
  const [selectedUser, setSelectedUser] = useState('all')
  const [selectedDepartment, setSelectedDepartment] = useState('all')
  const [users, setUsers] = useState([])
  const [departments, setDepartments] = useState([])
  const [viewMode, setViewMode] = useState('overview')
  const [productivityFilter, setProductivityFilter] = useState(null) // 'productive', 'nonproductive', 'neutral', 'idle', null
  const navigate = useNavigate()

  // Carregar dados do dashboard
  const loadDashboardData = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      console.log('🔄 Carregando dados do dashboard...')
      
      const [activitiesRes, usersRes, departmentsRes] = await Promise.all([
        api.get('/atividades?agrupar=true&limite=1000'),
        api.get('/usuarios-monitorados'),
        api.get('/departamentos')
      ])

      const activities = Array.isArray(activitiesRes.data) ? activitiesRes.data : []
      const usersList = Array.isArray(usersRes.data) ? usersRes.data : []
      const departmentsList = Array.isArray(departmentsRes.data) ? departmentsRes.data : []

      console.log(`📦 Dados recebidos: ${activities.length} atividades, ${usersList.length} usuários, ${departmentsList.length} departamentos`)

      setUsers(usersList)
      setDepartments(departmentsList)

      // Processar atividades
      const now = new Date()
      const startDate = startOfDay(subDays(now, dateRange))
      const endDate = endOfDay(now)

      // Filtrar atividades por data
      let filteredActivities = activities.filter(activity => {
        if (!activity?.horario) return false
        
        const activityDate = safeParseDate(activity.horario)
        if (!activityDate) return false
        
        // Comparar apenas datas (sem hora)
        const activityDateOnly = new Date(activityDate.getFullYear(), activityDate.getMonth(), activityDate.getDate())
        const startDateOnly = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate())
        const endDateOnly = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate())
        
        return activityDateOnly >= startDateOnly && activityDateOnly <= endDateOnly
      })

      // Filtrar por usuário
      if (selectedUser !== 'all') {
        const userId = parseInt(selectedUser)
        if (!isNaN(userId)) {
          filteredActivities = filteredActivities.filter(activity =>
            activity.usuario_monitorado_id === userId
          )
        }
      }

      // Filtrar por departamento
      if (selectedDepartment !== 'all') {
        const deptId = parseInt(selectedDepartment)
        if (!isNaN(deptId)) {
          const usersInDept = usersList.filter(u => u.departamento_id === deptId)
          const userIds = usersInDept.map(u => u.id)
          filteredActivities = filteredActivities.filter(activity =>
            userIds.includes(activity.usuario_monitorado_id)
          )
        }
      }

      // Filtrar por produtividade (se selecionado)
      if (productivityFilter) {
        filteredActivities = filteredActivities.filter(activity => {
          const produtividade = activity.produtividade || 'neutral'
          const ociosidade = activity.ociosidade || 0
          
          if (productivityFilter === 'idle') {
            return ociosidade >= 600
          }
          return produtividade === productivityFilter
        })
      }

      console.log(`✅ ${filteredActivities.length} atividades após filtros`)

      // Calcular summary
      const summary = {
        productive: 0,
        nonproductive: 0,
        neutral: 0,
        idle: 0,
        total: 0,
        facePresence: 0
      }

      filteredActivities.forEach(activity => {
        const duration = getActivityDurationSeconds(activity)
        if (duration <= 0) return
        
        summary.total += duration
        const produtividade = activity.produtividade || 'neutral'
        const ociosidade = activity.ociosidade || 0
        
        if (summary[produtividade] !== undefined) {
          summary[produtividade] += duration
        } else {
          if (ociosidade >= 600) {
            summary.idle += duration
          } else {
            summary.neutral += duration
          }
        }
        
        // Adicionar tempo de presença facial ao summary
        if (activity.face_presence_time) {
          summary.facePresence += activity.face_presence_time
        }
      })

      // Processar dados por domínio
      const domainMap = {}
      filteredActivities.forEach(activity => {
        const duration = getActivityDurationSeconds(activity)
        if (duration <= 0) return
        
        const domain = activity.domain || extractDomainFromWindow(activity.active_window)
        if (!domainMap[domain]) {
          domainMap[domain] = { name: domain, value: 0, activities: 0 }
        }
        domainMap[domain].value += duration
        domainMap[domain].activities += (activity.eventos_agrupados || 1)
      })

      const domainData = Object.values(domainMap)
        .sort((a, b) => b.value - a.value)
        .slice(0, 10)

      // Processar dados por aplicação
      const applicationMap = {}
      filteredActivities.forEach(activity => {
        const duration = getActivityDurationSeconds(activity)
        if (duration <= 0) return
        
        const application = activity.application || extractApplicationFromWindow(activity.active_window)
        if (!applicationMap[application]) {
          applicationMap[application] = { name: application, value: 0, activities: 0 }
        }
        applicationMap[application].value += duration
        applicationMap[application].activities += (activity.eventos_agrupados || 1)
      })

      const applicationData = Object.values(applicationMap)
        .sort((a, b) => b.value - a.value)
        .slice(0, 10)

      // Processar dados por hora
      const hourlyMap = {}
      for (let i = 0; i < 24; i++) {
        hourlyMap[i] = {
          hour: i,
          productive: 0,
          nonproductive: 0,
          neutral: 0,
          idle: 0,
          total: 0
        }
      }

      filteredActivities.forEach(activity => {
        const activityDate = safeParseDate(activity.horario)
        if (!activityDate) return
        
        const hour = activityDate.getHours()
        const duration = getActivityDurationSeconds(activity)
        if (duration <= 0) return
        
        const produtividade = activity.produtividade || 'neutral'
        const ociosidade = activity.ociosidade || 0

        hourlyMap[hour].total += duration
        if (hourlyMap[hour][produtividade] !== undefined) {
          hourlyMap[hour][produtividade] += duration
        } else {
          if (ociosidade >= 600) {
            hourlyMap[hour].idle += duration
          } else {
            hourlyMap[hour].neutral += duration
          }
        }
      })

      const hourlyData = Object.values(hourlyMap)

      // Processar dados diários
      const dailyData = {}
      filteredActivities.forEach(activity => {
        const activityDate = safeParseDate(activity.horario)
        if (!activityDate) return
        
        const day = format(activityDate, 'yyyy-MM-dd')
        if (!dailyData[day]) {
          dailyData[day] = {
            date: day,
            productive: 0,
            nonproductive: 0,
            neutral: 0,
            idle: 0
          }
        }

        const duration = getActivityDurationSeconds(activity)
        if (duration <= 0) return
        
        const produtividade = activity.produtividade || 'neutral'
        const ociosidade = activity.ociosidade || 0

        if (dailyData[day][produtividade] !== undefined) {
          dailyData[day][produtividade] += duration
        } else {
          if (ociosidade >= 600) {
            dailyData[day].idle += duration
          } else {
            dailyData[day].neutral += duration
          }
        }
      })

      const timelineData = Object.values(dailyData).sort((a, b) => a.date.localeCompare(b.date))

      // Processar estatísticas por usuário
      const userStatsMap = {}
      const presenceStatsMap = {} // Estatísticas de presença facial
      
      filteredActivities.forEach(activity => {
        if (!activity?.usuario_monitorado_id) return
        
        const userId = activity.usuario_monitorado_id
        const userName = activity.usuario_monitorado_nome ||
                        usersList.find(u => u.id === userId)?.nome ||
                        `Usuário ${userId}`

        if (!userStatsMap[userId]) {
          userStatsMap[userId] = {
            nome: userName,
            productive: 0,
            nonproductive: 0,
            neutral: 0,
            idle: 0,
            total: 0
          }
        }

        const duration = getActivityDurationSeconds(activity)
        if (duration <= 0) return
        
        const produtividade = activity.produtividade || 'neutral'
        const ociosidade = activity.ociosidade || 0

        userStatsMap[userId].total += duration
        if (userStatsMap[userId][produtividade] !== undefined) {
          userStatsMap[userId][produtividade] += duration
        } else {
          if (ociosidade >= 600) {
            userStatsMap[userId].idle += duration
          } else {
            userStatsMap[userId].neutral += duration
          }
        }
        
        // Processar dados de presença facial
        if (activity.face_presence_time !== null && activity.face_presence_time !== undefined) {
          if (!presenceStatsMap[userId]) {
            presenceStatsMap[userId] = {
              nome: userName,
              totalPresenceTime: 0,
              activitiesWithPresence: 0,
              maxPresenceTime: 0
            }
          }
          const presenceTime = parseInt(activity.face_presence_time) || 0
          presenceStatsMap[userId].totalPresenceTime = Math.max(
            presenceStatsMap[userId].totalPresenceTime,
            presenceTime
          )
          presenceStatsMap[userId].maxPresenceTime = Math.max(
            presenceStatsMap[userId].maxPresenceTime,
            presenceTime
          )
          presenceStatsMap[userId].activitiesWithPresence += 1
        }
      })

      const userStats = Object.values(userStatsMap)
      const presenceStats = Object.values(presenceStatsMap)
      
      // Calcular tempo total de presença no summary
      const totalPresenceTime = presenceStats.reduce((sum, stat) => sum + stat.maxPresenceTime, 0)

      // Atividades recentes
      const recentActivities = filteredActivities
        .sort((a, b) => {
          const dateA = safeParseDate(a.horario)
          const dateB = safeParseDate(b.horario)
          if (!dateA || !dateB) return 0
          return dateB - dateA
        })
        .slice(0, 10)
        .map(activity => ({
          ...activity,
          domain: activity.domain || extractDomainFromWindow(activity.active_window),
          application: activity.application || extractApplicationFromWindow(activity.active_window)
        }))

      // Dados do gráfico de pizza
      const pieData = [
        { name: 'Produtivo', value: summary.productive, color: COLORS.productive },
        { name: 'Não Produtivo', value: summary.nonproductive, color: COLORS.nonproductive },
        { name: 'Neutro', value: summary.neutral, color: COLORS.neutral },
        { name: 'Ocioso', value: summary.idle, color: COLORS.idle }
      ].filter(item => item.value > 0)

      const processedData = {
        pieData,
        timelineData,
        userStats,
        summary,
        recentActivities,
        domainData,
        applicationData,
        hourlyData,
        presenceStats,
        totalPresenceTime,
        rawActivities: activities
      }

      console.log('✅ Dashboard processado:', {
        summary,
        timelineDays: timelineData.length,
        recentActivities: recentActivities.length
      })

      setDashboardData(processedData)
    } catch (err) {
      console.error('❌ Erro ao carregar dashboard:', err)
      setError(err.message || 'Erro ao carregar dados do dashboard')
      setDashboardData({
        pieData: [],
        timelineData: [],
        userStats: [],
        summary: { productive: 0, nonproductive: 0, neutral: 0, idle: 0, total: 0 },
        recentActivities: [],
        domainData: [],
        applicationData: [],
        hourlyData: []
      })
    } finally {
      setLoading(false)
    }
  }, [dateRange, selectedUser, selectedDepartment, productivityFilter])

  // Carregar dados quando o componente monta ou quando filtros mudam
  useEffect(() => {
    loadDashboardData()
  }, [loadDashboardData])

  const formatTime = (seconds) => {
    if (!seconds || seconds === 0) return '0min'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours === 0) return `${minutes}min`
    if (minutes === 0) return `${hours}h`
    return `${hours}h ${minutes}min`
  }

  const formatPercentage = (value, total) => {
    if (!total || total === 0) return '0%'
    const percentage = ((value / total) * 100)
    if (isNaN(percentage) || !isFinite(percentage)) return '0%'
    return `${percentage.toFixed(1)}%`
  }

  const formatDuration = (seconds) => {
    if (!seconds || seconds === 0) return '0s'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    if (hours > 0) return `${hours}h ${minutes}min`
    if (minutes > 0) return `${minutes}min ${secs}s`
    return `${secs}s`
  }

  const formatHour = (hour) => {
    return `${hour.toString().padStart(2, '0')}:00`
  }

  const handleViewScreenshot = (activityId) => {
    navigate(`/screenshots/${activityId}`)
  }

  if (loading) {
    return <LoadingSpinner size="xl" text="Carregando dashboard..." fullScreen />
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 className="text-lg font-medium text-red-800 dark:text-red-200 mb-2">Erro ao carregar dashboard</h3>
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <button
            onClick={loadDashboardData}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  if (!dashboardData) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <ChartBarIcon className="mx-auto h-16 w-16 mb-4 text-gray-400" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Nenhum dado disponível</h3>
          <button
            onClick={loadDashboardData}
            className="px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            Carregar Dashboard
          </button>
        </div>
      </div>
    )
  }

  const { pieData, timelineData, userStats, summary, recentActivities, domainData, applicationData, hourlyData, presenceStats = [], totalPresenceTime = 0 } = dashboardData || {}
  
  // Garantir que filteredActivities existe para o componente
  const filteredActivities = dashboardData?.rawActivities || []

  const handleResetFilters = () => {
    setDateRange(7)
    setSelectedUser('all')
    setSelectedDepartment('all')
    setProductivityFilter(null)
  }

  const handleProductivityFilter = (filter) => {
    if (productivityFilter === filter) {
      setProductivityFilter(null) // Deselecionar se já estiver selecionado
    } else {
      setProductivityFilter(filter)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header Moderno */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Dashboard de Produtividade
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Bem-vindo, <span className="font-semibold">{user?.usuario}</span>! Análise completa de atividades e performance.
          </p>
        </div>
        <button
          onClick={loadDashboardData}
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center space-x-2 shadow-md hover:shadow-lg transition-all"
        >
          <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Atualizar</span>
        </button>
      </div>

      {/* Filtros Avançados */}
      <AdvancedFilters
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        selectedUser={selectedUser}
        onUserChange={setSelectedUser}
        selectedDepartment={selectedDepartment}
        onDepartmentChange={setSelectedDepartment}
        users={users}
        departments={departments}
        onReset={handleResetFilters}
      />

      {/* Tabs de Visualização */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', name: 'Visão Geral', icon: ChartBarIcon },
            { id: 'domains', name: 'Domínios', icon: GlobeAltIcon },
            { id: 'applications', name: 'Aplicações', icon: ComputerDesktopIcon },
            { id: 'timeline', name: 'Timeline', icon: CalendarDaysIcon }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setViewMode(tab.id)}
              className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors ${
                viewMode === tab.id
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
              }`}
            >
              <tab.icon className="h-5 w-5" />
              <span>{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Conteúdo baseado na tab selecionada */}
      {viewMode === 'overview' ? (
        <>
          {/* Cards de Métricas Principais - Clicáveis para Filtrar */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <button
              onClick={() => handleProductivityFilter('productive')}
              className={`transition-all transform hover:scale-105 ${productivityFilter === 'productive' ? 'ring-2 ring-green-500 ring-offset-2' : ''}`}
            >
              <MetricCard
                title="Tempo Produtivo"
                value={formatTime(summary.productive)}
                subtitle={formatPercentage(summary.productive, summary.total)}
                icon={ChartBarIcon}
                color="green"
                trend={summary.productive > summary.total * 0.5 ? 'up' : 'down'}
                trendValue={formatPercentage(summary.productive, summary.total)}
              />
            </button>
            <button
              onClick={() => handleProductivityFilter('nonproductive')}
              className={`transition-all transform hover:scale-105 ${productivityFilter === 'nonproductive' ? 'ring-2 ring-red-500 ring-offset-2' : ''}`}
            >
              <MetricCard
                title="Tempo Não Produtivo"
                value={formatTime(summary.nonproductive)}
                subtitle={formatPercentage(summary.nonproductive, summary.total)}
                icon={ChartBarIcon}
                color="red"
                trend={summary.nonproductive < summary.total * 0.3 ? 'up' : 'down'}
                trendValue={formatPercentage(summary.nonproductive, summary.total)}
              />
            </button>
            <button
              onClick={() => handleProductivityFilter('neutral')}
              className={`transition-all transform hover:scale-105 ${productivityFilter === 'neutral' ? 'ring-2 ring-yellow-500 ring-offset-2' : ''}`}
            >
              <MetricCard
                title="Tempo Neutro"
                value={formatTime(summary.neutral)}
                subtitle={formatPercentage(summary.neutral, summary.total)}
                icon={ClockIcon}
                color="yellow"
              />
            </button>
            <button
              onClick={() => handleProductivityFilter('idle')}
              className={`transition-all transform hover:scale-105 ${productivityFilter === 'idle' ? 'ring-2 ring-gray-500 ring-offset-2' : ''}`}
            >
              <MetricCard
                title="Tempo Ocioso"
                value={formatTime(summary.idle)}
                subtitle={formatPercentage(summary.idle, summary.total)}
                icon={ClockIcon}
                color="indigo"
              />
            </button>
          </div>

          {/* Indicador de Filtro Ativo */}
          {productivityFilter && (
            <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-3 flex items-center justify-between mb-6">
              <div className="flex items-center space-x-2">
                <FunnelIcon className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                <span className="text-sm font-medium text-indigo-900 dark:text-indigo-200">
                  Filtro ativo: <span className="capitalize">{productivityFilter === 'idle' ? 'Ocioso' : productivityFilter === 'productive' ? 'Produtivo' : productivityFilter === 'nonproductive' ? 'Não Produtivo' : 'Neutro'}</span>
                </span>
              </div>
              <button
                onClick={() => setProductivityFilter(null)}
                className="text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
              >
                Remover filtro
              </button>
            </div>
          )}

          {/* Layout Compacto - Grid de Visualizações */}
          <div className="grid grid-cols-12 gap-4">
            {/* Coluna 1: Insights de IA (3 colunas) */}
            <div className="col-span-12 lg:col-span-3">
              <AIInsights 
                data={dashboardData} 
                onAnalyze={loadDashboardData}
              />
            </div>

            {/* Coluna 2: Gráfico de Pizza (4 colunas) */}
            <div className="col-span-12 lg:col-span-4">
              <AdvancedChart
                type="pie"
                data={pieData}
                dataKey="value"
                height={280}
                title="Distribuição de Produtividade"
                subtitle="Tempo por categoria"
                colors={pieData.map(d => d.color)}
              />
            </div>

            {/* Coluna 3: Timeline Diária (5 colunas) */}
            <div className="col-span-12 lg:col-span-5">
              <AdvancedChart
                type="area"
                data={timelineData}
                xKey="date"
                yKeys={['productive', 'nonproductive', 'neutral']}
                height={280}
                title="Evolução Diária"
                subtitle="Tendência ao longo do tempo"
                stacked={true}
                colors={[COLORS.productive, COLORS.nonproductive, COLORS.neutral]}
              />
            </div>

            {/* Coluna 4: Distribuição por Hora (6 colunas) */}
            <div className="col-span-12 lg:col-span-6">
              <AdvancedChart
                type="bar"
                data={hourlyData}
                xKey="hour"
                yKeys={['productive', 'nonproductive', 'neutral']}
                height={250}
                title="Distribuição por Hora"
                subtitle="Horários mais produtivos"
                stacked={true}
                colors={[COLORS.productive, COLORS.nonproductive, COLORS.neutral]}
                formatTooltip={(value) => formatTime(value)}
                formatXAxis={(hour) => formatHour(hour)}
              />
            </div>

            {/* Coluna 5: Estatísticas Compactas (6 colunas) */}
            <div className="col-span-12 lg:col-span-6">
              <CompactStats
                domainData={domainData}
                applicationData={applicationData}
                userStats={userStats}
                formatTime={formatTime}
              />
            </div>
          </div>
        </>
      ) : null}

      {/* DOMÍNIOS - Página Dedicada */}
      {viewMode === 'domains' && (
        <div className="space-y-6">
          {/* Resumo de Domínios */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <MetricCard
              title="Total de Domínios"
              value={domainData.length}
              subtitle="Domínios únicos"
              icon={GlobeAltIcon}
              color="blue"
            />
            <MetricCard
              title="Tempo Total"
              value={formatTime(domainData.reduce((sum, d) => sum + d.value, 0))}
              subtitle="Em todos os domínios"
              icon={ClockIcon}
              color="indigo"
            />
            <MetricCard
              title="Top Domínio"
              value={domainData[0]?.name?.substring(0, 20) || 'N/A'}
              subtitle={domainData[0] ? formatTime(domainData[0].value) : '0min'}
              icon={GlobeAltIcon}
              color="green"
            />
          </div>

          {/* Lista de Domínios */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Top Domínios por Tempo de Uso</h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">{domainData.length} domínios encontrados</div>
            </div>
            {domainData.length > 0 ? (
              <div className="space-y-3">
                {domainData.map((domain, index) => {
                  const totalDomainTime = domainData.reduce((sum, d) => sum + d.value, 0)
                  const percentage = (domain.value / totalDomainTime) * 100
                  return (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                      <div className="flex items-center space-x-4 flex-1 min-w-0">
                        <div className="flex-shrink-0">
                          <div className="w-4 h-4 rounded-full" style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}></div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <GlobeAltIcon className="w-4 h-4 text-gray-400" />
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{domain.name}</p>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{domain.activities} atividade{domain.activities !== 1 ? 's' : ''}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">{formatTime(domain.value)}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{percentage.toFixed(1)}%</p>
                        </div>
                        <div className="w-20 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div className="h-2 rounded-full" style={{ width: `${Math.min(percentage, 100)}%`, backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}></div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <GlobeAltIcon className="mx-auto h-12 w-12 mb-2" />
                  <p className="text-sm">Nenhum domínio encontrado</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {viewMode === 'applications' && (
        <div className="space-y-6 mb-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Aplicações Mais Utilizadas</h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">{applicationData.length} aplicações encontradas</div>
            </div>
            {applicationData.length > 0 ? (
              <div className="space-y-3">
                {applicationData.map((app, index) => {
                  const totalAppTime = applicationData.reduce((sum, a) => sum + a.value, 0)
                  const percentage = (app.value / totalAppTime) * 100
                  return (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                      <div className="flex items-center space-x-4 flex-1 min-w-0">
                        <div className="flex-shrink-0 text-2xl">⚡</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{app.name}</p>
                            <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">#{index + 1}</span>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{app.activities} sessão{app.activities !== 1 ? 'ões' : ''} de uso</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">{formatTime(app.value)}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{percentage.toFixed(1)}% do tempo</p>
                        </div>
                        <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div className="h-2 rounded-full bg-gradient-to-r from-green-400 to-blue-500" style={{ width: `${Math.min(percentage, 100)}%` }}></div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <ComputerDesktopIcon className="mx-auto h-12 w-12 mb-2" />
                  <p className="text-sm">Nenhuma aplicação encontrada</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {viewMode === 'timeline' && (
        <div className="space-y-6">
          {/* Resumo da Timeline */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="Dias Monitorados"
              value={timelineData.length}
              subtitle="Período analisado"
              icon={CalendarDaysIcon}
              color="blue"
            />
            <MetricCard
              title="Tempo Total"
              value={formatTime(summary.total)}
              subtitle="Período completo"
              icon={ClockIcon}
              color="indigo"
            />
            <MetricCard
              title="Média Diária"
              value={formatTime(timelineData.length > 0 ? summary.total / timelineData.length : 0)}
              subtitle="Por dia"
              icon={ChartBarIcon}
              color="green"
            />
            <MetricCard
              title="Atividades"
              value={filteredActivities.length}
              subtitle="Total registrado"
              icon={ChartBarIcon}
              color="purple"
            />
          </div>

          {/* Timeline Visual */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Atividade Diária por Produtividade</h2>
            </div>
            {timelineData.length > 0 ? (
              <AdvancedChart
                type="bar"
                data={timelineData}
                xKey="date"
                yKeys={['productive', 'nonproductive', 'neutral', 'idle']}
                height={400}
                stacked={true}
                colors={[COLORS.productive, COLORS.nonproductive, COLORS.neutral, COLORS.idle]}
                formatTooltip={(value) => formatTime(value)}
                formatXAxis={(value) => format(parseISO(value), 'dd/MM')}
                formatYAxis={(value) => formatTime(value)}
              />
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <CalendarDaysIcon className="mx-auto h-16 w-16 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Nenhum dado de timeline</h3>
                  <p className="text-sm">Selecione um período diferente ou verifique os filtros</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Atividades Recentes */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Atividades Recentes</h2>
          <div className="text-sm text-gray-500 dark:text-gray-400">Últimas {recentActivities.length} atividades</div>
        </div>
        <div className="space-y-3">
          {recentActivities.length > 0 ? (
            recentActivities.map((activity, index) => (
              <div key={index} className="group flex items-start space-x-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200">
                <div className="flex-shrink-0 mt-1">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium text-white ${
                    activity.produtividade === 'productive' ? 'bg-green-500' :
                    activity.produtividade === 'nonproductive' ? 'bg-red-500' :
                    'bg-yellow-500'
                  }`}>
                    {activity.usuario_monitorado_nome?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 mb-1">
                        {activity.active_window}
                      </p>
                      <div className="flex items-center space-x-3 text-xs text-gray-500 dark:text-gray-400 mb-2">
                        <span className="font-medium">{activity.usuario_monitorado_nome}</span>
                        <span>•</span>
                        <span>{formatBrasiliaDate(activity.horario, 'datetime')}</span>
                        {activity.duracao && (
                          <>
                            <span>•</span>
                            <span>{formatDuration(activity.duracao)}</span>
                          </>
                        )}
                      </div>
                      <div className="flex items-center space-x-2 flex-wrap gap-1">
                        {activity.domain && (
                          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                            <GlobeAltIcon className="w-3 h-3 mr-1" />
                            {activity.domain}
                          </span>
                        )}
                        {activity.application && (
                          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                            <ComputerDesktopIcon className="w-3 h-3 mr-1" />
                            {activity.application}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      {activity.has_screenshot && (
                        <button
                          onClick={() => handleViewScreenshot(activity.id)}
                          className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
                          title="Ver Screenshot"
                        >
                          <PhotoIcon className="w-4 h-4 mr-1" />
                          <span className="hidden sm:inline">Screenshot</span>
                        </button>
                      )}
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                        activity.produtividade === 'productive'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                          : activity.produtividade === 'nonproductive'
                          ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                          : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                      }`}>
                        {activity.categoria || 
                         (activity.produtividade === 'productive' ? 'Produtivo' :
                          activity.produtividade === 'nonproductive' ? 'Não Produtivo' : 'Neutro')}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400 dark:text-gray-500">
                <ChartBarIcon className="mx-auto h-16 w-16 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Nenhuma atividade encontrada</h3>
                <p className="text-sm">Ajuste os filtros ou período para ver as atividades</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
