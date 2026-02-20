import React, { useState, useEffect, useRef, useCallback } from 'react'
import api from '../services/api'
import { formatBrasiliaDate } from '../utils/timezoneUtils'
import {
  PlayIcon,
  PauseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

const toMinutes = (hhmm) => {
  const [h, m] = (hhmm || '00:00').split(':').map(Number)
  return (h || 0) * 60 + (m || 0)
}
const slotTimeMinutes = (slotTime) => {
  const t = String(slotTime).slice(11, 16)
  return toMinutes(t)
}

/**
 * Player de timeline de telas (embed). Recebe userId, date, opcionalmente initialAt e filtro por horário.
 * Usado na página de detalhes do usuário para exibir o frame no horário do processo.
 */
export default function ScreenTimelinePlayer({ userId, date, initialAt = null, filterStartTime = '00:00', filterEndTime = '23:59', onClose, compact = true }) {
  const [frames, setFrames] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [imageUrls, setImageUrls] = useState([])
  const playRef = useRef(null)
  const imageCache = useRef({})

  const framesBySecond = React.useMemo(() => {
    if (!frames?.length) return []
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

  useEffect(() => {
    setCurrentIndex((i) => Math.min(i, Math.max(0, framesBySecondFiltered.length - 1)))
  }, [framesBySecondFiltered.length])

  const loadFrames = useCallback(async () => {
    if (!userId || !date) return
    setLoading(true)
    setError(null)
    setFrames([])
    setImageUrls([])
    setCurrentIndex(0)
    try {
      const res = await api.get(
        `/screen-frames?usuario_monitorado_id=${userId}&date=${date}&limit=2000`
      )
      setFrames(res.data?.frames ?? [])
    } catch (e) {
      console.error(e)
      setError(e.response?.data?.message || 'Erro ao carregar frames')
    } finally {
      setLoading(false)
    }
  }, [userId, date])

  useEffect(() => {
    loadFrames()
  }, [loadFrames])

  useEffect(() => {
    if (!initialAt || framesBySecondFiltered.length === 0) return
    setCurrentIndex(0)
  }, [initialAt, framesBySecondFiltered])

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
    const slot = framesBySecondFiltered[currentIndex]
    const ids = slot?.items?.length ? slot.items.map((f) => f.id).filter(Boolean) : []
    if (ids.length) fetchImageUrls(ids)
    else setImageUrls([])
  }, [currentIndex, framesBySecondFiltered, fetchImageUrls])

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

  useEffect(() => {
    return () => {
      Object.values(imageCache.current).forEach((url) => URL.revokeObjectURL(url))
      imageCache.current = {}
    }
  }, [])

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1))
  const goNext = () => setCurrentIndex((i) => Math.min(framesBySecondFiltered.length - 1, i + 1))

  if (!userId || !date) return null

  return (
    <div className={`rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-900 overflow-hidden ${compact ? 'max-w-4xl' : ''}`}>
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-sm font-medium text-gray-200">
          Timeline de telas — {date} {initialAt ? `• ${formatBrasiliaDate(initialAt, 'time')}` : ''}
        </span>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700"
            aria-label="Fechar"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        )}
      </div>
      <div className="p-3">
        {loading && (
          <div className="flex items-center justify-center min-h-[280px]">
            <LoadingSpinner size="md" text="Carregando frames..." />
          </div>
        )}
        {error && !loading && (
          <div className="rounded-lg bg-red-900/20 text-red-300 p-4 text-sm">
            {error}
          </div>
        )}
        {!loading && !error && framesBySecond.length === 0 && (
          <div className="rounded-lg bg-gray-800 text-gray-400 p-6 text-center text-sm">
            Nenhum frame encontrado para esta data.
          </div>
        )}
        {!loading && !error && framesBySecond.length > 0 && (
          <>
            <div className="rounded-lg overflow-hidden bg-black flex flex-wrap items-center justify-center gap-2 min-h-[280px] max-h-[50vh] p-2">
              {imageUrls.length > 0 ? (
                imageUrls.map((url, i) => (
                  <div key={i} className="flex-1 min-w-0 flex justify-center">
                    <img
                      src={url}
                      alt={`Tela ${i + 1}`}
                      className="max-w-full max-h-[50vh] w-auto h-auto object-contain"
                    />
                  </div>
                ))
              ) : (
                <span className="text-gray-500 text-sm">Carregando frame...</span>
              )}
            </div>
            <div className="flex items-center justify-center gap-3 py-2">
              <button
                type="button"
                onClick={goPrev}
                disabled={currentIndex === 0}
                className="p-2 rounded-full bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Anterior"
              >
                <ChevronLeftIcon className="w-5 h-5" />
              </button>
              <button
                type="button"
                onClick={() => setPlaying(!playing)}
                className="p-2.5 rounded-full bg-indigo-600 text-white hover:bg-indigo-500"
                title={playing ? 'Pausar' : 'Reproduzir'}
              >
                {playing ? <PauseIcon className="w-6 h-6" /> : <PlayIcon className="w-6 h-6" />}
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={currentIndex >= framesBySecondFiltered.length - 1}
                className="p-2 rounded-full bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Próximo"
              >
                <ChevronRightIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="text-center text-xs text-gray-500">
              {currentSlot && (
                <>
                  {formatBrasiliaDate(currentSlot.displayTime ?? currentSlot.time, 'datetime')} —{' '}
                  {currentIndex + 1} / {framesBySecondFiltered.length} (segundos)
                  {framesBySecondFiltered.length < framesBySecond.length && (
                    <span className="ml-1 text-gray-500">(filtrado de {framesBySecond.length})</span>
                  )}
                </>
              )}
            </div>
            <div className="flex flex-wrap gap-0.5 justify-center pt-2">
              {framesBySecondFiltered.slice(0, 80).map((slot, i) => (
                <button
                  key={slot.time}
                  type="button"
                  onClick={() => { setCurrentIndex(i); setPlaying(false) }}
                  className={`w-1.5 h-4 rounded-sm transition-colors ${
                    i === currentIndex ? 'bg-indigo-500' : 'bg-gray-600 hover:bg-gray-500'
                  }`}
                  title={formatBrasiliaDate(slot.displayTime ?? slot.time, 'datetime')}
                />
              ))}
              {framesBySecondFiltered.length > 80 && (
                <span className="text-gray-500 text-xs self-center ml-1">+{framesBySecondFiltered.length - 80}s</span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
