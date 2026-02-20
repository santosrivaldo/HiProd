import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import api from '../services/api'
import {
  parseBrasiliaDate,
  formatBrasiliaDate,
  startOfDayBrasilia,
  endOfDayBrasilia,
  getTodayIsoDate,
  subDaysBrasilia,
  formatBrasiliaTimeHHMM
} from '../utils/timezoneUtils'
import CircularProgress from '../components/dashboard/CircularProgress'
import AdvancedChart from '../components/charts/AdvancedChart'
import LoadingSpinner from '../components/LoadingSpinner'
import ScreenTimelinePlayer from '../components/ScreenTimelinePlayer'
import {
  ArrowPathIcon,
  FilmIcon,
  ChevronLeftIcon,
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  PlayIcon,
  ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline'

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

const formatTime = (seconds) => {
  if (!seconds || seconds === 0) return '0s'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const parts = []
  if (h > 0) parts.push(`${h}h`)
  if (m > 0) parts.push(`${m}m`)
  if (s > 0 || parts.length === 0) parts.push(`${s}s`)
  return parts.join(' ')
}

/** Paleta semântica para gráficos e status (harmonizada e acessível) */
const CHART_PALETTE = {
  productive: '#059669',   // green-600 – útil / produtivo
  nonproductive: '#dc2626', // red-600 – não útil / improdutivo
  neutral: '#b45309',       // amber-700 – indefinido
  idle: '#64748b',         // slate-500 – ocioso
  active: '#2563eb'        // blue-600 – ativo
}

export default function UserDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [activities, setActivities] = useState([])
  const [activitiesWeek, setActivitiesWeek] = useState([])
  const [activitiesMonth, setActivitiesMonth] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingActivities, setLoadingActivities] = useState(true)
  const [error, setError] = useState(null)

  // Dia: 'yesterday' | 'today' | 'custom'; Data: yyyy-MM-dd
  const [diaPreset, setDiaPreset] = useState('today')
  const [selectedDate, setSelectedDate] = useState(getTodayIsoDate())

  useEffect(() => {
    const today = getTodayIsoDate()
    if (diaPreset === 'today') setSelectedDate(today)
    else if (diaPreset === 'yesterday') setSelectedDate(subDaysBrasilia(today, 1))
  }, [diaPreset])

  const loadUser = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/usuarios-monitorados')
      const list = Array.isArray(res.data) ? res.data : []
      const found = list.find((u) => String(u.id) === String(id))
      if (found) setUser(found)
      else setError('Usuário não encontrado.')
    } catch (e) {
      console.error(e)
      setError('Erro ao carregar usuário.')
    } finally {
      setLoading(false)
    }
  }, [id])

  const loadActivities = useCallback(async () => {
    if (!id) return
    setLoadingActivities(true)
    try {
      const dayStart = startOfDayBrasilia(selectedDate)
      const dayEnd = endOfDayBrasilia(selectedDate)
      const weekStart = startOfDayBrasilia(subDaysBrasilia(selectedDate, 7))
      const monthStart = startOfDayBrasilia(subDaysBrasilia(selectedDate, 30))

      const [dayRes, weekRes, monthRes] = await Promise.all([
        api.get(
          `/atividades?usuario_monitorado_id=${id}&data_inicio=${dayStart.toISOString()}&data_fim=${dayEnd.toISOString()}&agrupar=true&limite=500`
        ),
        api.get(
          `/atividades?usuario_monitorado_id=${id}&data_inicio=${weekStart.toISOString()}&data_fim=${dayEnd.toISOString()}&agrupar=true&limite=2000`
        ),
        api.get(
          `/atividades?usuario_monitorado_id=${id}&data_inicio=${monthStart.toISOString()}&data_fim=${dayEnd.toISOString()}&agrupar=true&limite=5000`
        )
      ])

      const dayList = Array.isArray(dayRes.data) ? dayRes.data : []
      const weekList = Array.isArray(weekRes.data) ? weekRes.data : []
      const monthList = Array.isArray(monthRes.data) ? monthRes.data : []

      setActivities(dayList)
      setActivitiesWeek(weekList)
      setActivitiesMonth(monthList)
    } catch (e) {
      console.error(e)
      setActivities([])
      setActivitiesWeek([])
      setActivitiesMonth([])
    } finally {
      setLoadingActivities(false)
    }
  }, [id, selectedDate])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    loadActivities()
  }, [loadActivities])

  const safeParseDate = (dateString) => {
    if (!dateString) return null
    try {
      const d = new Date(dateString)
      return !isNaN(d.getTime()) ? d : null
    } catch {
      return null
    }
  }

  const daySummary = React.useMemo(() => {
    let productive = 0,
      nonproductive = 0,
      neutral = 0,
      idle = 0
    activities.forEach((a) => {
      const dur = getActivityDurationSeconds(a)
      if (dur <= 0) return
      const prod = (a.produtividade || 'neutral').toLowerCase()
      const ocioso = a.ociosidade >= 600
      if (prod === 'productive') productive += dur
      else if (prod === 'nonproductive') nonproductive += dur
      else if (ocioso) idle += dur
      else neutral += dur
    })
    const total = productive + nonproductive + neutral + idle
    return { productive, nonproductive, neutral, idle, total }
  }, [activities])

  const workingDaysWeek = React.useMemo(() => {
    const days = new Set()
    activitiesWeek.forEach((a) => {
      const d = safeParseDate(a.horario || a.primeiro_horario)
      if (d) days.add(formatBrasiliaDate(d, 'isoDate'))
    })
    return days.size
  }, [activitiesWeek])

  const workingDaysMonth = React.useMemo(() => {
    const days = new Set()
    activitiesMonth.forEach((a) => {
      const d = safeParseDate(a.horario || a.primeiro_horario)
      if (d) days.add(formatBrasiliaDate(d, 'isoDate'))
    })
    return days.size
  }, [activitiesMonth])

  const horasTrabalhoDia = 8
  const cargaHorariaSelecionada = 1 * horasTrabalhoDia * 3600
  const horarioTrabalho = user
    ? `${(user.horario_inicio_trabalho || '09:00').slice(0, 5)}-${(user.horario_fim_trabalho || '18:00').slice(0, 5)} (Almoço: 12h-13h)`
    : '09h-18h (Almoço: 12h-13h)'

  const custoColaboradorDia = 166.67
  const totalProd = daySummary.total
  const custoProdutivo =
    totalProd > 0 ? (daySummary.productive / totalProd) * custoColaboradorDia : 0
  const custoImprodutivo =
    totalProd > 0 ? (daySummary.nonproductive / totalProd) * custoColaboradorDia : 0
  const custoIndefinido =
    totalProd > 0
      ? ((daySummary.neutral + daySummary.idle) / totalProd) * custoColaboradorDia
      : 0

  const pctProdutivo =
    daySummary.total > 0
      ? (daySummary.productive / daySummary.total) * 100
      : 0
  const horasImprodutivasOuIndefinidas =
    daySummary.nonproductive + daySummary.neutral + daySummary.idle

  const pieTempoAtividade = [
    {
      name: 'Ativo',
      value: daySummary.productive + daySummary.nonproductive + daySummary.neutral,
      color: CHART_PALETTE.active
    },
    { name: 'Ocioso', value: daySummary.idle, color: CHART_PALETTE.idle }
  ].filter((d) => d.value > 0)

  const pieTarefasProdutivas = [
    { name: 'Útil', value: daySummary.productive, color: CHART_PALETTE.productive },
    { name: 'Não útil', value: daySummary.nonproductive, color: CHART_PALETTE.nonproductive },
    { name: 'Indefinido', value: daySummary.neutral + daySummary.idle, color: CHART_PALETTE.neutral }
  ].filter((d) => d.value > 0)

  const pieCusto = [
    { name: 'Custo produtivo', value: Math.round(custoProdutivo * 100) / 100, color: CHART_PALETTE.productive },
    { name: 'Custo improdutivo', value: Math.round(custoImprodutivo * 100) / 100, color: CHART_PALETTE.nonproductive },
    { name: 'Custo indefinido', value: Math.round(custoIndefinido * 100) / 100, color: CHART_PALETTE.neutral }
  ].filter((d) => d.value > 0)

  const applicationList = React.useMemo(() => {
    const list = activities
      .filter((a) => getActivityDurationSeconds(a) > 0)
      .map((a) => {
        const horario = a.horario || a.primeiro_horario
        const dt = typeof horario === 'string' ? horario : horario?.isoformat?.() || ''
        const ultimo = a.ultimo_horario
        const dtFim = typeof ultimo === 'string' ? ultimo : ultimo?.isoformat?.() || ''
        return {
          id: a.id,
          application: a.application || a.active_window?.split(' - ')[0] || 'Aplicação',
          process: a.active_window || a.titulo_janela || '—',
          duration: getActivityDurationSeconds(a),
          horario: dt,
          horarioFim: dtFim,
          produtividade: a.produtividade || 'neutral',
          ocioso: (a.ociosidade || 0) >= 600
        }
      })
      .sort((a, b) => (a.horario || '').localeCompare(b.horario || ''))
    return list
  }, [activities])

  const applicationsGrouped = React.useMemo(() => {
    const byApp = new Map()
    applicationList.forEach((item) => {
      const appName = item.application?.trim() || 'Não listado'
      if (!byApp.has(appName)) {
        byApp.set(appName, {
          appName,
          situacao: item.produtividade,
          tempoAtivo: 0,
          tempoOcioso: 0,
          processos: []
        })
      }
      const g = byApp.get(appName)
      if (item.ocioso) g.tempoOcioso += item.duration
      else g.tempoAtivo += item.duration
      g.processos.push({
        id: item.id,
        process: item.application?.split(/[\s-]/)[0] || 'processo',
        descricao: item.process,
        inicio: item.horario,
        fim: item.horarioFim,
        duracao: item.duration,
        horario: item.horario,
        data: item.horario ? formatBrasiliaDate(item.horario, 'date') : '—'
      })
    })
    return Array.from(byApp.values()).sort((a, b) => (b.tempoAtivo + b.tempoOcioso) - (a.tempoAtivo + a.tempoOcioso))
  }, [applicationList])

  const [expandedApp, setExpandedApp] = useState(null)
  const [inlineTimelineAt, setInlineTimelineAt] = useState(null)
  const [showInlineTimeline, setShowInlineTimeline] = useState(false)
  const [timelineFilterStartTime, setTimelineFilterStartTime] = useState('00:00')
  const [timelineFilterEndTime, setTimelineFilterEndTime] = useState('23:59')
  const [keylogPreview, setKeylogPreview] = useState([])

  const timelineUrl = `/timeline?userId=${id}&date=${selectedDate}`
  const timelineSearch = `?userId=${id}&date=${selectedDate}`
  const timelineUrlAt = (atIso) =>
    atIso
      ? `/timeline?userId=${id}&date=${selectedDate}&at=${encodeURIComponent(atIso)}`
      : timelineUrl

  useEffect(() => {
    if (!id || !inlineTimelineAt) {
      setKeylogPreview([])
      return
    }
    let cancelled = false
    api.get(`/keylog/search?usuario_monitorado_id=${id}&at=${encodeURIComponent(inlineTimelineAt)}&window_seconds=60&limit=50`)
      .then((res) => {
        if (!cancelled) setKeylogPreview(res.data?.results ?? [])
      })
      .catch(() => { if (!cancelled) setKeylogPreview([]) })
    return () => { cancelled = true }
  }, [id, inlineTimelineAt])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text="Carregando usuário..." />
      </div>
    )
  }

  if (error || !user) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 p-4">
          {error || 'Usuário não encontrado.'}
        </div>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 inline-flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          <ChevronLeftIcon className="w-5 h-5" /> Voltar
        </button>
      </div>
    )
  }

  const departamentoNome =
    user.departamento?.nome || user.departamento_nome || '—'

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 pb-24">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
          title="Voltar"
        >
          <ChevronLeftIcon className="w-6 h-6" />
        </button>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Detalhes do usuário
        </h1>
      </div>

      {/* Perfil: avatar + dados em grid */}
      <section className="glass-card p-6">
        <div className="flex flex-col sm:flex-row gap-6">
          <div className="flex-shrink-0">
            <div className="w-24 h-24 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-3xl font-bold text-indigo-700 dark:text-indigo-300">
              {(user.nome || 'U').slice(0, 2).toUpperCase()}
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">ID</label>
              <div className="mt-0.5 px-3 py-2 rounded-lg bg-indigo-50/50 dark:bg-indigo-900/20 text-gray-900 dark:text-white text-sm font-mono">
                {user.id}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Nome</label>
              <div className="mt-0.5 px-3 py-2 rounded-lg bg-indigo-50/50 dark:bg-indigo-900/20 text-gray-900 dark:text-white text-sm">
                {user.nome}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">E-mail</label>
              <div className="mt-0.5 px-3 py-2 rounded-lg bg-indigo-50/50 dark:bg-indigo-900/20 text-gray-500 dark:text-gray-400 text-sm">
                —
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Telefone</label>
              <div className="mt-0.5 px-3 py-2 rounded-lg bg-indigo-50/50 dark:bg-indigo-900/20 text-gray-500 dark:text-gray-400 text-sm">
                —
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Custo</label>
              <div className="mt-0.5 px-3 py-2 rounded-lg bg-indigo-50/50 dark:bg-indigo-900/20 text-gray-900 dark:text-white text-sm">
                BRL 3.500,00
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Departamento</label>
              <div className="mt-0.5 px-3 py-2 rounded-lg bg-indigo-50/50 dark:bg-indigo-900/20 text-gray-900 dark:text-white text-sm">
                {departamentoNome}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Filtro de data + Reconsolidar */}
      <section className="glass-card p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Dia</label>
            <select
              value={diaPreset}
              onChange={(e) => setDiaPreset(e.target.value)}
              className="glass-input text-gray-900 dark:text-white px-3 py-2"
            >
              <option value="yesterday">Ontem</option>
              <option value="today">Hoje</option>
              <option value="custom">Outro</option>
            </select>
          </div>
          {diaPreset === 'custom' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Data</label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="glass-input text-gray-900 dark:text-white px-3 py-2"
              />
            </div>
          )}
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Data: {formatBrasiliaDate(selectedDate + 'T12:00:00-03:00', 'date')}
          </div>
          <button
            onClick={loadActivities}
            disabled={loadingActivities}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <ArrowPathIcon className="w-5 h-5" />
            Reconsolidar
          </button>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Última consolidação: —
        </p>
      </section>

      {/* Preview / Timeline de telas */}
      <section className="glass-card p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
          <FilmIcon className="w-5 h-5" />
          Timeline de telas
        </h2>
        {!showInlineTimeline && !inlineTimelineAt && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Não há preview carregado. Selecione um período ou abra a timeline para ver os frames.
          </p>
        )}
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            type="button"
            onClick={() => {
              setShowInlineTimeline(true)
              setInlineTimelineAt(null)
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-indigo-600 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
          >
            <FilmIcon className="w-5 h-5" />
            Abrir timeline de telas
          </button>
          <button
            type="button"
            onClick={() => {
              const params = new URLSearchParams({
                userId: id,
                date: selectedDate,
                filterStartTime: timelineFilterStartTime,
                filterEndTime: timelineFilterEndTime,
              })
              if (inlineTimelineAt) params.set('at', inlineTimelineAt)
              const base = window.location.pathname.replace(/\/users\/.*$/, '') || '/'
              window.open(`${window.location.origin}${base}/preview?${params.toString()}`, '_blank', 'noopener,noreferrer')
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-600 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/20"
            title="Abre o preview em nova guia com seletor de tela, zoom e exportar imagem"
          >
            <ArrowTopRightOnSquareIcon className="w-5 h-5" />
            Abrir preview em nova guia
          </button>
          <button
            type="button"
            onClick={() => {
              setShowInlineTimeline(true)
              setInlineTimelineAt(null)
            }}
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
          >
            Primeiros 5 minutos
          </button>
          <button
            type="button"
            onClick={() => {
              setShowInlineTimeline(true)
              setInlineTimelineAt(null)
            }}
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
          >
            Últimos 5 minutos
          </button>
        </div>
        <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-3 text-sm text-blue-800 dark:text-blue-200">
          OBS: O tamanho do período pode variar conforme a atividade no período selecionado.
        </div>
        {showInlineTimeline && (
          <div className="mt-4 space-y-4">
            <div className="flex flex-wrap items-end gap-4 p-3 rounded-xl bg-gray-100 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filtro do preview:</span>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Data (dia)</label>
                <span className="text-sm text-gray-700 dark:text-gray-200">{selectedDate}</span>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Altere o dia no seletor acima na página.</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Horário (início)</label>
                <input
                  type="time"
                  value={timelineFilterStartTime}
                  onChange={(e) => setTimelineFilterStartTime(e.target.value)}
                  className="glass-input text-gray-900 dark:text-white px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Horário (fim)</label>
                <input
                  type="time"
                  value={timelineFilterEndTime}
                  onChange={(e) => setTimelineFilterEndTime(e.target.value)}
                  className="glass-input text-gray-900 dark:text-white px-2 py-1.5 text-sm"
                />
              </div>
            </div>
            <ScreenTimelinePlayer
              userId={id}
              date={selectedDate}
              initialAt={inlineTimelineAt}
              filterStartTime={timelineFilterStartTime}
              filterEndTime={timelineFilterEndTime}
              onClose={() => {
                setShowInlineTimeline(false)
                setInlineTimelineAt(null)
                setKeylogPreview([])
              }}
              compact
            />
            {inlineTimelineAt && (
              <div className="mt-4 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                  Texto digitado neste minuto (30s antes e depois da tarefa)
                </h3>
                {keylogPreview.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum keylog neste intervalo.</p>
                ) : (
                  <ul className="space-y-2 max-h-40 overflow-y-auto">
                    {keylogPreview.map((k) => (
                      <li key={k.id} className="text-sm border-b border-gray-200/50 dark:border-gray-700/50 pb-2 last:border-0">
                        <span className="text-gray-500 dark:text-gray-400">{formatBrasiliaDate(k.captured_at, 'time')}</span>
                        {k.window_title && (
                          <span className="ml-2 text-gray-400 dark:text-gray-500 truncate max-w-xs inline-block align-bottom" title={k.window_title}>
                            — {k.window_title}
                          </span>
                        )}
                        <p className="mt-0.5 text-gray-700 dark:text-gray-300 break-words">{k.text_content || '—'}</p>
                      </li>
                    ))}
                  </ul>
                )}
                <Link
                  to={timelineUrlAt(inlineTimelineAt)}
                  className="inline-flex items-center gap-1 mt-3 text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                >
                  <FilmIcon className="w-4 h-4" /> Abrir timeline completa neste momento
                </Link>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Aplicações e processos utilizados (expandível por aplicação) */}
      <section className="glass-card overflow-hidden">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white p-4 border-b border-gray-200 dark:border-gray-700">
          Aplicações e processos utilizados
        </h2>
        {loadingActivities ? (
          <div className="p-6"><LoadingSpinner size="md" /></div>
        ) : applicationsGrouped.length === 0 ? (
          <p className="p-6 text-sm text-gray-500 dark:text-gray-400">Nenhuma atividade no dia selecionado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  <th className="w-10 px-2 py-3" />
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Métrica</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Situação</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo ativo</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tempo ocioso</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Qtd. objetos</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Mouse</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Teclado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {applicationsGrouped.map((app) => {
                  const isExpanded = expandedApp === app.appName
                  const situacaoLabel = app.situacao === 'productive' ? 'Útil' : app.situacao === 'nonproductive' ? 'Não útil' : 'Indefinido'
                  const situacaoClass = app.situacao === 'productive' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : app.situacao === 'nonproductive' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                  return (
                    <React.Fragment key={app.appName}>
                      <tr className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-2 py-2">
                          <button
                            type="button"
                            onClick={() => setExpandedApp(isExpanded ? null : app.appName)}
                            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-500"
                            aria-label={isExpanded ? 'Recolher' : 'Expandir'}
                          >
                            {isExpanded ? <ChevronUpIcon className="w-5 h-5" /> : <ChevronDownIcon className="w-5 h-5" />}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                          <Link
                            to={timelineUrlAt(app.processos[0]?.horario)}
                            className="text-indigo-600 dark:text-indigo-400 hover:underline"
                            title="Abrir página de timeline neste aplicativo"
                          >
                            {app.appName}
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${situacaoClass}`}>{situacaoLabel}</span>
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-green-700 dark:text-green-300">{formatTime(app.tempoAtivo)}</td>
                        <td className="px-4 py-3 text-sm text-right text-red-700 dark:text-red-300">{formatTime(app.tempoOcioso)}</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-500 dark:text-gray-400">—</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-500 dark:text-gray-400">—</td>
                        <td className="px-4 py-3 text-sm text-right text-gray-500 dark:text-gray-400">—</td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={8} className="px-4 py-4 bg-gray-50/50 dark:bg-gray-900/30">
                            <div className="mb-3 flex flex-wrap items-center gap-4 text-sm">
                              <span className="text-gray-600 dark:text-gray-400"><span className="font-medium text-gray-700 dark:text-gray-300">Tempo acumulado:</span> {formatTime(app.tempoAtivo + app.tempoOcioso)}</span>
                              <span className="text-gray-600 dark:text-gray-400"><span className="font-medium text-gray-700 dark:text-gray-300">Objetos acessados:</span> —</span>
                            </div>
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                              <thead className="bg-gray-100 dark:bg-gray-700/50">
                                <tr>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">#</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Processo</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Descrição</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Início / Fim</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Data</th>
                                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400">Ações</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                                {app.processos.map((proc, idx) => {
                                  let inicioStr = '—'
                                  let fimStr = '—'
                                  if (proc.inicio) inicioStr = formatBrasiliaDate(proc.inicio, 'time')
                                  if (proc.fim) fimStr = formatBrasiliaDate(proc.fim, 'time')
                                  const inicioFim = proc.inicio ? `${inicioStr} - ${fimStr} (${formatTime(proc.duracao)})` : '—'
                                  return (
                                    <tr key={`${proc.id}-${idx}`} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                      <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">{idx + 1}</td>
                                      <td className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-white">{proc.process}</td>
                                      <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-300 max-w-xs truncate" title={proc.descricao}>{proc.descricao}</td>
                                      <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">{inicioFim}</td>
                                      <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">{proc.data}</td>
                                      <td className="px-3 py-2 text-center">
                                        <div className="inline-flex items-center gap-1">
                                          <button
                                            type="button"
                                            onClick={() => {
                                              setInlineTimelineAt(proc.horario)
                                              setShowInlineTimeline(true)
                                              const atDate = parseBrasiliaDate(proc.horario)
                                              if (atDate) {
                                                const startDate = new Date(atDate.getTime() - 30 * 1000)
                                                const endDate = new Date(atDate.getTime() + 30 * 1000)
                                                setTimelineFilterStartTime(formatBrasiliaTimeHHMM(startDate))
                                                setTimelineFilterEndTime(formatBrasiliaTimeHHMM(endDate))
                                              }
                                            }}
                                            className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-200 dark:hover:bg-indigo-800"
                                            title="Ver momento na timeline (nesta página)"
                                          >
                                            <PlayIcon className="w-5 h-5" />
                                          </button>
                                          <Link
                                            to={timelineUrlAt(proc.horario)}
                                            className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                                            title="Abrir página da timeline de telas neste momento"
                                          >
                                            <FilmIcon className="w-4 h-4" /> Abrir
                                          </Link>
                                        </div>
                                      </td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Resumo do dia selecionado */}
      <section className="bg-gradient-to-r from-indigo-600/10 to-purple-600/10 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl border border-indigo-200/50 dark:border-indigo-800/50 p-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Resumo do dia selecionado
        </h2>
        {loadingActivities ? (
          <LoadingSpinner size="md" />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            <SummaryCard label="Dias trabalhados na semana" value={`${workingDaysWeek} dias`} />
            <SummaryCard label="Dias trabalhados no mês" value={`${workingDaysMonth} dias (${workingDaysMonth * 8} horas)`} />
            <SummaryCard label="Dias selecionados" value="1 dia" />
            <SummaryCard label="Carga horária selecionada" value="8h" />
            <SummaryCard label="Horário de Trabalho" value={horarioTrabalho} />
            <SummaryCard
              label="Horas produtivas"
              value={formatTime(daySummary.productive)}
              valueClassName="text-green-700 dark:text-green-300"
            />
            <SummaryCard
              label="Horas improdutivas"
              value={formatTime(daySummary.nonproductive)}
              valueClassName="text-red-700 dark:text-red-300 bg-red-50/50 dark:bg-red-900/10 px-2 py-1 rounded"
            />
            <SummaryCard label="Custo do colaborador no dia" value={`${custoColaboradorDia.toFixed(2)} BRL`} />
            <SummaryCard
              label={`Custo produtivo (${formatTime(daySummary.productive)})`}
              value={`${custoProdutivo.toFixed(2)} BRL`}
            />
            <SummaryCard
              label={`Custo improdutivo (${formatTime(daySummary.nonproductive)})`}
              value={`${custoImprodutivo.toFixed(2)} BRL`}
              valueClassName="text-red-700 dark:text-red-300 bg-red-50/50 dark:bg-red-900/10 px-2 py-1 rounded"
            />
            <SummaryCard
              label={`Custo indefinido (${formatTime(daySummary.neutral + daySummary.idle)})`}
              value={`${custoIndefinido.toFixed(2)} BRL`}
              withInfo
            />
          </div>
        )}
      </section>

      {/* Gráficos: donuts + Produtividade consolidada */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ChartCard title="Tempo em atividade" minHeight={220}>
              {pieTempoAtividade.length > 0 ? (
                <AdvancedChart
                  type="pie"
                  data={pieTempoAtividade}
                  dataKey="value"
                  height={200}
                  colors={pieTempoAtividade.map((d) => d.color)}
                  noWrapper
                />
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400 py-8">Sem dados</p>
              )}
            </ChartCard>
            <ChartCard title="Tempo em tarefas produtivas" minHeight={220}>
              {pieTarefasProdutivas.length > 0 ? (
                <AdvancedChart
                  type="pie"
                  data={pieTarefasProdutivas}
                  dataKey="value"
                  height={200}
                  colors={pieTarefasProdutivas.map((d) => d.color)}
                  noWrapper
                />
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400 py-8">Sem dados</p>
              )}
            </ChartCard>
          </div>
          <ChartCard title="Custo" minHeight={240}>
            {pieCusto.length > 0 ? (
              <AdvancedChart
                type="pie"
                data={pieCusto}
                dataKey="value"
                height={220}
                colors={pieCusto.map((d) => d.color)}
                noWrapper
              />
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400 py-8">Sem dados</p>
            )}
          </ChartCard>
        </div>
        <div className="flex flex-col">
          <div className="glass-card border border-indigo-200/50 dark:border-indigo-500/30 p-6 flex flex-col items-center justify-center min-h-[280px]">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 text-center">
              Produtividade consolidada
            </h3>
            <CircularProgress percent={pctProdutivo} size={140} strokeWidth={10} />
            <div className="mt-5 w-full max-w-xs space-y-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" aria-hidden />
                  Horas produtivas
                </span>
                <span className="font-medium text-gray-900 dark:text-white tabular-nums">
                  {formatTime(daySummary.productive)} ({pctProdutivo.toFixed(1)}%)
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500" aria-hidden />
                  Horas improdutivas ou indefinidas
                </span>
                <span className="font-medium text-gray-900 dark:text-white tabular-nums">
                  {formatTime(horasImprodutivasOuIndefinidas)} ({(100 - pctProdutivo).toFixed(1)}%)
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Barra inferior: link para timeline (player) */}
      <div className="fixed bottom-0 left-0 right-0 bg-gray-800 dark:bg-gray-900 border-t border-gray-700 py-2 px-4 flex items-center justify-between z-20">
        <span className="text-sm text-gray-400">Timeline de telas</span>
        <Link
          to={timelineUrl}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 text-sm font-medium"
        >
          <FilmIcon className="w-5 h-5" />
          Abrir player
        </Link>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, valueClassName = '', withInfo = false }) {
  return (
    <div className="glass-card p-3">
      <div className="flex items-center gap-1">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
          {label}
        </span>
        {withInfo && (
          <InformationCircleIcon className="w-4 h-4 text-gray-400" title="Custo indefinido" />
        )}
      </div>
      <p className={`mt-1 text-sm font-semibold text-gray-900 dark:text-white ${valueClassName}`}>
        {value}
      </p>
    </div>
  )
}

function ChartCard({ title, children, minHeight }) {
  return (
    <div className="glass-card p-4 flex flex-col" style={minHeight ? { minHeight } : undefined}>
      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-3">{title}</h3>
      <div className="flex-1 flex items-center justify-center min-h-[160px]">
        {children}
      </div>
    </div>
  )
}
