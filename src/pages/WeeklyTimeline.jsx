import React, { useEffect, useMemo, useState } from 'react'
import api from '../services/api'
import { format, startOfWeek, endOfWeek, isSameDay, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

function parseBrasiliaDate(dateString) {
  try {
    // Backend sends ISO-like strings in Brasília timezone; parse safely
    return new Date(dateString)
  } catch (e) {
    return new Date()
  }
}

export default function WeeklyTimeline() {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(false)
  const [weekStart, setWeekStart] = useState(startOfWeek(new Date(), { weekStartsOn: 1 }))
  const weekEnd = useMemo(() => endOfWeek(weekStart, { weekStartsOn: 1 }), [weekStart])

  useEffect(() => {
    const fetchWeek = async () => {
      setLoading(true)
      try {
        const dataInicio = weekStart.toISOString()
        const dataFim = weekEnd.toISOString()
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
  }, [weekStart, weekEnd])

  const days = useMemo(() => {
    const list = []
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart)
      d.setDate(weekStart.getDate() + i)
      list.push(d)
    }
    return list
  }, [weekStart])

  const activitiesByDay = useMemo(() => {
    const map = new Map()
    days.forEach(d => map.set(format(d, 'yyyy-MM-dd'), []))
    for (const a of activities) {
      const when = a?.horario ? parseBrasiliaDate(a.horario) : null
      if (!when) continue
      const key = format(when, 'yyyy-MM-dd')
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(a)
    }
    // sort each day by time asc
    for (const [, arr] of map.entries()) {
      arr.sort((x, y) => new Date(x.horario) - new Date(y.horario))
    }
    return map
  }, [activities, days])

  const goPrevWeek = () => {
    const prev = new Date(weekStart)
    prev.setDate(prev.getDate() - 7)
    setWeekStart(prev)
  }

  const goNextWeek = () => {
    const next = new Date(weekStart)
    next.setDate(next.getDate() + 7)
    setWeekStart(next)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Timeline semanal</h2>
        <div className="flex items-center gap-2">
          <button onClick={goPrevWeek} className="px-3 py-1 rounded-md bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100">Semana anterior</button>
          <div className="text-sm text-gray-700 dark:text-gray-300">
            {format(weekStart, "dd 'de' MMM", { locale: ptBR })} — {format(weekEnd, "dd 'de' MMM yyyy", { locale: ptBR })}
          </div>
          <button onClick={goNextWeek} className="px-3 py-1 rounded-md bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100">Próxima semana</button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-600 dark:text-gray-300">Carregando...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
          {days.map(day => {
            const key = format(day, 'yyyy-MM-dd')
            const list = activitiesByDay.get(key) || []
            return (
              <div key={key} className="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
                <div className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                  {format(day, 'EEE dd/MM', { locale: ptBR })}
                </div>
                <div className="space-y-2">
                  {list.length === 0 && (
                    <div className="text-sm text-gray-500 dark:text-gray-400">Sem atividades</div>
                  )}
                  {list.map(act => (
                    <div key={act.id || act.horario} className="text-sm p-2 rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-800 dark:text-gray-200">{act.titulo || act.dominio || act.aplicacao || 'Atividade'}</span>
                        <span className="text-xs text-gray-500">{format(parseBrasiliaDate(act.horario), 'HH:mm')}</span>
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


