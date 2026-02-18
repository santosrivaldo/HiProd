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
import GlobalFilters from './dashboard/GlobalFilters'
import AIInsights from './ai/AIInsights'
import { GRUPOS_FUNCIONALIDADE, getGrupoFromCategoria } from '../constants/productivityGroups'

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

// CÃ¡lculo consistente da duraÃ§Ã£o (segundos)
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

// Extrair domÃ­nio
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

// Extrair aplicaÃ§Ã£o
const extractApplicationFromWindow = (activeWindow) => {
  if (!activeWindow) return 'AplicaÃ§Ã£o Desconhecida'
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
  const appMatch = activeWindow.match(/^([^-â€“]+)/)
  if (appMatch) {
    const appName = appMatch[1].trim()
    if (appName.length > 0 && appName.length < 50) return appName
  }
  return 'AplicaÃ§Ã£o Desconhecida'
}

export default function Dashboard() {
  const { user } = useAuth()
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [periodDays, setPeriodDays] = useState(7)
  const [customStart, setCustomStart] = useState(format(subDays(new Date(), 7), 'yyyy-MM-dd'))
  const [customEnd, setCustomEnd] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [selectedUser, setSelectedUser] = useState('all')
  const [selectedDepartment, setSelectedDepartment] = useState('all')
  const [selectedGroup, setSelectedGroup] = useState('all')
  const [selectedApplication, setSelectedApplication] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedUserForTimeline, setSelectedUserForTimeline] = useState(null)
  const [users, setUsers] = useState([])
  const [departments, setDepartments] = useState([])
  const navigate = useNavigate()

  // Carregar dados do dashboard
  const loadDashboardData = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      console.log('ðŸ”„ Carregando dados do dashboard...')
      
      const [activitiesRes, usersRes, departmentsRes] = await Promise.all([
        api.get('/atividades?agrupar=true&limite=1000'),
        api.get('/usuarios-monitorados'),
        api.get('/departamentos')
      ])

      const activities = Array.isArray(activitiesRes.data) ? activitiesRes.data : []
      const usersList = Array.isArray(usersRes.data) ? usersRes.data : []
      const departmentsList = Array.isArray(departmentsRes.data) ? departmentsRes.data : []

      console.log(`ðŸ“¦ Dados recebidos: ${activities.length} atividades, ${usersList.length} usuÃ¡rios, ${departmentsList.length} departamentos`)

      setUsers(usersList)
      setDepartments(departmentsList)

      // Processar atividades - perÃ­odo
      const now = new Date()
      let startDate, endDate
      if (periodDays === 'custom' && customStart && customEnd) {
        startDate = startOfDay(parseISO(customStart))
        endDate = endOfDay(parseISO(customEnd))
      } else {
        const days = typeof periodDays === 'number' ? periodDays : 7
        startDate = startOfDay(subDays(now, days))
        endDate = endOfDay(now)
      }

      // Filtrar atividades por data
      let filteredActivities = activities.filter(activity => {
        if (!activity?.horario) return false
        const activityDate = safeParseDate(activity.horario)
        if (!activityDate) return false
        const activityDateOnly = new Date(activityDate.getFullYear(), activityDate.getMonth(), activityDate.getDate())
        const startDateOnly = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate())
        const endDateOnly = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate())
        return activityDateOnly >= startDateOnly && activityDateOnly <= endDateOnly
      })

      // Filtrar por usuÃ¡rio
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

      // Filtrar por status (Produtivo | Neutro | NÃ£o produtivo)
      if (statusFilter && statusFilter !== 'all') {
        filteredActivities = filteredActivities.filter(activity => {
          const produtividade = activity.produtividade || 'neutral'
          const ociosidade = activity.ociosidade || 0
          if (statusFilter === 'idle') return ociosidade >= 600
          return produtividade === statusFilter
        })
      }

      // Filtrar por aplicaÃ§Ã£o
      if (selectedApplication && selectedApplication !== 'all') {
        filteredActivities = filteredActivities.filter(activity => {
          const app = activity.application || extractApplicationFromWindow(activity.active_window)
          return app === selectedApplication
        })
      }

      // Filtrar por grupo de pÃ¡ginas
      if (selectedGroup && selectedGroup !== 'all') {
        filteredActivities = filteredActivities.filter(activity => {
          const app = activity.application || extractApplicationFromWindow(activity.active_window)
          const grupo = getGrupoFromCategoria(activity.categoria, app)
          return grupo === selectedGroup
        })
      }

      console.log(`âœ… ${filteredActivities.length} atividades apÃ³s filtros`)

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
        
        // Adicionar tempo de presenÃ§a facial ao summary
        if (activity.face_presence_time) {
          summary.facePresence += activity.face_presence_time
        }
      })

      // Processar dados por domÃ­nio
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

      // Processar dados por aplicaÃ§Ã£o
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

      // Processar dados diÃ¡rios
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

      // Processar estatÃ­sticas por usuÃ¡rio
      const userStatsMap = {}
      const presenceStatsMap = {} // EstatÃ­sticas de presenÃ§a facial
      
      filteredActivities.forEach(activity => {
        if (!activity?.usuario_monitorado_id) return
        
        const userId = activity.usuario_monitorado_id
        const userName = activity.usuario_monitorado_nome ||
                        usersList.find(u => u.id === userId)?.nome ||
                        `UsuÃ¡rio ${userId}`

        const userObj = usersList.find(u => u.id === userId)
        const departamentoNome = userObj?.departamento?.nome || userObj?.departamento_nome || 'â€”'
        if (!userStatsMap[userId]) {
          userStatsMap[userId] = {
            id: userId,
            nome: userName,
            departamento: departamentoNome,
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
        
        // Processar dados de presenÃ§a facial
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
      
      // Calcular tempo total de presenÃ§a no summary
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

      // Tempo por aplicaÃ§Ã£o (com referÃªncia a print/screenshot)
      const timeByAppKey = {}
      filteredActivities.forEach(activity => {
        const duration = getActivityDurationSeconds(activity)
        if (duration <= 0) return
        const app = activity.application || extractApplicationFromWindow(activity.active_window)
        const grupo = getGrupoFromCategoria(activity.categoria, app)
        const userName = activity.usuario_monitorado_nome || usersList.find(u => u.id === activity.usuario_monitorado_id)?.nome || `UsuÃ¡rio ${activity.usuario_monitorado_id}`
        const key = `${activity.usuario_monitorado_id}|${app}`
        if (!timeByAppKey[key]) {
          timeByAppKey[key] = {
            userId: activity.usuario_monitorado_id,
            userName,
            application: app,
            grupoFuncionalidade: grupo,
            tempoTotal: 0,
            classificacao: activity.produtividade === 'productive' ? 'Produtivo' : activity.produtividade === 'nonproductive' ? 'NÃ£o produtivo' : 'Neutro',
            activityIdForScreenshot: activity.has_screenshot ? activity.id : null
          }
        }
        timeByAppKey[key].tempoTotal += duration
        if (activity.has_screenshot && !timeByAppKey[key].activityIdForScreenshot) {
          timeByAppKey[key].activityIdForScreenshot = activity.id
        }
      })
      const timeByApplication = Object.values(timeByAppKey).sort((a, b) => b.tempoTotal - a.tempoTotal)

      // Timeline por usuÃ¡rio (para detalhamento)
      const userTimelineMap = {}
      const sortedByHorario = [...filteredActivities].sort((a, b) => {
        const dateA = safeParseDate(a.horario)
        const dateB = safeParseDate(b.horario)
        if (!dateA || !dateB) return 0
        return dateA - dateB
      })
      sortedByHorario.forEach(activity => {
        const uid = activity.usuario_monitorado_id
        if (!userTimelineMap[uid]) userTimelineMap[uid] = []
        userTimelineMap[uid].push({
          ...activity,
          application: activity.application || extractApplicationFromWindow(activity.active_window),
          classificacao: activity.produtividade === 'productive' ? 'Produtivo' : activity.produtividade === 'nonproductive' ? 'NÃ£o produtivo' : 'Neutro'
        })
      })

      // OpÃ§Ãµes para filtro de grupo (grupos de funcionalidade)
      const groupOptions = GRUPOS_FUNCIONALIDADE.map(g => ({ value: g.grupo, label: g.grupo }))

      // Dados do grÃ¡fico de pizza
      const pieData = [
        { name: 'Produtivo', value: summary.productive, color: COLORS.productive },
        { name: 'NÃ£o Produtivo', value: summary.nonproductive, color: COLORS.nonproductive },
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
        rawActivities: activities,
        filteredActivities,
        timeByApplication,
        userTimelineMap,
        groupOptions
      }

      console.log('âœ… Dashboard processado:', {
        summary,
        timelineDays: timelineData.length,
        recentActivities: recentActivities.length
      })

      setDashboardData(processedData)
    } catch (err) {
      console.error('âŒ Erro ao carregar dashboard:', err)
      setError(err.message || 'Erro ao carregar dados do dashboard')
      setDashboardData({
        pieData: [],
        timelineData: [],
        userStats: [],
        summary: { productive: 0, nonproductive: 0, neutral: 0, idle: 0, total: 0 },
        recentActivities: [],
        domainData: [],
        applicationData: [],
        hourlyData: [],
        filteredActivities: [],
        timeByApplication: [],
        userTimelineMap: {},
        groupOptions: []
      })
    } finally {
      setLoading(false)
    }
  }, [periodDays, customStart, customEnd, selectedUser, selectedDepartment, selectedGroup, selectedApplication, statusFilter])

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
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Nenhum dado disponÃ­vel</h3>
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

  const {
    pieData,
    timelineData,
    userStats = [],
    summary = {},
    recentActivities = [],
    domainData = [],
    applicationData = [],
    hourlyData = [],
    presenceStats = [],
    totalPresenceTime = 0,
    timeByApplication = [],
    userTimelineMap = {},
    groupOptions = []
  } = dashboardData || {}

  const filteredActivities = dashboardData?.filteredActivities || []
  const productividadeMedia = summary.total > 0
    ? ((summary.productive / summary.total) * 100).toFixed(1)
    : '0'
  const usuariosMonitoradosCount = users.length

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
          Dashboard de Produtividade
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Bem-vindo, <span className="font-semibold">{user?.usuario}</span>. Filtros globais e anÃ¡lise integrada.
        </p>
      </div>

      {/* 1. Filtros Globais */}
      <GlobalFilters
        periodDays={periodDays}
        onPeriodChange={setPeriodDays}
        customStart={customStart}
        customEnd={customEnd}
        onCustomStartChange={setCustomStart}
        onCustomEndChange={setCustomEnd}
        selectedDepartment={selectedDepartment}
        onDepartmentChange={setSelectedDepartment}
        selectedGroup={selectedGroup}
        onGroupChange={setSelectedGroup}
        selectedApplication={selectedApplication}
        onApplicationChange={setSelectedApplication}
        selectedUser={selectedUser}
        onUserChange={setSelectedUser}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        departments={departments}
        users={users}
        applicationOptions={applicationData}
        groupOptions={groupOptions}
        onRefresh={loadDashboardData}
        loading={loading}
      />

      {/* 2. Resumo Geral */}
      <section className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Resumo geral</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">UsuÃ¡rios monitorados</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{usuariosMonitoradosCount}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo produtivo total</p>
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">{formatTime(summary.productive)}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo nÃ£o produtivo</p>
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">{formatTime(summary.nonproductive)}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo neutro</p>
            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{formatTime(summary.neutral)}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Produtividade mÃ©dia</p>
            <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{productividadeMedia}%</p>
          </div>
        </div>
      </section>

      {/* 3. Produtividade por UsuÃ¡rio */}
      <section className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white p-6 pb-0">Produtividade por usuÃ¡rio</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">UsuÃ¡rio</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Departamento</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo produtivo</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo nÃ£o produtivo</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo neutro</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">% Produtividade</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Detalhes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {userStats.map((u) => {
                const pct = u.total > 0 ? ((u.productive / u.total) * 100).toFixed(0) : 0
                return (
                  <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{u.nome}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{u.departamento || 'â€”'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600 dark:text-green-400">{formatTime(u.productive)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600 dark:text-red-400">{formatTime(u.nonproductive)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-amber-600 dark:text-amber-400">{formatTime(u.neutral)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900 dark:text-white">{pct}%</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={() => setSelectedUserForTimeline(selectedUserForTimeline === u.id ? null : u.id)}
                        className="text-indigo-600 dark:text-indigo-400 hover:underline text-sm font-medium"
                      >
                        Ver
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {userStats.length === 0 && (
          <p className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">Nenhum dado no perÃ­odo.</p>
        )}
      </section>

      {/* 4. Tempo por AplicaÃ§Ã£o (com Print) */}
      <section className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white p-6 pb-0">Tempo por aplicaÃ§Ã£o</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">UsuÃ¡rio</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">AplicaÃ§Ã£o</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Grupo de funcionalidade</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo total</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">ClassificaÃ§Ã£o</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Print</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {timeByApplication.slice(0, 50).map((row, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{row.userName}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">{row.application}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{row.grupoFuncionalidade}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">{formatTime(row.tempoTotal)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                      row.classificacao === 'Produtivo' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                      row.classificacao === 'NÃ£o produtivo' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' :
                      'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                    }`}>
                      {row.classificacao}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    {row.activityIdForScreenshot ? (
                      <button
                        onClick={() => navigate(`/screenshots/${row.activityIdForScreenshot}`)}
                        className="text-indigo-600 dark:text-indigo-400 hover:underline text-sm font-medium inline-flex items-center gap-1"
                      >
                        <PhotoIcon className="w-4 h-4" /> Ver screenshot
                      </button>
                    ) : (
                      <span className="text-gray-400 text-sm">â€”</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {timeByApplication.length === 0 && (
          <p className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">Nenhum dado no perÃ­odo.</p>
        )}
      </section>

      {/* 5. Agrupamento de PÃ¡ginas por Funcionalidade (referÃªncia) */}
      <section className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white p-6 pb-0">Agrupamento de pÃ¡ginas por funcionalidade</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Grupo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Exemplos de pÃ¡ginas / aplicaÃ§Ãµes</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">ClassificaÃ§Ã£o padrÃ£o</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {GRUPOS_FUNCIONALIDADE.map((g, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{g.grupo}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{g.exemplos}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">{g.classificacao}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 6. Detalhamento (Timeline do UsuÃ¡rio) */}
      <section className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Detalhamento â€” Timeline do usuÃ¡rio</h2>
        {selectedUserForTimeline ? (
          (() => {
            const timeline = userTimelineMap[selectedUserForTimeline] || []
            const u = userStats.find(us => us.id === selectedUserForTimeline)
            return (
              <>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  UsuÃ¡rio: <span className="font-semibold text-gray-900 dark:text-white">{u?.nome || selectedUserForTimeline}</span>
                  <button onClick={() => setSelectedUserForTimeline(null)} className="ml-3 text-indigo-600 dark:text-indigo-400 hover:underline text-sm">Fechar</button>
                </p>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {timeline.map((act, i) => (
                    <div key={i} className="flex items-center gap-4 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                      <span className="text-sm font-mono text-gray-500 dark:text-gray-400 w-24 shrink-0">
                        {formatBrasiliaDate(act.horario, 'time')}
                      </span>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{act.application}</span>
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                        act.classificacao === 'Produtivo' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                        act.classificacao === 'NÃ£o produtivo' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' :
                        'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                      }`}>
                        {act.classificacao}
                      </span>
                    </div>
                  ))}
                </div>
                {timeline.length === 0 && <p className="text-gray-500 dark:text-gray-400 text-sm">Nenhuma atividade no perÃ­odo.</p>}
              </>
            )
          })()
        ) : (
          <p className="text-gray-500 dark:text-gray-400 text-sm">Clique em &quot;Ver&quot; na tabela Produtividade por usuÃ¡rio para exibir a timeline.</p>
        )}
      </section>

      {/* 7. Insights automÃ¡ticos */}
      <section className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Insights automÃ¡ticos</h2>
        <AIInsights data={dashboardData} onAnalyze={loadDashboardData} />
      </section>
    </div>
  )
}
