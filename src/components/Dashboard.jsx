
import React, { useState, useCallback } from 'react'
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
  ResponsiveContainer
} from 'recharts'
import { ChartBarIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

const COLORS = {
  productive: '#10B981',
  nonproductive: '#EF4444',
  neutral: '#F59E0B',
  idle: '#6B7280'
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

  const loadDashboardData = useCallback(async () => {
    setLoading(true)
    try {
      console.log('🔄 Carregando dados do dashboard...')
      
      // Carregar dados básicos
      const [activitiesRes, usersRes, departmentsRes] = await Promise.all([
        api.get('/atividades?agrupar=true&limite=100'),
        api.get('/usuarios-monitorados'),
        api.get('/departamentos')
      ])

      const activities = Array.isArray(activitiesRes.data) ? activitiesRes.data : []
      const usersList = Array.isArray(usersRes.data) ? usersRes.data : []
      const departmentsList = Array.isArray(departmentsRes.data) ? departmentsRes.data : []

      setUsers(usersList)
      setDepartments(departmentsList)

      // Processar dados para o dashboard
      const processedData = processActivities(activities, usersList, departmentsList)
      setDashboardData(processedData)

      console.log('✅ Dashboard carregado com sucesso:', processedData.summary)
    } catch (error) {
      console.error('❌ Erro ao carregar dashboard:', error)
      setDashboardData({
        pieData: [],
        timelineData: [],
        userStats: [],
        summary: { productive: 0, nonproductive: 0, neutral: 0, idle: 0, total: 0 },
        recentActivities: []
      })
    } finally {
      setLoading(false)
    }
  }, [])

  const processActivities = (activities, usersList, departmentsList) => {
    const now = new Date()
    const startDate = startOfDay(subDays(now, dateRange))
    const endDate = endOfDay(now)

    // Filtrar atividades por data
    let filteredActivities = activities.filter(activity => {
      if (!activity?.horario) return false
      const activityDate = new Date(activity.horario)
      return activityDate >= startDate && activityDate <= endDate
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

    // Calcular resumo
    const summary = {
      productive: 0,
      nonproductive: 0,
      neutral: 0,
      idle: 0,
      total: 0
    }

    filteredActivities.forEach(activity => {
      const duration = activity.duracao || 10
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

    // Dados para gráfico de pizza
    const pieData = [
      { name: 'Produtivo', value: summary.productive, color: COLORS.productive },
      { name: 'Não Produtivo', value: summary.nonproductive, color: COLORS.nonproductive },
      { name: 'Neutro', value: summary.neutral, color: COLORS.neutral },
      { name: 'Ocioso', value: summary.idle, color: COLORS.idle }
    ].filter(item => item.value > 0)

    // Dados por dia
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

    // Estatísticas por usuário
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

    // Atividades recentes
    const recentActivities = filteredActivities
      .sort((a, b) => new Date(b.horario) - new Date(a.horario))
      .slice(0, 10)

    return {
      pieData,
      timelineData,
      userStats,
      summary,
      recentActivities
    }
  }

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
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

  const { pieData, timelineData, userStats, summary, recentActivities } = dashboardData

  return (
    <div className="p-6">
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
      <div className="mb-6 flex flex-wrap items-center gap-4">
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
                    Tempo Ocioso
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatTime(summary.idle)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Gráfico de Pizza */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Distribuição de Tempo
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

        {/* Gráfico de Barras */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Atividade por Dia
          </h2>
          {timelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
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
            <div className="flex items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
              Nenhum dado disponível
            </div>
          )}
        </div>
      </div>

      {/* Estatísticas por Usuário */}
      {userStats.length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow mb-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Estatísticas por Usuário
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Usuário
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Produtivo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Não Produtivo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Neutro
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Ocioso
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {userStats.map((stats, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {stats.nome}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 dark:text-green-400">
                      {formatTime(stats.productive)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 dark:text-red-400">
                      {formatTime(stats.nonproductive)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-yellow-600 dark:text-yellow-400">
                      {formatTime(stats.neutral)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                      {formatTime(stats.idle)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {formatTime(stats.total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
