import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { formatBrasiliaDate } from '../utils/timezoneUtils'
import {
  PlayIcon,
  PauseIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassPlusIcon,
  MagnifyingGlassMinusIcon,
  ArrowDownTrayIcon,
  Squares2X2Icon,
  ComputerDesktopIcon,
} from '@heroicons/react/24/outline'
import LoadingSpinner from '../components/LoadingSpinner'

const toMinutes = (hhmm) => {
  const [h, m] = (hhmm || '00:00').split(':').map(Number)
  return (h || 0) * 60 + (m || 0)
}
const slotTimeMinutes = (slotTime) => {
  const t = String(slotTime).slice(11, 16)
  return toMinutes(t)
}

/** viewMode: 'all' | 0 | 1 | ... (monitor index) */
export default function ScreenPreviewPage() {
  const [searchParams] = useSearchParams()
  const userId = searchParams.get('userId') || ''
  const date = searchParams.get('date') || ''
  const at = searchParams.get('at') || null
  const filterStartTime = searchParams.get('filterStartTime') || '00:00'
  const filterEndTime = searchParams.get('filterEndTime') || '23:59'

  const [frames, setFrames] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [imageUrls, setImageUrls] = useState([])
  const [viewMode, setViewMode] = useState('all') // 'all' | 0 | 1 | ...
  const [zoom, setZoom] = useState(1)
  const playRef = useRef(null)
  const imageCache = useRef({})
  const imgRefs = useRef([])

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
  const monitorCount = currentSlot?.items?.length ?? 0

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
    if (!at || framesBySecondFiltered.length === 0) return
    setCurrentIndex(0)
  }, [at, framesBySecondFiltered])

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

  const zoomMin = 0.25
  const zoomMax = 5
  const zoomStep = 0.25
  const zoomIn = () => setZoom((z) => Math.min(zoomMax, z + zoomStep))
  const zoomOut = () => setZoom((z) => Math.max(zoomMin, z - zoomStep))

  const displayUrls = viewMode === 'all' ? imageUrls : (typeof viewMode === 'number' && imageUrls[viewMode] ? [imageUrls[viewMode]] : imageUrls)

  const handleExportImage = useCallback(() => {
    if (displayUrls.length === 0) return
    const ts = currentSlot ? formatBrasiliaDate(currentSlot.displayTime ?? currentSlot.time, 'datetime').replace(/[/:]/g, '-').replace(/\s/g, '_') : 'frame'
    if (displayUrls.length === 1) {
      const a = document.createElement('a')
      a.href = displayUrls[0]
      a.download = `preview_${ts}.png`
      a.click()
      return
    }
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    const imgs = []
    let totalWidth = 0
    let maxHeight = 0
    let loaded = 0
    const gap = 8
    displayUrls.forEach((url, i) => {
      const img = new Image()
      img.onload = () => {
        imgs.push({ img, w: img.width, h: img.height, index: i })
        totalWidth += img.width + (i > 0 ? gap : 0)
        maxHeight = Math.max(maxHeight, img.height)
        loaded++
        if (loaded === displayUrls.length) {
          imgs.sort((a, b) => a.index - b.index)
          canvas.width = totalWidth
          canvas.height = maxHeight
          let x = 0
          imgs.forEach(({ img: im, w, h }) => {
            ctx.drawImage(im, x, 0, w, h)
            x += w + gap
          })
          canvas.toBlob((blob) => {
            if (!blob) return
            const u = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = u
            a.download = `preview_${ts}.png`
            a.click()
            URL.revokeObjectURL(u)
          }, 'image/png')
        }
      }
      img.onerror = () => {
        loaded++
        if (loaded === displayUrls.length && imgs.length > 0) {
          imgs.sort((a, b) => (a.index ?? 0) - (b.index ?? 0))
          let w = 0, h = 0
          imgs.forEach(({ w: ww, h: hh }, idx) => { w += ww + (idx > 0 ? gap : 0); h = Math.max(h, hh) })
          canvas.width = w
          canvas.height = h
          let x = 0
          imgs.forEach(({ img, w: ww, h: hh }) => {
            ctx.drawImage(img, x, 0, ww, hh)
            x += ww + gap
          })
          canvas.toBlob((blob) => {
            if (!blob) return
            const u = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = u
            a.download = `preview_${ts}.png`
            a.click()
            URL.revokeObjectURL(u)
          }, 'image/png')
        }
      }
      img.src = url
    })
  }, [displayUrls, currentSlot])

  if (!userId || !date) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-gray-400 p-6">
        <p>Use os parâmetros userId e date na URL. Ex.: /preview?userId=1&date=2025-02-18</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 flex flex-col">
      <header className="flex-shrink-0 px-4 py-3 bg-gray-800 border-b border-gray-700 flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium">
          Preview — {date} {currentSlot ? formatBrasiliaDate(currentSlot.displayTime ?? currentSlot.time, 'time') : ''}
        </span>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Tela:</span>
          <button
            type="button"
            onClick={() => setViewMode('all')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              viewMode === 'all' ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
            title="Todas as telas"
          >
            <Squares2X2Icon className="w-4 h-4 inline-block mr-1 align-middle" />
            Todas
          </button>
          {Array.from({ length: monitorCount }, (_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setViewMode(i)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                viewMode === i ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
              title={`Tela ${i + 1}`}
            >
              <ComputerDesktopIcon className="w-4 h-4 inline-block mr-1 align-middle" />
              Tela {i + 1}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <button type="button" onClick={zoomOut} disabled={zoom <= zoomMin} className="p-1.5 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-50" title="Menos zoom">
            <MagnifyingGlassMinusIcon className="w-5 h-5" />
          </button>
          <span className="px-2 text-sm tabular-nums min-w-[4rem] text-center">{Math.round(zoom * 100)}%</span>
          <button type="button" onClick={zoomIn} disabled={zoom >= zoomMax} className="p-1.5 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-50" title="Mais zoom">
            <MagnifyingGlassPlusIcon className="w-5 h-5" />
          </button>
        </div>

        <button
          type="button"
          onClick={handleExportImage}
          disabled={displayUrls.length === 0}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          title="Exportar imagem atual"
        >
          <ArrowDownTrayIcon className="w-5 h-5" />
          Exportar imagem
        </button>

        <div className="flex items-center gap-1 ml-auto">
          <button type="button" onClick={goPrev} disabled={currentIndex === 0} className="p-2 rounded-full bg-gray-700 hover:bg-gray-600 disabled:opacity-50" title="Anterior">
            <ChevronLeftIcon className="w-5 h-5" />
          </button>
          <button type="button" onClick={() => setPlaying(!playing)} className="p-2.5 rounded-full bg-indigo-600 hover:bg-indigo-500" title={playing ? 'Pausar' : 'Reproduzir'}>
            {playing ? <PauseIcon className="w-6 h-6" /> : <PlayIcon className="w-6 h-6" />}
          </button>
          <button type="button" onClick={goNext} disabled={currentIndex >= framesBySecondFiltered.length - 1} className="p-2 rounded-full bg-gray-700 hover:bg-gray-600 disabled:opacity-50" title="Próximo">
            <ChevronRightIcon className="w-5 h-5" />
          </button>
        </div>
        <span className="text-xs text-gray-500">
          {currentIndex + 1} / {framesBySecondFiltered.length}
        </span>
      </header>

      <main className="flex-1 overflow-auto p-4 flex items-start justify-center min-h-0">
        {loading && (
          <div className="flex items-center justify-center w-full min-h-[400px]">
            <LoadingSpinner size="lg" text="Carregando frames..." />
          </div>
        )}
        {error && !loading && (
          <div className="rounded-lg bg-red-900/20 text-red-300 p-6 text-center">{error}</div>
        )}
        {!loading && !error && framesBySecond.length === 0 && (
          <div className="rounded-lg bg-gray-800 text-gray-400 p-8 text-center">Nenhum frame encontrado para esta data.</div>
        )}
        {!loading && !error && framesBySecond.length > 0 && (
          <div className="w-full max-w-7xl overflow-auto rounded-lg bg-black flex items-center justify-center min-h-[60vh]" style={{ maxHeight: 'calc(100vh - 120px)' }}>
            {displayUrls.length > 0 ? (
              <div
                className="inline-flex flex-wrap items-center justify-center gap-2 p-4 transition-transform origin-top"
                style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
              >
                {displayUrls.map((url, i) => (
                  <img
                    key={i}
                    ref={(el) => { imgRefs.current[i] = el }}
                    src={url}
                    alt={`Tela ${viewMode === 'all' ? i + 1 : 1}`}
                    className="max-w-full h-auto object-contain shadow-lg"
                    style={{ maxHeight: '75vh' }}
                    draggable={false}
                  />
                ))}
              </div>
            ) : (
              <span className="text-gray-500 py-8">Carregando frame...</span>
            )}
          </div>
        )}
      </main>

      {!loading && !error && framesBySecondFiltered.length > 0 && (
        <div className="flex-shrink-0 px-4 py-2 bg-gray-800 border-t border-gray-700 flex flex-wrap gap-0.5 justify-center">
          {framesBySecondFiltered.slice(0, 100).map((slot, i) => (
            <button
              key={slot.time}
              type="button"
              onClick={() => { setCurrentIndex(i); setPlaying(false) }}
              className={`w-2 h-5 rounded-sm transition-colors ${
                i === currentIndex ? 'bg-indigo-500' : 'bg-gray-600 hover:bg-gray-500'
              }`}
              title={formatBrasiliaDate(slot.displayTime ?? slot.time, 'datetime')}
            />
          ))}
          {framesBySecondFiltered.length > 100 && <span className="text-gray-500 text-xs self-center ml-1">+{framesBySecondFiltered.length - 100}</span>}
        </div>
      )}
    </div>
  )
}
