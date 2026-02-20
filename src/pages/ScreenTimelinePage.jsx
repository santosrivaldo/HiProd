import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { formatBrasiliaDate } from '../utils/timezoneUtils'
import { formatBrasiliaDate, getTodayIsoDate, formatBrasiliaTimeHHMM } from '../utils/timezoneUtils'
import {
  PlayIcon,
  PauseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FilmIcon,
  Squares2X2Icon,
  Square2StackIcon,
  ClipboardDocumentListIcon
} from '@heroicons/react/24/outline'

export default function ScreenTimelinePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState(searchParams.get('userId') || '')
  const [selectedDate, setSelectedDate] = useState(searchParams.get('date') || getTodayIsoDate())
  const [frames, setFrames] = useState([])
  const [loading, setLoading] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [imageUrls, setImageUrls] = useState([]) // uma ou duas URLs conforme viewMode
  const [viewMode, setViewMode] = useState('one') // 'one' = uma tela, 'two' = duas telas
  const [selectedMonitorIndex, setSelectedMonitorIndex] = useState(0) // qual tela exibir no modo "uma tela" (0 = primeira, 1 = segunda)
  const [filterStartTime, setFilterStartTime] = useState('00:00') // HH:mm
  const [filterEndTime, setFilterEndTime] = useState('23:59') // HH:mm
  const [error, setError] = useState(null)
  const [atividades, setAtividades] = useState([])
  const [showAtividades, setShowAtividades] = useState(true)
  const playRef = useRef(null)
  const imageCache = useRef({})

  // Agrupar frames por segundo; dentro de cada segundo, ordenar por monitor_index
  // time = chave para ordenação (19 chars); displayTime = captured_at completo para exibir em Brasília
  const framesBySecond = React.useMemo(() => {
    const byTime = new Map()
    frames.forEach((f) => {
      const key = (f.captured_at || '').slice(0, 19)
      if (!byTime.has(key)) byTime.set(key, [])
      byTime.get(key).push(f)
    })
    const keys = Array.from(byTime.keys()).sort()
    return keys.map((k) => {
      const items = (byTime.get(k) || []).sort((a, b) => (a.monitor_index ?? 0) - (b.monitor_index ?? 0))
      const displayTime = items[0]?.captured_at || k
      return { time: k, displayTime, items }
    })
  }, [frames])

  const toMinutes = (hhmm) => {
    const [h, m] = (hhmm || '00:00').split(':').map(Number)
    return (h || 0) * 60 + (m || 0)
  }

  const slotTimeMinutes = (slotTime) => {
    const t = String(slotTime).slice(11, 16)
    return toMinutes(t)
  }

  const framesBySecondFiltered = React.useMemo(() => {
    const startM = toMinutes(filterStartTime)
    const endM = toMinutes(filterEndTime)
    if (startM <= endM) {
      return framesBySecond.filter((s) => {
        const m = slotTimeMinutes(s.time)
        return m >= startM && m <= endM
      })
    }
    return framesBySecond.filter((s) => {
      const m = slotTimeMinutes(s.time)
      return m >= startM || m <= endM
    })
  }, [framesBySecond, filterStartTime, filterEndTime])

  const currentSlot = framesBySecondFiltered[currentIndex]
  // Número máximo de monitores nos dados (para o seletor no modo "uma tela")
  const maxMonitors = React.useMemo(() => {
    if (!framesBySecondFiltered.length) return 1
    return Math.max(1, ...framesBySecondFiltered.map((s) => s.items?.length ?? 0))
  }, [framesBySecondFiltered])
  // Frames a exibir no slot atual: 1 ou 2 conforme viewMode; no modo "uma tela" usa selectedMonitorIndex
  const currentFramesToShow = currentSlot?.items?.length
    ? viewMode === 'two'
      ? currentSlot.items.slice(0, 2)
      : (() => {
          const idx = Math.min(selectedMonitorIndex, currentSlot.items.length - 1)
          return [currentSlot.items[idx]]
        })()
    : []

  const loadUsers = useCallback(async () => {
    try {
      const res = await api.get('/usuarios-monitorados')
      const list = Array.isArray(res.data) ? res.data : []
      setUsers(list)
      const fromUrl = searchParams.get('userId')
      if (list.length && !selectedUser) {
        setSelectedUser(fromUrl && list.some((u) => String(u.id) === fromUrl) ? fromUrl : String(list[0].id))
      }
    } catch (e) {
      console.error(e)
      setError('Erro ao carregar usuários')
    }
  }, [selectedUser, searchParams])

  const loadFrames = useCallback(async () => {
    if (!selectedUser || !selectedDate) return
    setLoading(true)
    setError(null)
    setImageUrls([])
    setCurrentIndex(0)
    setSelectedMonitorIndex(0)
    try {
      const res = await api.get(
        `/screen-frames?usuario_monitorado_id=${selectedUser}&date=${selectedDate}&limit=2000`
      )
      const list = res.data?.frames ?? []
      setFrames(list)
    } catch (e) {
      console.error(e)
      setError(e.response?.data?.message || 'Erro ao carregar frames')
      setFrames([])
    } finally {
      setLoading(false)
    }
  }, [selectedUser, selectedDate])

  const loadAtividades = useCallback(async () => {
    if (!selectedUser || !selectedDate) return
    try {
      const res = await api.get(
        `/atividades-by-window?usuario_monitorado_id=${selectedUser}&date=${selectedDate}&limit=200`
      )
      setAtividades(res.data?.atividades ?? [])
    } catch (e) {
      setAtividades([])
    }
  }, [selectedUser, selectedDate])

  const fetchImageUrls = useCallback(async (frameIds) => {
    if (!frameIds?.length) {
      setImageUrls([])
      return
    }
    const urls = []
    for (const frameId of frameIds) {
      if (imageCache.current[frameId]) {
        urls.push(imageCache.current[frameId])
        continue
      }
      try {
        const res = await api.get(`/screen-frames/${frameId}/image`, { responseType: 'blob' })
        const url = URL.createObjectURL(res.data)
        imageCache.current[frameId] = url
        urls.push(url)
      } catch (e) {
        console.error('Erro ao carregar imagem', e)
      }
    }
    setImageUrls(urls)
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  useEffect(() => {
    const userId = searchParams.get('userId')
    const date = searchParams.get('date')
    if (userId) setSelectedUser(userId)
    if (date) setSelectedDate(date)
  }, [searchParams])

  useEffect(() => {
    loadFrames()
  }, [loadFrames])

  useEffect(() => {
    loadAtividades()
  }, [loadAtividades])

  useEffect(() => {
    setCurrentIndex((i) => Math.min(i, Math.max(0, framesBySecondFiltered.length - 1)))
  }, [framesBySecondFiltered.length])

  const atParam = searchParams.get('at')

  useEffect(() => {
    if (!atParam || framesBySecond.length === 0) return
    const atTime = new Date(atParam).getTime()
    if (isNaN(atTime)) return
    const startDate = new Date(atTime - 30 * 60 * 1000)
    const endDate = new Date(atTime + 30 * 60 * 1000)
    setFilterStartTime(formatBrasiliaTimeHHMM(startDate))
    setFilterEndTime(formatBrasiliaTimeHHMM(endDate))
    const startM = toMinutes(formatBrasiliaTimeHHMM(startDate))
    const endM = toMinutes(formatBrasiliaTimeHHMM(endDate))
    const filtered = startM <= endM
      ? framesBySecond.filter((s) => { const m = slotTimeMinutes(s.time); return m >= startM && m <= endM })
      : framesBySecond.filter((s) => { const m = slotTimeMinutes(s.time); return m >= startM || m <= endM })
    let bestIdx = 0
    let bestDiff = Infinity
    filtered.forEach((slot, i) => {
      const slotTimeStr = slot.displayTime || slot.time || ''
      const slotTime = slotTimeStr ? new Date(slotTimeStr.replace(' ', 'T')).getTime() : 0
      if (!slotTime) return
      const diff = Math.abs(slotTime - atTime)
      if (diff < bestDiff) {
        bestDiff = diff
        bestIdx = i
      }
    })
    setCurrentIndex(bestIdx)
  }, [atParam, framesBySecond])

  useEffect(() => {
    const slot = framesBySecondFiltered[currentIndex]
    const toShow = slot?.items?.length
      ? viewMode === 'two'
        ? slot.items.slice(0, 2)
        : [slot.items[Math.min(selectedMonitorIndex, slot.items.length - 1)]]
      : []
    const ids = toShow.map((f) => f.id).filter(Boolean)
    if (ids.length) fetchImageUrls(ids)
    else setImageUrls([])
  }, [currentIndex, viewMode, selectedMonitorIndex, framesBySecondFiltered, fetchImageUrls])

  // Play: avança 1 slot por segundo
  useEffect(() => {
    if (!playing || framesBySecondFiltered.length === 0) return
    playRef.current = setInterval(() => {
      setCurrentIndex((i) => {
        if (i >= framesBySecondFiltered.length - 1) {
          setPlaying(false)
          return i
        }
        return i + 1
      })
    }, 1000)
    return () => {
      if (playRef.current) clearInterval(playRef.current)
    }
  }, [playing, framesBySecondFiltered.length])

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1))
  const goNext = () => setCurrentIndex((i) => Math.min(framesBySecondFiltered.length - 1, i + 1))

  // Limpar object URLs ao desmontar
  useEffect(() => {
    return () => {
      Object.values(imageCache.current).forEach((url) => URL.revokeObjectURL(url))
      imageCache.current = {}
    }
  }, [])

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-7xl mx-auto">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2 tracking-tight">
          <span className="p-2 rounded-xl glass">
            <FilmIcon className="w-7 h-7 text-indigo-600 dark:text-indigo-400" />
          </span>
          Timeline de telas
        </h1>
      </div>

      <div className="glass-card p-5 space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Usuário</label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="glass-input text-gray-900 dark:text-white px-3 py-2 min-w-[200px] focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-400"
            >
              <option value="">Selecione</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.nome || `ID ${u.id}`}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Filtro por dia</label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="glass-input text-gray-900 dark:text-white px-3 py-2 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Filtro por horário (início)</label>
            <input
              type="time"
              value={filterStartTime}
              onChange={(e) => setFilterStartTime(e.target.value)}
              className="glass-input text-gray-900 dark:text-white px-3 py-2 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Filtro por horário (fim)</label>
            <input
              type="time"
              value={filterEndTime}
              onChange={(e) => setFilterEndTime(e.target.value)}
              className="glass-input text-gray-900 dark:text-white px-3 py-2 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-400"
            />
          </div>
          <button
            onClick={loadFrames}
            disabled={loading || !selectedUser}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white font-medium shadow-lg shadow-indigo-500/30 hover:bg-indigo-500 hover:shadow-indigo-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? 'Carregando...' : 'Carregar'}
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-card p-4 border-red-200/50 dark:border-red-500/20 bg-red-50/80 dark:bg-red-900/20 text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {!loading && frames.length === 0 && selectedUser && !error && (
        <div className="glass-card p-8 text-center text-gray-600 dark:text-gray-400">
          Nenhum frame encontrado para esta data. Verifique se o agente está enviando frames.
        </div>
      )}

      {framesBySecond.length > 0 && (
        <>
          <div className="glass-card flex flex-wrap items-center justify-between gap-4 p-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Telas para seleção:</span>
              <button
                onClick={() => setViewMode('one')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                  viewMode === 'one'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30'
                    : 'bg-white/50 dark:bg-white/10 text-gray-700 dark:text-gray-300 hover:bg-white/70 dark:hover:bg-white/15 border border-white/20'
                }`}
                title="Uma tela apenas"
              >
                <Square2StackIcon className="w-5 h-5" />
                Uma tela
              </button>
              <button
                onClick={() => setViewMode('two')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all ${
                  viewMode === 'two'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30'
                    : 'bg-white/50 dark:bg-white/10 text-gray-700 dark:text-gray-300 hover:bg-white/70 dark:hover:bg-white/15 border border-white/20'
                }`}
                title="Duas telas (quando houver 2 monitores)"
              >
                <Squares2X2Icon className="w-5 h-5" />
                Duas telas
              </button>
              {viewMode === 'one' && maxMonitors >= 2 && (
                <>
                  <span className="text-sm text-gray-500 dark:text-gray-400 mx-1">|</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">Qual tela:</span>
                  <select
                    value={selectedMonitorIndex}
                    onChange={(e) => setSelectedMonitorIndex(Number(e.target.value))}
                    className="glass-input text-gray-900 dark:text-white px-2 py-1.5 text-sm"
                    title="Escolha qual monitor exibir"
                  >
                    {Array.from({ length: maxMonitors }, (_, i) => (
                      <option key={i} value={i}>
                        Tela {i + 1}
                      </option>
                    ))}
                  </select>
                </>
              )}
            </div>
          </div>

          <div className="glass-card overflow-hidden rounded-2xl min-h-[400px] relative">
            <div className="bg-black/95 flex items-center justify-center min-h-[400px] w-full">
            {imageUrls.length > 0 ? (
              <div
                className={`flex gap-2 p-2 w-full justify-center items-center ${
                  imageUrls.length === 2 ? 'flex-row' : ''
                }`}
              >
                {imageUrls.map((url, i) => (
                  <div key={i} className="flex-1 min-w-0 flex justify-center">
                    <img
                      src={url}
                      alt={imageUrls.length === 2 ? `Tela ${i + 1}` : 'Frame'}
                      className="max-w-full max-h-[80vh] w-auto h-auto object-contain"
                      style={{ maxHeight: '70vh' }}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <span className="text-gray-500">Selecione um instante na timeline</span>
            )}
            </div>
          </div>

          <div className="glass-card flex items-center justify-center gap-4 p-3">
            <button
              onClick={goPrev}
              disabled={currentIndex === 0}
              className="p-2.5 rounded-xl bg-white/60 dark:bg-white/10 hover:bg-white/80 dark:hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors border border-white/20"
              title="Anterior"
            >
              <ChevronLeftIcon className="w-6 h-6 text-gray-700 dark:text-gray-200" />
            </button>
            <button
              onClick={() => setPlaying(!playing)}
              className="p-3 rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-500/40 hover:bg-indigo-500 hover:shadow-indigo-500/50 transition-all"
              title={playing ? 'Pausar' : 'Reproduzir (1 frame/s)'}
            >
              {playing ? <PauseIcon className="w-8 h-8" /> : <PlayIcon className="w-8 h-8" />}
            </button>
            <button
              onClick={goNext}
              disabled={currentIndex >= framesBySecondFiltered.length - 1}
              className="p-2.5 rounded-xl bg-white/60 dark:bg-white/10 hover:bg-white/80 dark:hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors border border-white/20"
              title="Próximo"
            >
              <ChevronRightIcon className="w-6 h-6 text-gray-700 dark:text-gray-200" />
            </button>
          </div>

          <div className="text-center text-sm text-gray-500 dark:text-gray-400">
            {currentSlot && (
              <span>
                {formatBrasiliaDate(currentSlot.displayTime ?? currentSlot.time, 'datetime')} —{' '}
                {currentIndex + 1} / {framesBySecondFiltered.length} (segundos)
                {framesBySecondFiltered.length < framesBySecond.length && (
                  <span className="ml-1 text-gray-400">(filtrado de {framesBySecond.length})</span>
                )}
              </span>
            )}
          </div>

          {/* Scrubber: barra com pontos por segundo (lista filtrada) */}
          <div className="glass-card flex flex-wrap gap-1 justify-center p-3">
            {framesBySecondFiltered.slice(0, 120).map((slot, i) => (
              <button
                key={slot.time}
                onClick={() => {
                  setCurrentIndex(i)
                  setPlaying(false)
                }}
                className={`w-2 h-6 rounded-md transition-all ${
                  i === currentIndex
                    ? 'bg-indigo-600 shadow-md shadow-indigo-500/40'
                    : 'bg-white/50 dark:bg-white/20 hover:bg-white/70 dark:hover:bg-white/30 border border-white/20'
                }`}
                title={formatBrasiliaDate(slot.displayTime ?? slot.time, 'datetime')}
              />
            ))}
            {framesBySecondFiltered.length > 120 && (
              <span className="text-xs text-gray-400 self-center ml-2">
                +{framesBySecondFiltered.length - 120} s
              </span>
            )}
          </div>

          {atividades.length > 0 && (
            <div className="glass-card p-4 mt-4">
              <button
                type="button"
                onClick={() => setShowAtividades((v) => !v)}
                className="flex items-center gap-2 w-full text-left font-medium text-gray-900 dark:text-white"
              >
                <ClipboardDocumentListIcon className="w-5 h-5 text-indigo-500" />
                Atividades neste dia ({atividades.length})
              </button>
              {showAtividades && (
                <div className="mt-3 max-h-48 overflow-y-auto space-y-1">
                  {atividades.slice(0, 50).map((a) => (
                    <div
                      key={a.id}
                      className="flex items-center justify-between gap-2 py-1.5 px-2 rounded-lg hover:bg-white/10 dark:hover:bg-gray-700/50"
                    >
                      <span className="text-sm text-gray-600 dark:text-gray-300 truncate flex-1" title={a.active_window}>
                        {formatBrasiliaDate(a.horario, 'time')} — {a.active_window || a.categoria}
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          const at = a.horario_iso || a.horario
                          if (at) {
                            setSearchParams((prev) => {
                              const p = new URLSearchParams(prev)
                              p.set('at', at)
                              return p
                            })
                          }
                        }}
                        className="flex-shrink-0 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                        title="Ir para este momento na timeline"
                      >
                        Tela
                      </button>
                    </div>
                  ))}
                  {atividades.length > 50 && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 pt-1">
                      +{atividades.length - 50} atividades (mostrando 50)
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
