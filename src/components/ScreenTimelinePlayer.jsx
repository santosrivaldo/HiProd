import React, { useState, useEffect, useRef, useCallback } from 'react'
import api from '../services/api'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  PlayIcon,
  PauseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

/**
 * Player de timeline de telas (embed). Recebe userId, date e opcionalmente initialAt.
 * Usado na página de detalhes do usuário para exibir o frame no horário do processo.
 */
export default function ScreenTimelinePlayer({ userId, date, initialAt = null, onClose, compact = true }) {
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
      return { time: k, items }
    })
  }, [frames])

  const currentSlot = framesBySecond[currentIndex]

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
    if (!initialAt || framesBySecond.length === 0) return
    const atTime = new Date(initialAt).getTime()
    if (isNaN(atTime)) return
    let bestIdx = 0
    let bestDiff = Infinity
    framesBySecond.forEach((slot, i) => {
      const slotTime = new Date(slot.time.replace(' ', 'T')).getTime()
      const diff = Math.abs(slotTime - atTime)
      if (diff < bestDiff) {
        bestDiff = diff
        bestIdx = i
      }
    })
    setCurrentIndex(bestIdx)
  }, [initialAt, framesBySecond])

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
    const slot = framesBySecond[currentIndex]
    const ids = slot?.items?.length ? slot.items.map((f) => f.id).filter(Boolean) : []
    if (ids.length) fetchImageUrls(ids)
    else setImageUrls([])
  }, [currentIndex, framesBySecond, fetchImageUrls])

  useEffect(() => {
    if (!playing || framesBySecond.length === 0) return
    playRef.current = setInterval(() => {
      setCurrentIndex((i) => {
        if (i >= framesBySecond.length - 1) {
          setPlaying(false)
          return i
        }
        return i + 1
      })
    }, 1000)
    return () => {
      if (playRef.current) clearInterval(playRef.current)
    }
  }, [playing, framesBySecond.length])

  useEffect(() => {
    return () => {
      Object.values(imageCache.current).forEach((url) => URL.revokeObjectURL(url))
      imageCache.current = {}
    }
  }, [])

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1))
  const goNext = () => setCurrentIndex((i) => Math.min(framesBySecond.length - 1, i + 1))

  if (!userId || !date) return null

  return (
    <div className={`rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-900 overflow-hidden ${compact ? 'max-w-4xl' : ''}`}>
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-sm font-medium text-gray-200">
          Timeline de telas — {date} {initialAt ? `• ${format(new Date(initialAt), 'HH:mm:ss')}` : ''}
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
            <div className="rounded-lg overflow-hidden bg-black flex items-center justify-center min-h-[280px] max-h-[50vh]">
              {imageUrls.length > 0 ? (
                <img
                  src={imageUrls[0]}
                  alt="Frame"
                  className="max-w-full max-h-[50vh] w-auto h-auto object-contain"
                />
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
                disabled={currentIndex >= framesBySecond.length - 1}
                className="p-2 rounded-full bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Próximo"
              >
                <ChevronRightIcon className="w-5 h-5" />
              </button>
            </div>
            <div className="text-center text-xs text-gray-500">
              {currentSlot && (
                <>
                  {format(parseISO(currentSlot.time), 'dd/MM/yyyy HH:mm:ss', { locale: ptBR })} —{' '}
                  {currentIndex + 1} / {framesBySecond.length} (segundos)
                </>
              )}
            </div>
            <div className="flex flex-wrap gap-0.5 justify-center pt-2">
              {framesBySecond.slice(0, 80).map((slot, i) => (
                <button
                  key={slot.time}
                  type="button"
                  onClick={() => { setCurrentIndex(i); setPlaying(false) }}
                  className={`w-1.5 h-4 rounded-sm transition-colors ${
                    i === currentIndex ? 'bg-indigo-500' : 'bg-gray-600 hover:bg-gray-500'
                  }`}
                  title={format(parseISO(slot.time), 'dd/MM/yyyy HH:mm:ss', { locale: ptBR })}
                />
              ))}
              {framesBySecond.length > 80 && (
                <span className="text-gray-500 text-xs self-center ml-1">+{framesBySecond.length - 80}s</span>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
