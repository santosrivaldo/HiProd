import React, { useState, useEffect, useRef, useCallback } from 'react'
import api from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  PlayIcon,
  PauseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FilmIcon
} from '@heroicons/react/24/outline'

export default function ScreenTimelinePage() {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [frames, setFrames] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingImage, setLoadingImage] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [imageUrl, setImageUrl] = useState(null)
  const [error, setError] = useState(null)
  const playRef = useRef(null)
  const imageCache = useRef({})

  // Agrupar frames por segundo (captured_at) para exibir um "frame" por segundo na timeline
  const framesBySecond = React.useMemo(() => {
    const byTime = new Map()
    frames.forEach((f) => {
      const key = f.captured_at.slice(0, 19)
      if (!byTime.has(key)) byTime.set(key, [])
      byTime.get(key).push(f)
    })
    const keys = Array.from(byTime.keys()).sort()
    return keys.map((k) => ({ time: k, items: byTime.get(k) }))
  }, [frames])

  const currentSlot = framesBySecond[currentIndex]
  const currentFrame = currentSlot?.items?.[0] // primeiro monitor do segundo

  const loadUsers = useCallback(async () => {
    try {
      const res = await api.get('/usuarios-monitorados')
      const list = Array.isArray(res.data) ? res.data : []
      setUsers(list)
      if (list.length && !selectedUser) setSelectedUser(String(list[0].id))
    } catch (e) {
      console.error(e)
      setError('Erro ao carregar usuários')
    }
  }, [selectedUser])

  const loadFrames = useCallback(async () => {
    if (!selectedUser || !selectedDate) return
    setLoading(true)
    setError(null)
    setImageUrl(null)
    setCurrentIndex(0)
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

  const fetchImageUrl = useCallback(async (frameId) => {
    if (imageCache.current[frameId]) {
      setImageUrl(imageCache.current[frameId])
      return
    }
    setLoadingImage(true)
    try {
      const res = await api.get(`/screen-frames/${frameId}/image`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      imageCache.current[frameId] = url
      setImageUrl(url)
    } catch (e) {
      console.error('Erro ao carregar imagem', e)
      setImageUrl(null)
    } finally {
      setLoadingImage(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  useEffect(() => {
    loadFrames()
  }, [loadFrames])

  useEffect(() => {
    if (!currentFrame?.id) {
      setImageUrl(null)
      return
    }
    fetchImageUrl(currentFrame.id)
  }, [currentFrame?.id, fetchImageUrl])

  // Play: avança 1 slot por segundo
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

  const goPrev = () => setCurrentIndex((i) => Math.max(0, i - 1))
  const goNext = () => setCurrentIndex((i) => Math.min(framesBySecond.length - 1, i + 1))

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

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Usuário
          </label>
          <select
            value={selectedUser}
            onChange={(e) => setSelectedUser(e.target.value)}
            className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 min-w-[200px]"
          >
            <option value="">Selecione</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nome || `ID ${u.id}`}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Data
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
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

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 p-4">
          {error}
        </div>
      )}

      {loading && <LoadingSpinner />}

      {!loading && frames.length === 0 && selectedUser && !error && (
        <div className="rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 p-8 text-center">
          Nenhum frame encontrado para esta data. Verifique se o agente está enviando frames.
        </div>
      )}

      {!loading && framesBySecond.length > 0 && (
        <>
          <div className="bg-black/90 rounded-lg overflow-hidden flex items-center justify-center min-h-[400px] relative">
            {loadingImage && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                <LoadingSpinner size="md" />
              </div>
            )}
            {imageUrl ? (
              <img
                src={imageUrl}
                alt="Frame"
                className="max-w-full max-h-[80vh] w-auto h-auto object-contain"
                style={{ maxHeight: '70vh' }}
              />
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
              disabled={currentIndex >= framesBySecond.length - 1}
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
                {currentIndex + 1} / {framesBySecond.length} (segundos)
              </span>
            )}
          </div>

          {/* Scrubber: barra com pontos por segundo */}
          <div className="flex flex-wrap gap-1 justify-center py-2">
            {framesBySecond.slice(0, 120).map((slot, i) => (
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
            {framesBySecond.length > 120 && (
              <span className="text-xs text-gray-400 self-center ml-2">
                +{framesBySecond.length - 120} s
              </span>
            )}
          </div>
        </>
      )}
    </div>
  )
}
