import React, { useState, useEffect } from 'react'
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
  LineChart,
  Line,
  ResponsiveContainer
} from 'recharts'
import { ChartBarIcon } from '@heroicons/react/outline'

const COLORS = {
  productive: '#10B981',
  nonproductive: '#EF4444',
  neutral: '#F59E0B',
  idle: '#6B7280'
}

export default function Dashboard() {
  const { user } = useAuth()
  const [activities, setActivities] = useState([])
  const [usuariosMonitorados, setUsuariosMonitorados] = useState([])
  const [departamentos, setDepartamentos] = useState([])
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState(7)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [selectedUser, setSelectedUser] = useState('all')
  const [selectedDepartment, setSelectedDepartment] = useState('all')

  useEffect(() => {
    fetchData()

    let interval
    if (autoRefresh) {
      interval = setInterval(fetchData, 30000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [dateRange, autoRefresh])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [activitiesRes, usuariosRes, departamentosRes] = await Promise.all([
        api.get('/atividades?agrupar=true'),
        api.get('/usuarios-monitorados'),
        api.get('/departamentos')
      ])

      // Validar e filtrar dados antes de definir no state
      const validActivities = Array.isArray(activitiesRes.data) ? activitiesRes.data : []
      const validUsuarios = Array.isArray(usuariosRes.data) ? 
        usuariosRes.data.filter(u => u && u.id && u.nome) : []
      const validDepartamentos = Array.isArray(departamentosRes.data) ? 
        departamentosRes.data.filter(d => d && d.id && d.nome) : []

      setActivities(validActivities)
      setUsuariosMonitorados(validUsuarios)
      setDepartamentos(validDepartamentos)

      console.log('Dados carregados:', {
        atividades: validActivities.length,
        usuarios: validUsuarios.length,
        departamentos: validDepartamentos.length
      })
    } catch (error) {
      console.error('Erro ao buscar dados:', error)
      setActivities([])
      setUsuariosMonitorados([])
      setDepartamentos([])
    } finally {
      setLoading(false)
    }
  }

  const processActivityData = () => {
    const now = new Date()
    const startDate = startOfDay(subDays(now, dateRange))
    const endDate = endOfDay(now)

    // Validar se temos dados
    if (!Array.isArray(activities)) {
      return { pieData: [], timelineData: [], totalTime: 0, userStats: {}, recentActivities: [] }
    }

    // Filtrar atividades por data
    let filteredActivities = activities.filter(activity => {
      if (!activity || !activity.horario) return false
      const activityDate = new Date(activity.horario)
      return activityDate >= startDate && activityDate <= endDate
    })

    // Filtrar por usuário selecionado
    if (selectedUser !== 'all' && selectedUser !== '') {
      const selectedUserId = parseInt(selectedUser)
      if (!isNaN(selectedUserId)) {
        filteredActivities = filteredActivities.filter(activity => 
          activity.usuario_monitorado_id === selectedUserId
        )
      }
    }

    // Filtrar por departamento selecionado
    if (selectedDepartment !== 'all' && selectedDepartment !== '') {
      const selectedDeptId = parseInt(selectedDepartment)
      if (!isNaN(selectedDeptId) && Array.isArray(usuariosMonitorados)) {
        const usuariosDoDept = usuariosMonitorados.filter(u => 
          u && u.departamento_id === selectedDeptId
        )
        const userIds = usuariosDoDept.map(u => u.id).filter(id => id !== undefined)
        if (userIds.length > 0) {
          filteredActivities = filteredActivities.filter(activity => 
            userIds.includes(activity.usuario_monitorado_id)
          )
        }
      }
    }

    // Calcular tempo em cada categoria
    const timeData = {
      productive: 0,
      nonproductive: 0,
      neutral: 0,
      idle: 0
    }

    let totalTime = 0

    filteredActivities.forEach(activity => {
      const duration = activity.duracao || 10 // cada registro representa 10 segundos por padrão
      totalTime += duration

      // Usar a classificação que vem da API
      const produtividade = activity.produtividade || 'neutral'
      if (timeData[produtividade] !== undefined) {
        timeData[produtividade] += duration
      } else {
        // Fallback para classificações antigas
        if (activity.ociosidade >= 600) {
          timeData.idle += duration
        } else {
          timeData.neutral += duration
        }
      }
    })

    const pieData = [
      { name: 'Produtivo', value: timeData.productive, color: COLORS.productive },
      { name: 'Não Produtivo', value: timeData.nonproductive, color: COLORS.nonproductive },
      { name: 'Neutro', value: timeData.neutral, color: COLORS.neutral },
      { name: 'Ocioso', value: timeData.idle, color: COLORS.idle }
    ].filter(item => item.value > 0)

    // Agrupar por dia para timeline
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
        // Fallback
        if (activity.ociosidade >= 600) {
          dailyData[day].idle += duration
        } else {
          dailyData[day].neutral += duration
        }
      }
    })

    const timelineData = Object.values(dailyData).sort((a, b) => a.date.localeCompare(b.date))

    // Estatísticas por usuário
    const userStats = {}
    filteredActivities.forEach(activity => {
      if (!activity || !activity.usuario_monitorado_id) return

      const userId = activity.usuario_monitorado_id
      const userName = activity.usuario_monitorado_nome || 
                      usuariosMonitorados.find(u => u.id === userId)?.nome || 
                      `Usuário ${userId}`

      if (!userStats[userId]) {
        userStats[userId] = {
          nome: userName,
          productive: 0,
          nonproductive: 0,
          neutral: 0,
          idle: 0,
          total: 0
        }
      }

      const duration = Math.max(activity.duracao || 10, 1) // Garantir que duracao seja pelo menos 1
      const produtividade = activity.produtividade || 'neutral'

      userStats[userId].total += duration
      if (userStats[userId][produtividade] !== undefined) {
        userStats[userId][produtividade] += duration
      } else {
        if (activity.ociosidade >= 600) {
          userStats[userId].idle += duration
        } else {
          userStats[userId].neutral += duration
        }
      }
    })

    const recentActivities = filteredActivities.slice().sort((a, b) => new Date(b.horario) - new Date(a.horario));

    return { pieData, timelineData, totalTime, userStats, recentActivities }
  }

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-500"></div>
      </div>
    )
  }

  const { pieData, timelineData, totalTime, userStats, recentActivities } = processActivityData()

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Bem-vindo de volta, {user?.usuario}!
        </p>
      </div>

      {/* Controls */}
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
            className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm min-w-[150px]"
          >
            <option value="all">Todos os usuários</option>
            {Array.isArray(usuariosMonitorados) && usuariosMonitorados
              .filter(usuario => usuario && usuario.id && usuario.nome)
              .map(usuario => (
                <option key={`user-${usuario.id}`} value={usuario.id}>
                  {usuario.nome}
                </option>
              ))
            }
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Departamento:
          </label>
          <select
            value={selectedDepartment}
            onChange={(e) => setSelectedDepartment(e.target.value)}
            className="rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm min-w-[150px]"
          >
            <option value="all">Todos os departamentos</option>
            {Array.isArray(departamentos) && departamentos
              .filter(dept => dept && dept.id && dept.nome)
              .map(dept => (
                <option key={`dept-${dept.id}`} value={dept.id}>
                  {dept.nome}
                </option>
              ))
            }
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Auto-refresh:
          </label>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1 rounded text-sm ${
              autoRefresh
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
            }`}
          >
            {autoRefresh ? 'Ligado' : 'Desligado'}
          </button>
        </div>

        <button
          onClick={fetchData}
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
        >
          Atualizar
        </button>
      </div>

      {/* Stats Cards */}
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
                    {formatTime(pieData.find(d => d.name === 'Produtivo')?.value || 0)}
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
                    {formatTime(pieData.find(d => d.name === 'Não Produtivo')?.value || 0)}
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
                    {formatTime(pieData.find(d => d.name === 'Neutro')?.value || 0)}
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
                    {formatTime(pieData.find(d => d.name === 'Ocioso')?.value || 0)}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Pie Chart */}
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
              Nenhum dado disponível para o período selecionado
            </div>
          )}
        </div>

        {/* Bar Chart */}
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
              Nenhum dado disponível para o período selecionado
            </div>
          )}
        </div>
      </div>

      {/* Timeline Chart */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow mb-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Tendência ao Longo do Tempo
        </h2>
        {timelineData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={timelineData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={(value) => format(new Date(value), 'dd/MM')} />
              <YAxis tickFormatter={formatTime} />
              <Tooltip formatter={(value) => formatTime(value)} />
              <Legend />
              <Line type="monotone" dataKey="productive" stroke={COLORS.productive} name="Produtivo" />
              <Line type="monotone" dataKey="nonproductive" stroke={COLORS.nonproductive} name="Não Produtivo" />
              <Line type="monotone" dataKey="neutral" stroke={COLORS.neutral} name="Neutro" />
              <Line type="monotone" dataKey="idle" stroke={COLORS.idle} name="Ocioso" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[400px] text-gray-500 dark:text-gray-400">
            Nenhum dado disponível para o período selecionado
          </div>
        )}
      </div>

      {/* User Statistics */}
      {Object.keys(userStats).length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
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
                {Object.values(userStats).map((stats, index) => (
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

      {/* Recent Activities - Empty State */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow mt-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Atividades Recentes
        </h2>
        {recentActivities && recentActivities.length > 0 ? (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {recentActivities.slice(0, 5).map((activity) => (
              <li key={activity.id} className="py-4">
                <div className="flex space-x-3">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                        {activity.active_window || 'Atividade sem título'}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {activity.horario ? new Date(activity.horario).toLocaleTimeString() : ''}
                      </p>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Usuário: {activity.usuario_monitorado_nome || 'N/A'} - {activity.categoria || 'Sem categoria'}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-center py-8">
            <div className="text-gray-400 dark:text-gray-500">
              <ChartBarIcon className="mx-auto h-12 w-12 mb-4" />
              <p className="text-sm">Nenhuma atividade encontrada</p>
              <p className="text-xs mt-1">As atividades aparecerão aqui quando o agente começar a enviar dados</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}