import React, { useState, useEffect } from 'react'
import { PhotoIcon, XMarkIcon, ArrowLeftIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import api from '../services/api'

const ScreenshotViewer = ({ 
  isOpen, 
  onClose, 
  activityId, 
  activityTitle = 'Screenshot da Atividade',
  onPrevious,
  onNext,
  hasPrevious = false,
  hasNext = false
}) => {
  const [screenshot, setScreenshot] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isOpen && activityId) {
      loadScreenshot()
    }
  }, [isOpen, activityId])

  const loadScreenshot = async () => {
    if (!activityId) return

    setLoading(true)
    setError(null)
    setScreenshot(null)

    try {
      const response = await api.get(`/atividade/screenshot/${activityId}`, {
        responseType: 'blob'
      })

      if (response.data) {
        // Converter blob para base64
        const reader = new FileReader()
        reader.onload = () => {
          const base64 = reader.result.split(',')[1] // Remove o prefixo data:image/jpeg;base64,
          setScreenshot(base64)
          setLoading(false)
        }
        reader.onerror = () => {
          setError('Erro ao processar imagem')
          setLoading(false)
        }
        reader.readAsDataURL(response.data)
      } else {
        setError('Screenshot não encontrado')
        setLoading(false)
      }
    } catch (error) {
      console.error('Erro ao carregar screenshot:', error)
      setError('Erro ao carregar screenshot')
      setLoading(false)
    }
  }

  const handlePrevious = () => {
    if (hasPrevious && onPrevious) {
      onPrevious()
    }
  }

  const handleNext = () => {
    if (hasNext && onNext) {
      onNext()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose()
    } else if (e.key === 'ArrowLeft' && hasPrevious) {
      handlePrevious()
    } else if (e.key === 'ArrowRight' && hasNext) {
      handleNext()
    }
  }

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, hasPrevious, hasNext])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
      <div className="relative max-w-6xl max-h-full mx-4 bg-white dark:bg-gray-800 rounded-lg shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {activityTitle}
          </h3>
          
          <div className="flex items-center space-x-2">
            {/* Navegação */}
            {(hasPrevious || hasNext) && (
              <div className="flex items-center space-x-1">
                <button
                  onClick={handlePrevious}
                  disabled={!hasPrevious}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Anterior (←)"
                >
                  <ArrowLeftIcon className="w-5 h-5" />
                </button>
                <button
                  onClick={handleNext}
                  disabled={!hasNext}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Próximo (→)"
                >
                  <ArrowRightIcon className="w-5 h-5" />
                </button>
              </div>
            )}
            
            {/* Botão fechar */}
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              title="Fechar (ESC)"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 max-h-96 overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Carregando screenshot...
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <PhotoIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {error}
                </p>
                <button
                  onClick={loadScreenshot}
                  className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Tentar novamente
                </button>
              </div>
            </div>
          )}

          {screenshot && !loading && (
            <div className="text-center">
              <img
                src={`data:image/jpeg;base64,${screenshot}`}
                alt="Screenshot da atividade"
                className="max-w-full h-auto rounded-lg shadow-lg mx-auto"
                style={{ maxHeight: '70vh' }}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {activityId && `Atividade ID: ${activityId}`}
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ScreenshotViewer
