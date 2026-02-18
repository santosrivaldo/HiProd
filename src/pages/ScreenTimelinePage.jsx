import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  PlayIcon,
  PauseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FilmIcon,
  Squares2X2Icon,
  Square2StackIcon
} from '@heroicons/react/24/outline'

export default function ScreenTimelinePage() {
  const [searchParams] = useSearchParams()
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState(searchParams.get('userId') || '')
  const [selectedDate, setSelectedDate] = useState(searchParams.get('date') || format(new Date(), 'yyyy-MM-dd'))
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
  const playRef = useRef(null)
  const imageCache = useRef({})

  // Agrupar frames por segundo; dentro de cada segundo, ordenar por monitor_index
  const framesBySecond = React.useMemo(() => {
    const byTime = new Map()
    frames.forEach((f) => {
      const key = f.captured_at.slice(0, 19)
      if (!byTime.has(key)) byTime.set(key, [])
      byTime.get(key).push(f)
    })
    const keys = Array.from(byTime.keys()).sort()
    return keys.map((k) => {
      const items = (byTime.get(k) || []).sort((a, b) => (a.monitor_index ?? 0) - (b.monitor_index ?? 0))
      return { time: k, items }
    })
  }, [frames])

  const toMinutes = (hhmm) => {
    const [h, m] = (hhmm || '00:00').split(':').map(Number)
    return (h || 0) * 60 + (m || 0)
  }

  const slotTimeMinutes = (slotTime) => {
    const t = slotTime.slice(11, 16)
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
    setCurrentIndex((i) => Math.min(i, Math.max(0, framesBySecondFiltered.length - 1)))
  }, [framesBySecondFiltered.length])

  const atParam = searchParams.get('at')

  useEffect(() => {
    if (!atParam || framesBySecond.length === 0) return
    const atTime = new Date(atParam).getTime()
    if (isNaN(atTime)) return
    const startDate = new Date(atTime - 30 * 60 * 1000)
    const endDate = new Date(atTime + 30 * 60 * 1000)
    setFilterStartTime(format(startDate, 'HH:mm'))
    setFilterEndTime(format(endDate, 'HH:mm'))
    const startM = toMinutes(format(startDate, 'HH:mm'))
    const endM = toMinutes(format(endDate, 'HH:mm'))
    const filtered = startM <= endM
      ? framesBySecond.filter((s) => { const m = slotTimeMinutes(s.time); return m >= startM && m <= endM })
      : framesBySecond.filter((s) => { const m = slotTimeMinutes(s.time); return m >= startM || m <= endM })
    let bestIdx = 0
    let bestDiff = Infinity
    filtered.forEach((slot, i) => {
      const slotTime = new Date(slot.time.replace(' ', 'T')).getTime()
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
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <FilmIcon className="w-8 h-8" />
          Timeline de telas
        </h1>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Usuário</label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 min-w-[200px]"
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
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Filtro por horário (início)</label>
            <input
              type="time"
              value={filterStartTime}
              onChange={(e) => setFilterStartTime(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Filtro por horário (fim)</label>
            <input
              type="time"
              value={filterEndTime}
              onChange={(e) => setFilterEndTime(e.target.value)}
              className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2"
            />
          </div>
          <button
            onClick={loadFrames}
            disabled={loading || !selectedUser}
            className="px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Carregando...' : 'Carregar'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 p-4">
          {error}
        </div>
      )}

      {!loading && frames.length === 0 && selectedUser && !error && (
        <div className="rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 p-8 text-center">
          Nenhum frame encontrado para esta data. Verifique se o agente está enviando frames.
        </div>
      )}

      {framesBySecond.length > 0 && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4 py-2">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Telas para seleção:</span>
              <button
                onClick={() => setViewMode('one')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'one'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-500'
                }`}
                title="Uma tela apenas"
              >
                <Square2StackIcon className="w-5 h-5" />
                Uma tela
              </button>
              <button
                onClick={() => setViewMode('two')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'two'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-500'
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
                    className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-2 py-1.5 text-sm"
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

          <div className="bg-black/90 rounded-lg overflow-hidden flex items-center justify-center min-h-[400px] relative">
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

          <div className="flex items-center justify-center gap-4 py-2">
            <button
              onClick={goPrev}
              disabled={currentIndex === 0}
              className="p-2 rounded-full bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Anterior"
            >
              <ChevronLeftIcon className="w-6 h-6" />
            </button>
            <button
              onClick={() => setPlaying(!playing)}
              className="p-3 rounded-full bg-indigo-600 text-white hover:bg-indigo-700"
              title={playing ? 'Pausar' : 'Reproduzir (1 frame/s)'}
            >
              {playing ? <PauseIcon className="w-8 h-8" /> : <PlayIcon className="w-8 h-8" />}
            </button>
            <button
              onClick={goNext}
              disabled={currentIndex >= framesBySecondFiltered.length - 1}
              className="p-2 rounded-full bg-gray-200 dark:bg-gray-600 hover:bg-gray-300 dark:hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Próximo"
            >
              <ChevronRightIcon className="w-6 h-6" />
            </button>
          </div>

          <div className="text-center text-sm text-gray-500 dark:text-gray-400">
            {currentSlot && (
              <span>
                {format(parseISO(currentSlot.time), "dd/MM/yyyy HH:mm:ss", { locale: ptBR })} —{' '}
                {currentIndex + 1} / {framesBySecondFiltered.length} (segundos)
                {framesBySecondFiltered.length < framesBySecond.length && (
                  <span className="ml-1 text-gray-400">(filtrado de {framesBySecond.length})</span>
                )}
              </span>
            )}
          </div>

          {/* Scrubber: barra com pontos por segundo (lista filtrada) */}
          <div className="flex flex-wrap gap-1 justify-center py-2">
            {framesBySecondFiltered.slice(0, 120).map((slot, i) => (
              <button
                key={slot.time}
                onClick={() => {
                  setCurrentIndex(i)
                  setPlaying(false)
                }}
                className={`w-2 h-6 rounded transition-colors ${
                  i === currentIndex
                    ? 'bg-indigo-600'
                    : 'bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500'
                }`}
                title={format(parseISO(slot.time), "dd/MM/yyyy HH:mm:ss", { locale: ptBR })}
              />
            ))}
            {framesBySecondFiltered.length > 120 && (
              <span className="text-xs text-gray-400 self-center ml-2">
                +{framesBySecondFiltered.length - 120} s
              </span>
            )}
          </div>
        </>
      )}
    </div>
  )
}
