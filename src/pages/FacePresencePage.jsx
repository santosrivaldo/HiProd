import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import { format, subDays, startOfDay, endOfDay, parseISO } from 'date-fns'
import {
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
  ClockIcon,
  UserIcon,
  CalendarDaysIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'

export default function FacePresencePage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState([])
  const [dateRange, setDateRange] = useState(7)
  const [selectedUser, setSelectedUser] = useState('all')
  const [groupBy, setGroupBy] = useState('day')
  const [users, setUsers] = useState([])
  const [summary, setSummary] = useState({
    totalHoras: 0,
    totalUsuarios: 0,
    mediaHoras: 0,
    totalVerificacoes: 0
  })

  const formatTime = (seconds) => {
    if (!seconds || seconds === 0) return '0min'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours === 0) return `${minutes}min`
    if (minutes === 0) return `${hours}h`
    return `${hours}h ${minutes}min`
  }

  const formatMinutes = (minutes) => {
    if (!minutes || minutes === 0) return '0min'
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours === 0) return `${mins}min`
    if (mins === 0) return `${hours}h`
    return `${hours}h ${mins}min`
  }

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Calcular datas
      const now = new Date()
      const startDate = format(startOfDay(subDays(now, dateRange)), 'yyyy-MM-dd')
      const endDate = format(endOfDay(now), 'yyyy-MM-dd')

      // Carregar usuários
      const usersRes = await api.get('/usuarios-monitorados')
      const usersList = Array.isArray(usersRes.data) ? usersRes.data : []
      setUsers(usersList)

      // Carregar estatísticas de presença facial
      let url = `/face-presence-stats?group_by=${groupBy}&start_date=${startDate}&end_date=${endDate}`
      if (selectedUser !== 'all') {
        url += `&usuario_monitorado_id=${selectedUser}`
      }

      const statsRes = await api.get(url)
      const statsData = Array.isArray(statsRes.data) ? statsRes.data : []
      setStats(statsData)

      // Calcular resumo (horas_presente na verdade são minutos)
      const totalMinutos = statsData.reduce((sum, stat) => sum + (stat.horas_presente || 0), 0)
      const totalVerificacoes = statsData.reduce((sum, stat) => sum + (stat.total_verificacoes || 0), 0)
      const usuariosUnicos = new Set(statsData.map(s => s.usuario_id)).size

      setSummary({
        totalHoras: totalMinutos, // Na verdade são minutos
        totalUsuarios: usuariosUnicos || usersList.length,
        mediaHoras: usuariosUnicos > 0 ? totalMinutos / usuariosUnicos : 0, // Na verdade são minutos
        totalVerificacoes: totalVerificacoes
      })

    } catch (err) {
      console.error('❌ Erro ao carregar dados de presença facial:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Erro ao carregar dados'
      setError(errorMessage)
      setStats([])
      
      // Se for erro 404 ou tabela não existe, mostrar mensagem específica
      if (err.response?.status === 404 || errorMessage.includes('does not exist')) {
        setError('Tabela de verificação facial ainda não foi criada. Aguarde alguns minutos após o primeiro envio de dados.')
      }
    } finally {
      setLoading(false)
    }
  }, [dateRange, selectedUser, groupBy])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Preparar dados para gráficos
  const chartData = stats.map(stat => {
    const dataKey = groupBy === 'day' ? 'data' : groupBy === 'hour' ? 'hora' : 'semana'
    return {
      periodo: groupBy === 'day' 
        ? format(parseISO(stat.data), 'dd/MM')
        : groupBy === 'hour'
        ? `${stat.hora}:00`
        : format(parseISO(stat.semana), 'dd/MM'),
      usuario: stat.usuario_nome,
      minutos: stat.horas_presente || 0,  // Na verdade são minutos
      deteccoes: stat.deteccoes || 0,
      ausencias: stat.ausencias || 0,
      taxaPresenca: stat.total_verificacoes > 0 
        ? ((stat.deteccoes / stat.total_verificacoes) * 100).toFixed(1)
        : 0
    }
  })

  // Agrupar por período para gráfico
  const groupedByPeriod = {}
  chartData.forEach(item => {
    if (!groupedByPeriod[item.periodo]) {
      groupedByPeriod[item.periodo] = {
        periodo: item.periodo,
        totalHoras: 0,
        totalDeteccoes: 0,
        totalAusencias: 0,
        usuarios: new Set()
      }
    }
    groupedByPeriod[item.periodo].totalHoras += item.horas
    groupedByPeriod[item.periodo].totalDeteccoes += item.deteccoes
    groupedByPeriod[item.periodo].totalAusencias += item.ausencias
    groupedByPeriod[item.periodo].usuarios.add(item.usuario)
  })

  const chartDataGrouped = Object.values(groupedByPeriod).map(item => ({
    ...item,
    usuarios: item.usuarios.size
  })).sort((a, b) => a.periodo.localeCompare(b.periodo))

  if (loading) {
    return <LoadingSpinner size="xl" text="Carregando dados de presença facial..." fullScreen />
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 className="text-lg font-medium text-red-800 dark:text-red-200 mb-2">Erro ao carregar dados</h3>
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
              <UserIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Presença Facial - Horas em Frente ao PC
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Relatório detalhado de tempo detectado em frente ao computador
              </p>
            </div>
          </div>
        </div>

        {/* Filtros */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Período:</label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(parseInt(e.target.value))}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value={1}>Último dia</option>
              <option value={7}>Últimos 7 dias</option>
              <option value={30}>Últimos 30 dias</option>
              <option value={90}>Últimos 90 dias</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Usuário:</label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value="all">Todos</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>{user.nome}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Agrupar por:</label>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value="day">Dia</option>
              <option value="hour">Hora</option>
              <option value="week">Semana</option>
            </select>
          </div>
        </div>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                <ClockIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total de Minutos</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatMinutes(summary.totalHoras)}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <UserIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Usuários Monitorados</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.totalUsuarios}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Média por Usuário</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {formatMinutes(summary.mediaHoras)}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
                <CalendarDaysIcon className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Verificações</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {summary.totalVerificacoes.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Gráfico */}
      {chartDataGrouped.length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
            Minutos de Presença por Período
          </h2>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={chartDataGrouped}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="periodo" 
                stroke="#6B7280"
                tick={{ fill: '#6B7280' }}
              />
              <YAxis 
                stroke="#6B7280"
                tick={{ fill: '#6B7280' }}
                tickFormatter={(value) => `${value}h`}
              />
              <Tooltip 
                formatter={(value) => `${formatMinutes(value)}`}
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="totalHoras" 
                stroke="#8B5CF6" 
                fill="#8B5CF6" 
                fillOpacity={0.3}
                name="Minutos de Presença"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tabela Detalhada */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
          Detalhamento por Usuário
        </h2>
        {stats.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {groupBy === 'day' ? 'Data' : groupBy === 'hour' ? 'Hora' : 'Semana'}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Usuário
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Minutos Presente
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Detecções
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Ausências
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Taxa de Presença
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {stats
                  .sort((a, b) => {
                    const dateA = groupBy === 'day' ? a.data : groupBy === 'hour' ? `${a.data}-${a.hora}` : a.semana
                    const dateB = groupBy === 'day' ? b.data : groupBy === 'hour' ? `${b.data}-${b.hora}` : b.semana
                    return dateB.localeCompare(dateA)
                  })
                  .map((stat, index) => {
                    const periodo = groupBy === 'day' 
                      ? format(parseISO(stat.data), 'dd/MM/yyyy')
                      : groupBy === 'hour'
                      ? `${format(parseISO(stat.data), 'dd/MM')} ${stat.hora}:00`
                      : format(parseISO(stat.semana), 'dd/MM/yyyy')
                    
                    const taxaPresenca = stat.total_verificacoes > 0
                      ? ((stat.deteccoes / stat.total_verificacoes) * 100).toFixed(1)
                      : '0.0'

                    return (
                      <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                          {periodo}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                          {stat.usuario_nome || `Usuário ${stat.usuario_id}`}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white font-semibold">
                          {formatMinutes(stat.horas_presente || 0)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600 dark:text-green-400">
                          {stat.deteccoes || 0}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600 dark:text-red-400">
                          {stat.ausencias || 0}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            parseFloat(taxaPresenca) >= 80
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                              : parseFloat(taxaPresenca) >= 50
                              ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                              : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                          }`}>
                            {taxaPresenca}%
                          </span>
                        </td>
                      </tr>
                    )
                  })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <UserIcon className="mx-auto h-16 w-16 mb-4 text-gray-400" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Nenhum dado de presença disponível
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Ajuste os filtros ou aguarde novos dados de verificação facial
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

