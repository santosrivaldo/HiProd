
import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { format, subDays, startOfDay, endOfDay } from 'date-fns'
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
  }, [loading])

  const processActivities = useCallback((activities, usersList, departmentsList) => {
    const now = new Date()
    const startDate = startOfDay(subDays(now, dateRange))
    const endDate = endOfDay(now)

    console.log(`📊 Processando ${activities.length} atividades no período de ${startDate.toISOString()} a ${endDate.toISOString()}`)

    let filteredActivities = activities.filter(activity => {
      if (!activity?.horario) return false
      const activityDate = new Date(activity.horario)
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
      const duration = activity.duracao || activity.duracao_total || 10
      summary.total += duration

      const produtividade = activity.produtividade || 'neutral'
      if (summary[produtividade] !== undefined) {
        summary[produtividade] += duration
      } else {
        if (activity.ociosidade >= 600) {
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
      let domain = activity.domain
      if (!domain) {
        domain = extractDomainFromWindow(activity.active_window) || 'Sistema Local'
      }
      const duration = activity.duracao || activity.duracao_total || 10
      
      if (!domainMap[domain]) {
        domainMap[domain] = { name: domain, value: 0, activities: 0 }
      }
      domainMap[domain].value += duration
      domainMap[domain].activities += activity.eventos_agrupados || 1
    })

    const domainData = Object.values(domainMap)
      .sort((a, b) => b.value - a.value)
      .slice(0, 10)

    console.log('🌐 Dados de domínio processados:', domainData)

    // Processar dados por aplicação
    const applicationMap = {}
    filteredActivities.forEach(activity => {
      let application = activity.application
      if (!application) {
        application = extractApplicationFromWindow(activity.active_window) || 'Aplicação Desconhecida'
      }
      const duration = activity.duracao || activity.duracao_total || 10
      
      if (!applicationMap[application]) {
        applicationMap[application] = { name: application, value: 0, activities: 0 }
      }
      applicationMap[application].value += duration
      applicationMap[application].activities += activity.eventos_agrupados || 1
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
      const hour = new Date(activity.horario).getHours()
      const duration = activity.duracao || 10
      const produtividade = activity.produtividade || 'neutral'
      
      hourlyMap[hour].total += duration
      if (hourlyMap[hour][produtividade] !== undefined) {
        hourlyMap[hour][produtividade] += duration
      } else {
        if (activity.ociosidade >= 600) {
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
      const day = format(new Date(activity.horario), 'yyyy-MM-dd')
      if (!dailyData[day]) {
        dailyData[day] = {
          date: day,
          productive: 0,
          nonproductive: 0,
          neutral: 0,
          idle: 0
        }
      }

      const duration = activity.duracao || 10
      const produtividade = activity.produtividade || 'neutral'

      if (dailyData[day][produtividade] !== undefined) {
        dailyData[day][produtividade] += duration
      } else {
        if (activity.ociosidade >= 600) {
          dailyData[day].idle += duration
        } else {
          dailyData[day].neutral += duration
        }
      }
    })

    const timelineData = Object.values(dailyData).sort((a, b) => a.date.localeCompare(b.date))

    const userStatsMap = {}
    filteredActivities.forEach(activity => {
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

      const duration = activity.duracao || 10
      const produtividade = activity.produtividade || 'neutral'

      userStatsMap[userId].total += duration
      if (userStatsMap[userId][produtividade] !== undefined) {
        userStatsMap[userId][produtividade] += duration
      } else {
        if (activity.ociosidade >= 600) {
          userStatsMap[userId].idle += duration
        } else {
          userStatsMap[userId].neutral += duration
        }
      }
    })

    const userStats = Object.values(userStatsMap)

    const recentActivities = filteredActivities
      .sort((a, b) => new Date(b.horario) - new Date(a.horario))
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
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
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
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-md flex items-center justify-center">
                  <div className="w-4 h-4 bg-green-500 rounded"></div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Tempo Produtivo
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatTime(summary.productive)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-red-100 dark:bg-red-900 rounded-md flex items-center justify-center">
                  <div className="w-4 h-4 bg-red-500 rounded"></div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Tempo Não Produtivo
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatTime(summary.nonproductive)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-yellow-100 dark:bg-yellow-900 rounded-md flex items-center justify-center">
                  <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Tempo Neutro
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatTime(summary.neutral)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded-md flex items-center justify-center">
                  <div className="w-4 h-4 bg-gray-500 rounded"></div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Tempo Total
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatTime(summary.total)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Conteúdo baseado na visualização selecionada */}
      {viewMode === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Gráfico de Pizza */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Distribuição de Tempo por Produtividade
            </h2>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatTime(value)} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>

          {/* Timeline por Hora */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Distribuição por Hora do Dia
            </h2>
            {hourlyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={hourlyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="hour" 
                    tickFormatter={formatHour}
                    interval={2}
                  />
                  <YAxis tickFormatter={formatTime} />
                  <Tooltip 
                    labelFormatter={(hour) => `${formatHour(hour)}`}
                    formatter={(value, name) => [formatTime(value), name]}
                  />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="total" 
                    stackId="1" 
                    stroke="#3B82F6" 
                    fill="#3B82F6" 
                    fillOpacity={0.6}
                    name="Total"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>
        </div>
      )}

      {viewMode === 'domains' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Top Domínios */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Top 10 Domínios por Tempo
            </h2>
            {domainData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={domainData} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tickFormatter={formatTime} />
                  <YAxis dataKey="name" type="category" width={120} />
                  <Tooltip 
                    formatter={(value, name) => [formatTime(value), name]}
                    labelFormatter={(label) => `Domínio: ${label}`}
                  />
                  <Bar dataKey="value" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>

          {/* Domínios em Pizza */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Distribuição por Domínios
            </h2>
            {domainData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                  <Pie
                    data={domainData}
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {domainData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatTime(value)} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>
        </div>
      )}

      {viewMode === 'applications' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Top Aplicações */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Top 10 Aplicações por Tempo
            </h2>
            {applicationData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={applicationData} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tickFormatter={formatTime} />
                  <YAxis dataKey="name" type="category" width={120} />
                  <Tooltip 
                    formatter={(value, name) => [formatTime(value), name]}
                    labelFormatter={(label) => `Aplicação: ${label}`}
                  />
                  <Bar dataKey="value" fill="#10B981" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>

          {/* Aplicações em Pizza */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Distribuição por Aplicações
            </h2>
            {applicationData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                  <Pie
                    data={applicationData}
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {applicationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatTime(value)} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>
        </div>
      )}

      {viewMode === 'timeline' && (
        <div className="grid grid-cols-1 gap-6 mb-6">
          {/* Timeline Diária Completa */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Timeline Diária de Atividades
            </h2>
            {timelineData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={timelineData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickFormatter={(value) => format(new Date(value), 'dd/MM')} />
                  <YAxis tickFormatter={formatTime} />
                  <Tooltip formatter={(value) => formatTime(value)} />
                  <Legend />
                  <Bar dataKey="productive" stackId="a" fill={COLORS.productive} name="Produtivo" />
                  <Bar dataKey="nonproductive" stackId="a" fill={COLORS.nonproductive} name="Não Produtivo" />
                  <Bar dataKey="neutral" stackId="a" fill={COLORS.neutral} name="Neutro" />
                  <Bar dataKey="idle" stackId="a" fill={COLORS.idle} name="Ocioso" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>

          {/* Distribuição Horária */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Padrão de Uso por Hora
            </h2>
            {hourlyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={hourlyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="hour" 
                    tickFormatter={formatHour}
                    interval={2}
                  />
                  <YAxis tickFormatter={formatTime} />
                  <Tooltip 
                    labelFormatter={(hour) => `${formatHour(hour)}`}
                    formatter={(value, name) => [formatTime(value), name]}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="productive" 
                    stroke={COLORS.productive} 
                    strokeWidth={2}
                    name="Produtivo"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="nonproductive" 
                    stroke={COLORS.nonproductive} 
                    strokeWidth={2}
                    name="Não Produtivo"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="neutral" 
                    stroke={COLORS.neutral} 
                    strokeWidth={2}
                    name="Neutro"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
                Nenhum dado disponível
              </div>
            )}
          </div>
        </div>
      )}

      {/* Atividades Recentes */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Atividades Recentes
        </h2>
        <div className="space-y-4">
          {recentActivities.length > 0 ? (
            recentActivities.map((activity, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {activity.active_window}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-300">
                    {activity.usuario_monitorado_nome} • {format(new Date(activity.horario), 'dd/MM/yyyy HH:mm')}
                  </p>
                  {activity.domain && (
                    <p className="text-xs text-blue-600 dark:text-blue-400">
                      🌐 {activity.domain}
                    </p>
                  )}
                  {activity.application && (
                    <p className="text-xs text-green-600 dark:text-green-400">
                      💻 {activity.application}
                    </p>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      activity.produtividade === 'productive'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : activity.produtividade === 'nonproductive'
                        ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                    }`}
                  >
                    {activity.categoria || activity.produtividade || 'neutral'}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8">
              <div className="text-gray-400 dark:text-gray-500">
                <ChartBarIcon className="mx-auto h-12 w-12 mb-4" />
                <p className="text-sm">Nenhuma atividade encontrada</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
