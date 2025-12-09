import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format, subDays, startOfDay, endOfDay, parseISO } from 'date-fns'
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

      console.log(`✅ ${filteredActivities.length} atividades após filtros`)

      // Calcular summary
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
  }, [dateRange, selectedUser, selectedDepartment])

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
    return `${((value / total) * 100).toFixed(1)}%`
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

  const { pieData, timelineData, userStats, summary, recentActivities, domainData, applicationData, hourlyData, presenceStats = [], totalPresenceTime = 0 } = dashboardData

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">Bem-vindo, {user?.usuario}!</p>
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
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Período:</label>
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
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Usuário:</label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
            >
              <option value="all">Todos os usuários</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>{user.nome}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Departamento:</label>
            <select
              value={selectedDepartment}
              onChange={(e) => setSelectedDepartment(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
            >
              <option value="all">Todos os departamentos</option>
              {departments.map(dept => (
                <option key={dept.id} value={dept.id}>{dept.nome}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Visualização:</label>
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

        {/* Tabs */}
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
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <div className="w-5 h-5 bg-green-500 rounded-md"></div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Tempo Produtivo</p>
                <div className="flex items-baseline space-x-2">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatTime(summary.productive)}</p>
                  <p className="text-sm font-medium text-green-600 dark:text-green-400">
                    {formatPercentage(summary.productive, summary.total)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                <div className="w-5 h-5 bg-red-500 rounded-md"></div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Não Produtivo</p>
                <div className="flex items-baseline space-x-2">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatTime(summary.nonproductive)}</p>
                  <p className="text-sm font-medium text-red-600 dark:text-red-400">
                    {formatPercentage(summary.nonproductive, summary.total)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
                <div className="w-5 h-5 bg-yellow-500 rounded-md"></div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Tempo Neutro</p>
                <div className="flex items-baseline space-x-2">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatTime(summary.neutral)}</p>
                  <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                    {formatPercentage(summary.neutral, summary.total)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <ClockIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Tempo Total</p>
                <div className="flex items-baseline space-x-2">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{formatTime(summary.total)}</p>
                  <p className="text-sm font-medium text-blue-600 dark:text-blue-400">100%</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Seção de Relatório de Presença Facial */}
      {presenceStats.length > 0 && (
        <div className="mb-6 bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Relatório de Presença Facial</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">Tempo detectado em frente ao computador</p>
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            {presenceStats
              .sort((a, b) => b.maxPresenceTime - a.maxPresenceTime)
              .map((stat, index) => {
                const hours = Math.floor(stat.maxPresenceTime / 3600)
                const minutes = Math.floor((stat.maxPresenceTime % 3600) / 60)
                const percentage = summary.total > 0 ? (stat.maxPresenceTime / summary.total) * 100 : 0
                
                return (
                  <div key={index} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                    <div className="flex items-center space-x-4 flex-1 min-w-0">
                      <div className="flex-shrink-0 w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center">
                        <span className="text-purple-600 dark:text-purple-400 font-bold text-sm">#{index + 1}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{stat.nome}</p>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {stat.activitiesWithPresence} registro{stat.activitiesWithPresence !== 1 ? 's' : ''} com detecção
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {hours > 0 ? `${hours}h ${minutes}min` : `${minutes}min`}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{percentage.toFixed(1)}% do tempo total</p>
                      </div>
                      <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div 
                          className="h-2 rounded-full bg-gradient-to-r from-purple-400 to-pink-500" 
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      )}

      {/* Conteúdo baseado na visualização */}
      {viewMode === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Gráfico de Pizza */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Distribuição por Produtividade</h2>
              <div className="text-sm text-gray-500 dark:text-gray-400">Total: {formatTime(summary.total)}</div>
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
                    <Tooltip formatter={(value) => formatTime(value)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-2 gap-3">
                  {pieData.map((entry, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }}></div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-white truncate">{entry.name}</div>
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

          {/* Insights */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Insights de Produtividade</h2>
            </div>
            {summary.total > 0 ? (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 p-4 rounded-lg border border-green-200 dark:border-green-800">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                        <span className="text-white font-bold text-sm">
                          {Math.round((summary.productive / summary.total) * 100)}%
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-green-800 dark:text-green-200">Taxa de Produtividade</p>
                        <p className="text-xs text-green-600 dark:text-green-400">{formatTime(summary.productive)} produtivo</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                        <ClockIcon className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-blue-800 dark:text-blue-200">Tempo Total Ativo</p>
                        <p className="text-xs text-blue-600 dark:text-blue-400">{formatTime(summary.total)} registrado</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center">
                        <span className="text-white font-bold text-xs">{recentActivities.length}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-purple-800 dark:text-purple-200">Atividades Recentes</p>
                        <p className="text-xs text-purple-600 dark:text-purple-400">Últimas sessões</p>
                      </div>
                    </div>
                  </div>
                </div>
                {hourlyData.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">Atividade por Hora do Dia</h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart data={hourlyData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <defs>
                          <linearGradient id="colorActivity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.1}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                        <XAxis dataKey="hour" tickFormatter={formatHour} interval={3} stroke="#6B7280" fontSize={11} />
                        <YAxis tickFormatter={(value) => value > 3600 ? `${Math.round(value/3600)}h` : `${Math.round(value/60)}m`} stroke="#6B7280" fontSize={11} />
                        <Tooltip labelFormatter={(hour) => `${formatHour(hour)}`} formatter={(value) => [formatTime(value), 'Atividade']} />
                        <Area type="monotone" dataKey="total" stroke="#3B82F6" strokeWidth={2} fillOpacity={1} fill="url(#colorActivity)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
                <div className="text-center">
                  <ChartBarIcon className="mx-auto h-16 w-16 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Nenhum dado disponível</h3>
                  <p className="text-sm">Carregue o dashboard para ver os insights</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {viewMode === 'domains' && (
        <div className="space-y-6 mb-6">
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

      {/* Seção de Relatório de Presença Facial */}
      {presenceStats.length > 0 && (
        <div className="mb-6 bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Relatório de Presença Facial</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">Tempo detectado em frente ao computador</p>
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            {presenceStats
              .sort((a, b) => b.maxPresenceTime - a.maxPresenceTime)
              .map((stat, index) => {
                const hours = Math.floor(stat.maxPresenceTime / 3600)
                const minutes = Math.floor((stat.maxPresenceTime % 3600) / 60)
                const percentage = summary.total > 0 ? (stat.maxPresenceTime / summary.total) * 100 : 0
                
                return (
                  <div key={index} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                    <div className="flex items-center space-x-4 flex-1 min-w-0">
                      <div className="flex-shrink-0 w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center">
                        <span className="text-purple-600 dark:text-purple-400 font-bold text-sm">#{index + 1}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{stat.nome}</p>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {stat.activitiesWithPresence} registro{stat.activitiesWithPresence !== 1 ? 's' : ''} com detecção
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">
                          {hours > 0 ? `${hours}h ${minutes}min` : `${minutes}min`}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{percentage.toFixed(1)}% do tempo total</p>
                      </div>
                      <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div 
                          className="h-2 rounded-full bg-gradient-to-r from-purple-400 to-pink-500" 
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      )}

      {viewMode === 'timeline' && (
        <div className="space-y-6 mb-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Atividade Diária por Produtividade</h2>
            </div>
            {timelineData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={timelineData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis dataKey="date" tickFormatter={(value) => format(parseISO(value), 'dd/MM')} stroke="#6B7280" />
                  <YAxis tickFormatter={formatTime} stroke="#6B7280" />
                  <Tooltip formatter={(value) => formatTime(value)} labelFormatter={(label) => format(parseISO(label), 'dd/MM/yyyy')} />
                  <Legend />
                  <Bar dataKey="productive" stackId="a" fill={COLORS.productive} name="Produtivo" />
                  <Bar dataKey="nonproductive" stackId="a" fill={COLORS.nonproductive} name="Não Produtivo" />
                  <Bar dataKey="neutral" stackId="a" fill={COLORS.neutral} name="Neutro" />
                  <Bar dataKey="idle" stackId="a" fill={COLORS.idle} name="Ocioso" />
                </BarChart>
              </ResponsiveContainer>
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
