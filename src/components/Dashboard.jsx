import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format, subDays, startOfDay, endOfDay } from 'date-fns'
import { parseBrasiliaDate, formatBrasiliaDate } from '../utils/timezoneUtils'
import { PhotoIcon } from '@heroicons/react/24/outline'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  Area,
  AreaChart
} from 'recharts'
import { 
  ChartBarIcon, 
  ArrowPathIcon, 
  GlobeAltIcon,
  ComputerDesktopIcon,
  ClockIcon,
  CalendarDaysIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

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
  const total = activity?.duracao_total
  const single = activity?.duracao
  if (typeof total === 'number' && !isNaN(total)) return total
  if (typeof single === 'number' && !isNaN(single)) return single
  const grouped = activity?.eventos_agrupados
  if (typeof grouped === 'number' && grouped > 0) return grouped * 10
  return 0
}

// Função auxiliar para extrair domínio
const extractDomainFromWindow = (activeWindow) => {
  if (!activeWindow) return null

  // Tentar encontrar URLs no título da janela
  const urlMatch = activeWindow.match(/https?:\/\/([^\/\s]+)/)
  if (urlMatch) {
    return urlMatch[1]
  }

  // Procurar por padrões conhecidos de domínio
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

// Função auxiliar para extrair aplicação
const extractApplicationFromWindow = (activeWindow) => {
  if (!activeWindow) return null

  // Aplicações conhecidas
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

  // Tentar extrair o nome da aplicação do início do título
  const appMatch = activeWindow.match(/^([^-–]+)/)
  if (appMatch) {
    const appName = appMatch[1].trim()
    if (appName.length > 0 && appName.length < 50) {
      return appName
    }
  }

  return null
}

export default function Dashboard() {
  const { user } = useAuth()
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [dateRange, setDateRange] = useState(7)
  const [selectedUser, setSelectedUser] = useState('all')
  const [selectedDepartment, setSelectedDepartment] = useState('all')
  const [users, setUsers] = useState([])
  const [departments, setDepartments] = useState([])
  const [viewMode, setViewMode] = useState('overview') // overview, domains, applications, timeline
  const navigate = useNavigate()

  const handleViewScreenshot = (activityId) => {
    navigate(`/screenshots/${activityId}`)
  }

  const processActivities = useCallback((activities, usersList, departmentsList) => {
    const now = new Date()
    const startDate = startOfDay(subDays(now, dateRange))
    const endDate = endOfDay(now)

    console.log(`📊 Processando ${activities.length} atividades no período de ${startDate.toISOString()} a ${endDate.toISOString()}`)

    let filteredActivities = activities.filter(activity => {
      if (!activity?.horario) return false
      const activityDate = parseBrasiliaDate(activity.horario)
      return activityDate >= startDate && activityDate <= endDate
    })

    console.log(`🔍 ${filteredActivities.length} atividades após filtro de data`)

    if (selectedUser !== 'all') {
      const userId = parseInt(selectedUser)
      if (!isNaN(userId)) {
        filteredActivities = filteredActivities.filter(activity =>
          activity.usuario_monitorado_id === userId
        )
        console.log(`👤 ${filteredActivities.length} atividades após filtro de usuário`)
      }
    }

    if (selectedDepartment !== 'all') {
      const deptId = parseInt(selectedDepartment)
      if (!isNaN(deptId)) {
        const usersInDept = usersList.filter(u => u.departamento_id === deptId)
        const userIds = usersInDept.map(u => u.id)
        filteredActivities = filteredActivities.filter(activity =>
          userIds.includes(activity.usuario_monitorado_id)
        )
        console.log(`🏢 ${filteredActivities.length} atividades após filtro de departamento`)
      }
    }

    // Processar summary
    const summary = {
      productive: 0,
      nonproductive: 0,
      neutral: 0,
      idle: 0,
      total: 0
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
    })

    console.log('📈 Summary calculado:', summary)

    // Processar dados por domínio
    const domainMap = {}
    filteredActivities.forEach(activity => {
      const duration = getActivityDurationSeconds(activity)
      if (duration <= 0) return
      
      let domain = activity.domain
      if (!domain) {
        domain = extractDomainFromWindow(activity.active_window) || 'Sistema Local'
      }

      if (!domainMap[domain]) {
        domainMap[domain] = { name: domain, value: 0, activities: 0 }
      }
      domainMap[domain].value += duration
      domainMap[domain].activities += (activity.eventos_agrupados || 1)
    })

    const domainData = Object.values(domainMap)
      .sort((a, b) => b.value - a.value)
      .slice(0, 10)

    console.log('🌐 Dados de domínio processados:', domainData)

    // Processar dados por aplicação
    const applicationMap = {}
    filteredActivities.forEach(activity => {
      const duration = getActivityDurationSeconds(activity)
      if (duration <= 0) return
      
      let application = activity.application
      if (!application) {
        application = extractApplicationFromWindow(activity.active_window) || 'Aplicação Desconhecida'
      }

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
      if (!activity?.horario) return
      const activityDate = parseBrasiliaDate(activity.horario)
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

    // Dados existentes (pie, timeline, etc.)
    const pieData = [
      { name: 'Produtivo', value: summary.productive, color: COLORS.productive },
      { name: 'Não Produtivo', value: summary.nonproductive, color: COLORS.nonproductive },
      { name: 'Neutro', value: summary.neutral, color: COLORS.neutral },
      { name: 'Ocioso', value: summary.idle, color: COLORS.idle }
    ].filter(item => item.value > 0)

    const dailyData = {}
    filteredActivities.forEach(activity => {
      if (!activity?.horario) return
      const activityDate = parseBrasiliaDate(activity.horario)
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

    const userStatsMap = {}
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
    })

    const userStats = Object.values(userStatsMap)

    const recentActivities = filteredActivities
      .sort((a, b) => parseBrasiliaDate(b.horario) - parseBrasiliaDate(a.horario))
      .slice(0, 10)
      .map(activity => ({
        ...activity,
        domain: activity.domain || extractDomainFromWindow(activity.active_window),
        application: activity.application || extractApplicationFromWindow(activity.active_window)
      }))

    console.log('📰 Atividades recentes processadas:', recentActivities.length)

    return {
      pieData,
      timelineData,
      userStats,
      summary,
      recentActivities,
      domainData,
      applicationData,
      hourlyData
    }
  }, [dateRange, selectedUser, selectedDepartment])

  const loadDashboardData = useCallback(async () => {
    if (loading) return

    setLoading(true)
    try {
      console.log('🔄 Carregando dados do dashboard...')

      const [activitiesRes, usersRes, departmentsRes] = await Promise.all([
        api.get('/atividades?agrupar=true&limite=500'),
        api.get('/usuarios-monitorados'),
        api.get('/departamentos')
      ])

      const activities = Array.isArray(activitiesRes.data) ? activitiesRes.data : []
      const usersList = Array.isArray(usersRes.data) ? usersRes.data : []
      const departmentsList = Array.isArray(departmentsRes.data) ? departmentsRes.data : []

      setUsers(usersList)
      setDepartments(departmentsList)

      const processedData = processActivities(activities, usersList, departmentsList)
      processedData.rawActivities = activities // Store raw data for reprocessing
      setDashboardData(processedData)

      console.log('✅ Dashboard carregado com sucesso')
    } catch (error) {
      console.error('❌ Erro ao carregar dashboard:', error)
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
  }, [loading, processActivities])

  // Carregar dados automaticamente quando o componente monta
  useEffect(() => {
    if (!dashboardData && !loading) {
      loadDashboardData()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Reprocessar dados quando filtros mudarem
  useEffect(() => {
    if (dashboardData && dashboardData.rawActivities && users.length > 0 && departments.length > 0) {
      const processedData = processActivities(
        dashboardData.rawActivities,
        users,
        departments
      )
      setDashboardData(prev => ({ ...prev, ...processedData }))
    }
  }, [dateRange, selectedUser, selectedDepartment, processActivities, dashboardData?.rawActivities])

  const formatTime = (seconds) => {
    if (!seconds || seconds === 0) return '0min'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours === 0) {
      return `${minutes}min`
    }
    
    if (minutes === 0) {
      return `${hours}h`
    }
    
    return `${hours}h ${minutes}min`
  }

  const formatPercentage = (value, total) => {
    if (!total || total === 0) return '0%'
    return `${((value / total) * 100).toFixed(1)}%`
  }

  const formatDuration = (seconds) => {
    if (!seconds || seconds === 0) return '0s'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    if (hours > 0) {
      return `${hours}h ${minutes}min`
    } else if (minutes > 0) {
      return `${minutes}min ${secs}s`
    } else {
      return `${secs}s`
    }
  }

  const formatHour = (hour) => {
    return `${hour.toString().padStart(2, '0')}:00`
  }

  if (loading) {
    return <LoadingSpinner size="xl" text="Carregando dashboard..." fullScreen />
  }

  if (!dashboardData) {
    return (
      <div className="p-6">
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Bem-vindo, {user?.usuario}!
            </p>
          </div>
        </div>

        <div className="text-center py-12">
          <div className="text-gray-400 dark:text-gray-500">
            <ChartBarIcon className="mx-auto h-16 w-16 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Dashboard
            </h3>
            <p className="text-sm mb-6">
              Clique no botão abaixo para carregar os dados do dashboard
            </p>
            <button
              onClick={loadDashboardData}
              className="px-6 py-3 bg-indigo-600 text-white text-base font-medium rounded-md hover:bg-indigo-700"
            >
              Carregar Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  const { pieData, timelineData, userStats, summary, recentActivities, domainData, applicationData, hourlyData } = dashboardData

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Bem-vindo, {user?.usuario}!
          </p>
        </div>
        <button
          onClick={loadDashboardData}
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 flex items-center space-x-2"
        >
          <ArrowPathIcon className="h-4 w-4" />
          <span>Atualizar</span>
        </button>
      </div>

      {/* Controles */}
      <div className="mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Período:
            </label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(parseInt(e.target.value))}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
            >
              <option value={1}>Hoje</option>
              <option value={7}>Últimos 7 dias</option>
              <option value={30}>Últimos 30 dias</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Usuário:
            </label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
            >
              <option value="all">Todos os usuários</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Departamento:
            </label>
            <select
              value={selectedDepartment}
              onChange={(e) => setSelectedDepartment(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
            >
              <option value="all">Todos os departamentos</option>
              {departments.map(dept => (
                <option key={dept.id} value={dept.id}>
                  {dept.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Visualização:
            </label>
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
            >
              <option value="overview">Visão Geral</option>
              <option value="domains">Por Domínio</option>
              <option value="applications">Por Aplicação</option>
              <option value="timeline">Timeline Diária</option>
            </select>
          </div>
        </div>

        {/* Tabs de navegação */}
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
                className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  viewMode === tab.id
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Cards de Estatísticas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                    <div className="w-5 h-5 bg-green-500 rounded-md"></div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Tempo Produtivo
                    </p>
                    <div className="flex items-baseline space-x-2">
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {formatTime(summary.productive)}
                      </p>
                      <p className="text-sm font-medium text-green-600 dark:text-green-400">
                        {formatPercentage(summary.productive, summary.total)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                    <div className="w-5 h-5 bg-red-500 rounded-md"></div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Não Produtivo
                    </p>
                    <div className="flex items-baseline space-x-2">
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {formatTime(summary.nonproductive)}
                      </p>
                      <p className="text-sm font-medium text-red-600 dark:text-red-400">
                        {formatPercentage(summary.nonproductive, summary.total)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
                    <div className="w-5 h-5 bg-yellow-500 rounded-md"></div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Tempo Neutro
                    </p>
                    <div className="flex items-baseline space-x-2">
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {formatTime(summary.neutral)}
                      </p>
                      <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                        {formatPercentage(summary.neutral, summary.total)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                    <ClockIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Tempo Total
                    </p>
                    <div className="flex items-baseline space-x-2">
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {formatTime(summary.total)}
                      </p>
                      <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                        100%
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Conteúdo baseado na visualização selecionada */}
      {viewMode === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Gráfico de Pizza */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Distribuição por Produtividade
              </h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Total: {formatTime(summary.total)}
              </div>
            </div>
            {pieData.length > 0 ? (
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      innerRadius={40}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${(percent * 100).toFixed(1)}%`}
                      labelLine={false}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value, name) => [formatTime(value), name]}
                      labelFormatter={() => ''}
                    />
                  </PieChart>
                </ResponsiveContainer>
                
                {/* Legenda personalizada */}
                <div className="grid grid-cols-2 gap-3">
                  {pieData.map((entry, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: entry.color }}
                      ></div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {entry.name}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {formatTime(entry.value)} ({formatPercentage(entry.value, summary.total)})
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <ChartBarIcon className="mx-auto h-12 w-12 mb-2" />
                  <p className="text-sm">Nenhum dado disponível</p>
                </div>
              </div>
            )}
          </div>

          {/* Insights e Métricas */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Insights de Produtividade
              </h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Análise inteligente
              </div>
            </div>
            
            {summary.total > 0 ? (
              <div className="space-y-6">
                {/* Métricas principais */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 p-4 rounded-lg border border-green-200 dark:border-green-800">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                        <span className="text-white font-bold text-sm">
                          {Math.round((summary.productive / summary.total) * 100)}%
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-green-800 dark:text-green-200">
                          Taxa de Produtividade
                        </p>
                        <p className="text-xs text-green-600 dark:text-green-400">
                          {formatTime(summary.productive)} produtivo
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                        <ClockIcon className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                          Tempo Total Ativo
                        </p>
                        <p className="text-xs text-blue-600 dark:text-blue-400">
                          {formatTime(summary.total)} registrado
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center">
                        <span className="text-white font-bold text-xs">
                          {recentActivities.length}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-purple-800 dark:text-purple-200">
                          Atividades Recentes
                        </p>
                        <p className="text-xs text-purple-600 dark:text-purple-400">
                          Últimas sessões
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Gráfico de atividade por hora simplificado */}
                {hourlyData.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                      Atividade por Hora do Dia
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart data={hourlyData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <defs>
                          <linearGradient id="colorActivity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.1}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                        <XAxis 
                          dataKey="hour" 
                          tickFormatter={formatHour}
                          interval={3}
                          stroke="#6B7280"
                          fontSize={11}
                        />
                        <YAxis 
                          tickFormatter={(value) => value > 3600 ? `${Math.round(value/3600)}h` : `${Math.round(value/60)}m`}
                          stroke="#6B7280"
                          fontSize={11}
                        />
                        <Tooltip 
                          labelFormatter={(hour) => `${formatHour(hour)}`}
                          formatter={(value) => [formatTime(value), 'Atividade']}
                          contentStyle={{
                            backgroundColor: '#1F2937',
                            border: '1px solid #374151',
                            borderRadius: '6px',
                            color: '#F9FAFB',
                            fontSize: '12px'
                          }}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="total" 
                          stroke="#3B82F6" 
                          strokeWidth={2}
                          fillOpacity={1} 
                          fill="url(#colorActivity)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
                
                {/* Resumo textual */}
                <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                    📊 Resumo do Período
                  </h4>
                  <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <p>
                      • <strong>{Math.round((summary.productive / summary.total) * 100)}%</strong> do tempo foi produtivo
                      ({formatTime(summary.productive)})
                    </p>
                    <p>
                      • <strong>{Math.round((summary.nonproductive / summary.total) * 100)}%</strong> foi não produtivo
                      ({formatTime(summary.nonproductive)})
                    </p>
                    {summary.neutral > 0 && (
                      <p>
                        • <strong>{Math.round((summary.neutral / summary.total) * 100)}%</strong> foi neutro
                        ({formatTime(summary.neutral)})
                      </p>
                    )}
                    <p>
                      • Total de <strong>{recentActivities.length}</strong> atividades registradas
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <ChartBarIcon className="mx-auto h-16 w-16 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Nenhum dado disponível
                  </h3>
                  <p className="text-sm">
                    Carregue o dashboard para ver os insights
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {viewMode === 'domains' && (
        <div className="space-y-6 mb-6">
          {/* Lista de Domínios */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Top Domínios por Tempo de Uso
              </h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {domainData.length} domínios encontrados
              </div>
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
                          <div 
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                          ></div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <GlobeAltIcon className="w-4 h-4 text-gray-400" />
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                              {domain.name}
                            </p>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {domain.activities} atividade{domain.activities !== 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">
                            {formatTime(domain.value)}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {percentage.toFixed(1)}%
                          </p>
                        </div>
                        <div className="w-20 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div
                            className="h-2 rounded-full"
                            style={{ 
                              width: `${Math.min(percentage, 100)}%`,
                              backgroundColor: CHART_COLORS[index % CHART_COLORS.length]
                            }}
                          ></div>
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
          
          {/* Gráfico de Domínios */}
          {domainData.length > 0 && (
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                Distribuição Visual por Domínios
              </h2>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={domainData.slice(0, 8)} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis 
                    type="number" 
                    tickFormatter={formatTime}
                    stroke="#6B7280"
                  />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    width={150}
                    stroke="#6B7280"
                    fontSize={12}
                  />
                  <Tooltip 
                    formatter={(value, name) => [formatTime(value), 'Tempo de uso']}
                    labelFormatter={(label) => `${label}`}
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#F9FAFB'
                    }}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="#3B82F6"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {viewMode === 'applications' && (
        <div className="space-y-6 mb-6">
          {/* Lista de Aplicações */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Aplicações Mais Utilizadas
              </h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {applicationData.length} aplicações encontradas
              </div>
            </div>
            
            {applicationData.length > 0 ? (
              <div className="space-y-3">
                {applicationData.map((app, index) => {
                  const totalAppTime = applicationData.reduce((sum, a) => sum + a.value, 0)
                  const percentage = (app.value / totalAppTime) * 100
                  
                  // Ícones para aplicações conhecidas
                  const getAppIcon = (appName) => {
                    const name = appName.toLowerCase()
                    if (name.includes('chrome')) return '🌐'
                    if (name.includes('firefox')) return '🦊'
                    if (name.includes('edge')) return '🔷'
                    if (name.includes('code') || name.includes('visual studio')) return '💻'
                    if (name.includes('teams')) return '👥'
                    if (name.includes('outlook')) return '📧'
                    if (name.includes('word')) return '📄'
                    if (name.includes('excel')) return '📊'
                    if (name.includes('powerpoint')) return '📽️'
                    if (name.includes('slack')) return '💬'
                    if (name.includes('discord')) return '🎮'
                    if (name.includes('whatsapp')) return '💬'
                    if (name.includes('notepad')) return '📝'
                    if (name.includes('explorer')) return '📁'
                    return '⚡'
                  }
                  
                  return (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                      <div className="flex items-center space-x-4 flex-1 min-w-0">
                        <div className="flex-shrink-0 text-2xl">
                          {getAppIcon(app.name)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                              {app.name}
                            </p>
                            <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                              #{index + 1}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {app.activities} sessão{app.activities !== 1 ? 'ões' : ''} de uso
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white">
                            {formatTime(app.value)}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {percentage.toFixed(1)}% do tempo
                          </p>
                        </div>
                        <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div
                            className="h-2 rounded-full bg-gradient-to-r from-green-400 to-blue-500"
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                          ></div>
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
          
          {/* Gráfico de Aplicações */}
          {applicationData.length > 0 && (
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
                Comparativo de Uso por Aplicação
              </h2>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={applicationData.slice(0, 8)} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis 
                    type="number" 
                    tickFormatter={formatTime}
                    stroke="#6B7280"
                  />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    width={150}
                    stroke="#6B7280"
                    fontSize={12}
                  />
                  <Tooltip 
                    formatter={(value, name) => [formatTime(value), 'Tempo de uso']}
                    labelFormatter={(label) => `${label}`}
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#F9FAFB'
                    }}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="#10B981"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {viewMode === 'timeline' && (
        <div className="space-y-6 mb-6">
          {/* Resumo do Período */}
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-6 rounded-xl shadow-lg text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-2">
                  Análise Temporal
                </h2>
                <p className="text-blue-100">
                  Padrões de atividade nos últimos {dateRange} dia{dateRange > 1 ? 's' : ''}
                </p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold">
                  {timelineData.length}
                </div>
                <div className="text-blue-100 text-sm">
                  dias com atividade
                </div>
              </div>
            </div>
          </div>

          {/* Timeline Diária Melhorada */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Atividade Diária por Produtividade
              </h2>
              <div className="flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-gray-600 dark:text-gray-400">Produtivo</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span className="text-gray-600 dark:text-gray-400">Não Produtivo</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <span className="text-gray-600 dark:text-gray-400">Neutro</span>
                </div>
              </div>
            </div>
            
            {timelineData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={timelineData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(value) => format(new Date(value), 'dd/MM')}
                    stroke="#6B7280"
                  />
                  <YAxis 
                    tickFormatter={formatTime}
                    stroke="#6B7280"
                  />
                  <Tooltip 
                    formatter={(value, name) => [formatTime(value), name]}
                    labelFormatter={(label) => format(new Date(label), 'dd/MM/yyyy')}
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#F9FAFB'
                    }}
                  />
                  <Legend />
                  <Bar dataKey="productive" stackId="a" fill={COLORS.productive} name="Produtivo" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="nonproductive" stackId="a" fill={COLORS.nonproductive} name="Não Produtivo" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="neutral" stackId="a" fill={COLORS.neutral} name="Neutro" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="idle" stackId="a" fill={COLORS.idle} name="Ocioso" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <CalendarDaysIcon className="mx-auto h-16 w-16 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Nenhum dado de timeline
                  </h3>
                  <p className="text-sm">
                    Selecione um período diferente ou verifique os filtros
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Padrão Horário Melhorado */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Padrão de Atividade por Hora do Dia
              </h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Horário de pico: {hourlyData.length > 0 ? formatHour(hourlyData.reduce((max, hour) => hour.total > max.total ? hour : max, hourlyData[0])?.hour || 0) : 'N/A'}
              </div>
            </div>
            
            {hourlyData.length > 0 ? (
              <div className="space-y-4">
                {/* Gráfico de linha */}
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={hourlyData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.1}/>
                      </linearGradient>
                      <linearGradient id="colorProductive" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0.1}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                    <XAxis 
                      dataKey="hour" 
                      tickFormatter={formatHour}
                      interval={2}
                      stroke="#6B7280"
                    />
                    <YAxis 
                      tickFormatter={formatTime}
                      stroke="#6B7280"
                    />
                    <Tooltip 
                      labelFormatter={(hour) => `${formatHour(hour)}`}
                      formatter={(value, name) => [formatTime(value), name]}
                      contentStyle={{
                        backgroundColor: '#1F2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#F9FAFB'
                      }}
                    />
                    <Legend />
                    <Area 
                      type="monotone" 
                      dataKey="total" 
                      stroke="#3B82F6" 
                      fillOpacity={1} 
                      fill="url(#colorTotal)"
                      name="Total"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="productive" 
                      stroke="#10B981" 
                      fillOpacity={1} 
                      fill="url(#colorProductive)"
                      name="Produtivo"
                    />
                  </AreaChart>
                </ResponsiveContainer>
                
                {/* Estatísticas horárias */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {formatHour(hourlyData.reduce((max, hour) => hour.total > max.total ? hour : max, hourlyData[0])?.hour || 0)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Hora de pico</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {formatTime(Math.max(...hourlyData.map(h => h.productive)))}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Máx. produtivo</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                      {formatTime(hourlyData.reduce((sum, h) => sum + h.total, 0) / hourlyData.length)}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Média por hora</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {hourlyData.filter(h => h.total > 0).length}h
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Horas ativas</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <ClockIcon className="mx-auto h-16 w-16 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Nenhum padrão horário
                  </h3>
                  <p className="text-sm">
                    Dados insuficientes para análise horária
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Atividades Recentes */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Atividades Recentes
          </h2>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Últimas {recentActivities.length} atividades
          </div>
        </div>
        
        <div className="space-y-3">
          {recentActivities.length > 0 ? (
            recentActivities.map((activity, index) => (
              <div
                key={index}
                className="group flex items-start space-x-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200"
              >
                {/* Avatar/Icon */}
                <div className="flex-shrink-0 mt-1">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium text-white ${
                    activity.produtividade === 'productive' ? 'bg-green-500' :
                    activity.produtividade === 'nonproductive' ? 'bg-red-500' :
                    'bg-yellow-500'
                  }`}>
                    {activity.usuario_monitorado_nome?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                </div>
                
                {/* Content */}
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
                      
                      {/* Tags */}
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
                    
                    {/* Actions */}
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
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Nenhuma atividade encontrada
                </h3>
                <p className="text-sm">
                  Ajuste os filtros ou período para ver as atividades
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  )
}