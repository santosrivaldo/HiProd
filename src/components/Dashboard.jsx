
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

const COLORS = {
  productive: '#10B981',
  nonproductive: '#EF4444',
  unclassified: '#F59E0B',
  idle: '#6B7280'
}

export default function Dashboard() {
  const { user } = useAuth()
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState(7) // days
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    fetchActivities()
    
    let interval
    if (autoRefresh) {
      interval = setInterval(fetchActivities, 30000) // refresh every 30 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [dateRange, autoRefresh])

  const fetchActivities = async () => {
    try {
      const response = await api.get('/atividades')
      setActivities(response.data || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching activities:', error)
      setActivities([]) // Set empty array on error
      setLoading(false)
    }
  }

  const processActivityData = () => {
    const userActivities = activities.filter(activity => 
      activity.usuario_id === user.usuario_id
    )

    const now = new Date()
    const startDate = startOfDay(subDays(now, dateRange))
    const endDate = endOfDay(now)

    const filteredActivities = userActivities.filter(activity => {
      const activityDate = new Date(activity.horario)
      return activityDate >= startDate && activityDate <= endDate
    })

    // Calculate time spent in each category
    const timeData = {
      productive: 0,
      nonproductive: 0,
      unclassified: 0,
      idle: 0
    }

    let totalTime = 0

    filteredActivities.forEach(activity => {
      const duration = 10 // each record represents 10 seconds
      totalTime += duration
      
      if (activity.ociosidade >= 600) { // 10 minutes or more = idle
        timeData.idle += duration
      } else {
        // For now, classify as unclassified since we don't have classification in the API yet
        timeData.unclassified += duration
      }
    })

    const pieData = [
      { name: 'Produtivo', value: timeData.productive, color: COLORS.productive },
      { name: 'Não Produtivo', value: timeData.nonproductive, color: COLORS.nonproductive },
      { name: 'Não Classificado', value: timeData.unclassified, color: COLORS.unclassified },
      { name: 'Ocioso', value: timeData.idle, color: COLORS.idle }
    ].filter(item => item.value > 0)

    // Group by day for timeline
    const dailyData = {}
    filteredActivities.forEach(activity => {
      const day = format(new Date(activity.horario), 'yyyy-MM-dd')
      if (!dailyData[day]) {
        dailyData[day] = { date: day, productive: 0, nonproductive: 0, unclassified: 0, idle: 0 }
      }
      
      const duration = 10
      if (activity.ociosidade >= 600) {
        dailyData[day].idle += duration
      } else {
        dailyData[day].unclassified += duration
      }
    })

    const timelineData = Object.values(dailyData).sort((a, b) => a.date.localeCompare(b.date))

    return { pieData, timelineData, totalTime }
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

  const { pieData, timelineData, totalTime } = processActivityData()

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
          onClick={fetchActivities}
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
                    Não Classificado
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatTime(pieData.find(d => d.name === 'Não Classificado')?.value || 0)}
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

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Pie Chart */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Distribuição de Tempo
          </h2>
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
        </div>

        {/* Bar Chart */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Atividade por Dia
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={timelineData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={(value) => format(new Date(value), 'dd/MM')} />
              <YAxis tickFormatter={formatTime} />
              <Tooltip formatter={(value) => formatTime(value)} />
              <Legend />
              <Bar dataKey="productive" stackId="a" fill={COLORS.productive} name="Produtivo" />
              <Bar dataKey="nonproductive" stackId="a" fill={COLORS.nonproductive} name="Não Produtivo" />
              <Bar dataKey="unclassified" stackId="a" fill={COLORS.unclassified} name="Não Classificado" />
              <Bar dataKey="idle" stackId="a" fill={COLORS.idle} name="Ocioso" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Timeline Chart */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Tendência ao Longo do Tempo
        </h2>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={timelineData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={(value) => format(new Date(value), 'dd/MM')} />
            <YAxis tickFormatter={formatTime} />
            <Tooltip formatter={(value) => formatTime(value)} />
            <Legend />
            <Line type="monotone" dataKey="productive" stroke={COLORS.productive} name="Produtivo" />
            <Line type="monotone" dataKey="nonproductive" stroke={COLORS.nonproductive} name="Não Produtivo" />
            <Line type="monotone" dataKey="unclassified" stroke={COLORS.unclassified} name="Não Classificado" />
            <Line type="monotone" dataKey="idle" stroke={COLORS.idle} name="Ocioso" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
