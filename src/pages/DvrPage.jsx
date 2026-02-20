import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { formatBrasiliaDate, getTodayIsoDate } from '../utils/timezoneUtils'
import { ComputerDesktopIcon, SignalIcon } from '@heroicons/react/24/outline'
import LoadingSpinner from '../components/LoadingSpinner'

const POLL_INTERVAL_MS = 4000

/**
 * Página DVR: telas ao vivo do usuário monitorado (polling dos frames mais recentes).
 * Pode ser aberta em nova guia (só a tela, estilo VNC) ou pelo menu (com layout).
 */
export default function DvrPage() {
  const [searchParams] = useSearchParams()
  const userIdFromUrl = searchParams.get('userId')

  const [users, setUsers] = useState([])
  const [selectedUserId, setSelectedUserId] = useState(userIdFromUrl || '')
  const [frames, setFrames] = useState([])
  const [imageUrls, setImageUrls] = useState([])
  const [lastFetchAt, setLastFetchAt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const imageCache = useRef({})
  const pollTimer = useRef(null)

  const today = getTodayIsoDate()

  useEffect(() => {
    api.get('/usuarios-monitorados').then((res) => {
      const list = res.data || []
      setUsers(list)
      if (!selectedUserId && list.length > 0) setSelectedUserId(String(list[0].id))
    }).catch(() => setUsers([]))
  }, [])

  useEffect(() => {
    if (userIdFromUrl) setSelectedUserId(userIdFromUrl)
  }, [userIdFromUrl])

  const fetchLatestFrames = useCallback(async () => {
    if (!selectedUserId) return
    try {
      const res = await api.get(
        `/screen-frames?usuario_monitorado_id=${selectedUserId}&date=${today}&limit=20&order=desc`
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
  }, [selectedUserId, today])

  useEffect(() => {
    if (!selectedUserId) {
      setLoading(false)
      setImageUrls([])
      return
    }
    setLoading(true)
    fetchLatestFrames()
  }, [selectedUserId, fetchLatestFrames])

  useEffect(() => {
    if (!selectedUserId || frames.length === 0) {
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
  }, [frames])

  useEffect(() => {
    if (!selectedUserId) return
    pollTimer.current = setInterval(fetchLatestFrames, POLL_INTERVAL_MS)
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current)
    }
  }, [selectedUserId, fetchLatestFrames])

  useEffect(() => {
    return () => {
      Object.values(imageCache.current).forEach((url) => URL.revokeObjectURL(url))
      imageCache.current = {}
    }
  }, [])

  const selectedUser = users.find((u) => String(u.id) === String(selectedUserId))
  const latestTime = frames.length > 0 ? (() => {
    const byTime = new Map()
    frames.forEach((f) => {
      const key = (f.captured_at || '').slice(0, 19)
      if (!byTime.has(key)) byTime.set(key, [])
      byTime.get(key).push(f)
    })
    return Array.from(byTime.keys()).sort().reverse()[0]
  })() : null

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 flex flex-col">
      <header className="flex-shrink-0 px-4 py-2 bg-gray-800 border-b border-gray-700 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <SignalIcon className="w-5 h-5 text-emerald-400" />
          <span className="text-sm font-medium text-emerald-400">Ao vivo</span>
        </div>
        <select
          value={selectedUserId}
          onChange={(e) => setSelectedUserId(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">Selecione o usuário</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>{u.nome || `Usuário ${u.id}`}</option>
          ))}
        </select>
        {lastFetchAt && (
          <span className="text-xs text-gray-500">
            Última atualização: {formatBrasiliaDate(lastFetchAt, 'time')}
          </span>
        )}
        {latestTime && (
          <span className="text-xs text-gray-400">
            Tela: {formatBrasiliaDate(latestTime, 'datetime')}
          </span>
        )}
        {error && <span className="text-sm text-red-400">{error}</span>}
      </header>

      <main className="flex-1 overflow-auto p-4 flex items-center justify-center min-h-0">
        {!selectedUserId && (
          <div className="text-gray-400 text-center py-12">Selecione um usuário para ver as telas ao vivo.</div>
        )}
        {selectedUserId && loading && imageUrls.length === 0 && (
          <div className="flex items-center justify-center w-full min-h-[300px]">
            <LoadingSpinner size="lg" text="Conectando..." />
          </div>
        )}
        {selectedUserId && !loading && imageUrls.length === 0 && !error && (
          <div className="text-gray-400 text-center py-12">
            Nenhum frame de hoje ainda. As telas aparecerão quando o agente enviar capturas.
          </div>
        )}
        {selectedUserId && imageUrls.length > 0 && (
          <div className="w-full max-w-7xl mx-auto flex flex-wrap items-center justify-center gap-4">
            {imageUrls.filter(Boolean).map((url, i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <ComputerDesktopIcon className="w-4 h-4" /> Tela {i + 1}
                </span>
                <img
                  src={url}
                  alt={`Tela ${i + 1} ao vivo`}
                  className="max-w-full h-auto object-contain rounded-lg shadow-lg border border-gray-700"
                  style={{ maxHeight: '75vh' }}
                  draggable={false}
                />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
