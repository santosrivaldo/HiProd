import React, { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { formatBrasiliaDate, getTodayIsoDate } from '../utils/timezoneUtils'
import { ComputerDesktopIcon, SignalIcon } from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

const POLL_INTERVAL_MS = 4000

/**
 * Bloco de telas ao vivo (DVR) para um usuário. Polling + exibição lado a lado.
 * Usado na página DVR e no console DVR (janela estilo VNC).
 */
export default function LiveScreensDvr({ userId, layout = 'row', showHeader = true, className = '' }) {
  const [frames, setFrames] = useState([])
  const [imageUrls, setImageUrls] = useState([])
  const [lastFetchAt, setLastFetchAt] = useState(null)
  const [loading, setLoading] = useState(!!userId)
  const [error, setError] = useState(null)
  const imageCache = useRef({})
  const pollTimer = useRef(null)
  const today = getTodayIsoDate()

  const fetchLatestFrames = React.useCallback(async () => {
    if (!userId) return
    try {
      const res = await api.get(
        `/screen-frames?usuario_monitorado_id=${userId}&date=${today}&limit=20&order=desc`
      )
      const list = res.data?.frames ?? []
      setFrames(list)
      setError(null)
      setLastFetchAt(new Date())
      if (list.length === 0) setImageUrls([])
    } catch (e) {
      setError(e.response?.data?.message || 'Erro ao buscar frames')
      setFrames([])
      setImageUrls([])
    } finally {
      setLoading(false)
    }
  }, [userId, today])

  useEffect(() => {
    if (!userId) {
      setLoading(false)
      setImageUrls([])
      return
    }
    setLoading(true)
    fetchLatestFrames()
  }, [userId, fetchLatestFrames])

  useEffect(() => {
    if (!userId || frames.length === 0) {
      setImageUrls([])
      return
    }
    const byTime = new Map()
    frames.forEach((f) => {
      const key = (f.captured_at || '').slice(0, 19)
      if (!byTime.has(key)) byTime.set(key, [])
      byTime.get(key).push(f)
    })
    const latestTime = Array.from(byTime.keys()).sort().reverse()[0]
    const latestItems = (byTime.get(latestTime) || []).sort((a, b) => (a.monitor_index ?? 0) - (b.monitor_index ?? 0))
    const frameIds = latestItems.map((f) => f.id).filter(Boolean)
    if (frameIds.length === 0) {
      setImageUrls([])
      return
    }
    const urls = []
    let done = 0
    frameIds.forEach((frameId, i) => {
      if (imageCache.current[frameId]) {
        urls[i] = imageCache.current[frameId]
        done++
        if (done === frameIds.length) setImageUrls([...urls])
        return
      }
      api.get(`/screen-frames/${frameId}/image`, { responseType: 'blob' })
        .then((res) => {
          const url = URL.createObjectURL(res.data)
          imageCache.current[frameId] = url
          urls[i] = url
          done++
          if (done === frameIds.length) setImageUrls([...urls])
        })
        .catch(() => {
          urls[i] = null
          done++
          if (done === frameIds.length) setImageUrls([...urls])
        })
    })
  }, [userId, frames])

  useEffect(() => {
    if (!userId) return
    pollTimer.current = setInterval(fetchLatestFrames, POLL_INTERVAL_MS)
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current)
    }
  }, [userId, fetchLatestFrames])

  useEffect(() => {
    return () => {
      Object.values(imageCache.current).forEach((url) => URL.revokeObjectURL(url))
      imageCache.current = {}
    }
  }, [])

  const latestTime = frames.length > 0 ? (() => {
    const byTime = new Map()
    frames.forEach((f) => {
      const key = (f.captured_at || '').slice(0, 19)
      if (!byTime.has(key)) byTime.set(key, [])
      byTime.get(key).push(f)
    })
    return Array.from(byTime.keys()).sort().reverse()[0]
  })() : null

  if (!userId) {
    return <div className="text-gray-400 text-center py-8 text-sm">Selecione um usuário.</div>
  }

  return (
    <div className={`flex flex-col min-h-0 ${className}`}>
      {showHeader && (
        <div className="flex-shrink-0 px-3 py-2 bg-gray-800 border-b border-gray-700 flex flex-wrap items-center gap-2 text-sm">
          <SignalIcon className="w-4 h-4 text-emerald-400" />
          <span className="text-emerald-400 font-medium">Ao vivo</span>
          {lastFetchAt && <span className="text-gray-500">Atualizado: {formatBrasiliaDate(lastFetchAt, 'time')}</span>}
          {latestTime && <span className="text-gray-400">{formatBrasiliaDate(latestTime, 'datetime')}</span>}
          {error && <span className="text-red-400">{error}</span>}
        </div>
      )}
      <div className="flex-1 overflow-auto p-3 flex items-center justify-center min-h-0">
        {loading && imageUrls.length === 0 && (
          <LoadingSpinner size="md" text="Conectando..." />
        )}
        {!loading && imageUrls.length === 0 && !error && (
          <div className="text-gray-400 text-center py-8 text-sm">Nenhum frame de hoje. As telas aparecerão quando o agente enviar capturas.</div>
        )}
        {imageUrls.length > 0 && (
          <div className={`flex items-stretch justify-center gap-3 w-full overflow-x-auto ${layout === 'row' ? 'flex-nowrap' : 'flex-wrap'}`}>
            {imageUrls.filter(Boolean).map((url, i) => (
              <div key={i} className="flex flex-col items-center gap-1 flex-1 min-w-0">
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <ComputerDesktopIcon className="w-4 h-4" /> Tela {i + 1}
                </span>
                <img
                  src={url}
                  alt={`Tela ${i + 1}`}
                  className="w-full h-auto object-contain rounded border border-gray-700 max-h-[70vh]"
                  draggable={false}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
