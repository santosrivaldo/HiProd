import { useState, useCallback } from 'react'
import api from '../services/api'

export const useScreenshots = () => {
  const [screenshots, setScreenshots] = useState(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadScreenshot = useCallback(async (activityId) => {
    // Se já temos o screenshot em cache, retornar imediatamente
    if (screenshots.has(activityId)) {
      return screenshots.get(activityId)
    }

    setLoading(true)
    setError(null)

    try {
      const response = await api.get(`/atividade/screenshot/${activityId}`, {
        responseType: 'blob'
      })

      if (response.data) {
        // Converter blob para base64
        const reader = new FileReader()
        return new Promise((resolve, reject) => {
          reader.onload = () => {
            const base64 = reader.result.split(',')[1] // Remove o prefixo data:image/jpeg;base64,
            const screenshotData = {
              id: activityId,
              data: base64,
              loadedAt: new Date().toISOString()
            }
            
            // Armazenar no cache
            setScreenshots(prev => new Map(prev).set(activityId, screenshotData))
            setLoading(false)
            resolve(screenshotData)
          }
          reader.onerror = () => {
            setError('Erro ao processar imagem')
            setLoading(false)
            reject(new Error('Erro ao processar imagem'))
          }
          reader.readAsDataURL(response.data)
        })
      } else {
        setError('Screenshot não encontrado')
        setLoading(false)
        throw new Error('Screenshot não encontrado')
      }
    } catch (error) {
      console.error('Erro ao carregar screenshot:', error)
      setError('Erro ao carregar screenshot')
      setLoading(false)
      throw error
    }
  }, [screenshots])

  const getScreenshot = useCallback((activityId) => {
    return screenshots.get(activityId)
  }, [screenshots])

  const clearCache = useCallback(() => {
    setScreenshots(new Map())
  }, [])

  const removeScreenshot = useCallback((activityId) => {
    setScreenshots(prev => {
      const newMap = new Map(prev)
      newMap.delete(activityId)
      return newMap
    })
  }, [])

  return {
    screenshots,
    loading,
    error,
    loadScreenshot,
    getScreenshot,
    clearCache,
    removeScreenshot
  }
}

export default useScreenshots
