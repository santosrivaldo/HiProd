import React, { useEffect, useMemo, useState } from 'react'
import api from '../services/api'
import {
  parseBrasiliaDate,
  formatBrasiliaDate,
  startOfDayBrasilia,
  endOfDayBrasilia,
  getWeekStartBrasilia,
  subDaysBrasilia
} from '../utils/timezoneUtils'

const WEEKDAY_NAMES = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

export default function WeeklyTimeline() {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(false)
  const [weekStartIso, setWeekStartIso] = useState(getWeekStartBrasilia)
  const weekEndIso = useMemo(() => subDaysBrasilia(weekStartIso, -6), [weekStartIso])

  useEffect(() => {
    const fetchWeek = async () => {
      setLoading(true)
      try {
        const dataInicio = startOfDayBrasilia(weekStartIso)?.toISOString()
        const dataFim = endOfDayBrasilia(weekEndIso)?.toISOString()
        if (!dataInicio || !dataFim) return
        const res = await api.get(`/atividades?agrupar=true&limite=500&data_inicio=${encodeURIComponent(dataInicio)}&data_fim=${encodeURIComponent(dataFim)}`)
        setActivities(Array.isArray(res.data) ? res.data : [])
      } catch (e) {
        console.error('Erro ao carregar atividades da semana', e)
        setActivities([])
      } finally {
        setLoading(false)
      }
    }
    fetchWeek()
  }, [weekStartIso, weekEndIso])

  const dayIsos = useMemo(() => {
    return [0, 1, 2, 3, 4, 5, 6].map((i) => subDaysBrasilia(weekStartIso, -i))
  }, [weekStartIso])

  const activitiesByDay = useMemo(() => {
    const map = new Map()
    dayIsos.forEach((iso) => map.set(iso, []))
    for (const a of activities) {
      const when = a?.horario ? parseBrasiliaDate(a.horario) : null
      if (!when) continue
      const key = formatBrasiliaDate(when, 'isoDate')
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(a)
    }
    for (const [, arr] of map.entries()) {
      arr.sort((x, y) => new Date(x.horario).getTime() - new Date(y.horario).getTime())
    }
    return map
  }, [activities, dayIsos])

  const goPrevWeek = () => setWeekStartIso(subDaysBrasilia(weekStartIso, 7))
  const goNextWeek = () => setWeekStartIso(subDaysBrasilia(weekStartIso, -7))

  const weekdayLabel = (iso) => {
    const d = new Date(iso + 'T12:00:00-03:00')
    const day = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Sao_Paulo', weekday: 'short' }).format(d)
    const num = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 0 }[day]
    return `${WEEKDAY_NAMES[num]} ${formatBrasiliaDate(iso + 'T12:00:00-03:00', 'date').slice(0, 5)}`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Timeline semanal (São Paulo)</h2>
        <div className="flex items-center gap-2">
          <button onClick={goPrevWeek} className="px-3 py-1 rounded-md bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100">Semana anterior</button>
          <div className="text-sm text-gray-700 dark:text-gray-300">
            {formatBrasiliaDate(weekStartIso + 'T12:00:00-03:00', 'dateWithMonth')} — {formatBrasiliaDate(weekEndIso + 'T12:00:00-03:00', 'dateWithMonth')} {weekEndIso?.slice(0, 4)}
          </div>
          <button onClick={goNextWeek} className="px-3 py-1 rounded-md bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100">Próxima semana</button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-600 dark:text-gray-300">Carregando...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
          {dayIsos.map((iso) => {
            const list = activitiesByDay.get(iso) || []
            return (
              <div key={iso} className="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
                <div className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                  {weekdayLabel(iso)}
                </div>
                <div className="space-y-2">
                  {list.length === 0 && (
                    <div className="text-sm text-gray-500 dark:text-gray-400">Sem atividades</div>
                  )}
                  {list.map((act) => (
                    <div key={act.id || act.horario} className="text-sm p-2 rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-800 dark:text-gray-200">{act.titulo || act.dominio || act.aplicacao || 'Atividade'}</span>
                        <span className="text-xs text-gray-500">{formatBrasiliaDate(act.horario, 'time').slice(0, 5)}</span>
                      </div>
                      {act.categoria && (
                        <div className="text-xs text-gray-500 mt-1">{act.categoria}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}


