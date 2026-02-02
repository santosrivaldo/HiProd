// Importação direta dos hooks - garantindo resolução correta
import { useEffect, useRef, useState } from 'react'

/**
 * Hook para observar quando um elemento entra ou sai da viewport
 * Usa IntersectionObserver API para detectar quando um elemento está visível
 * 
 * @param {Object} options - Opções do IntersectionObserver
 * @param {number} options.threshold - Threshold para disparar (0-1)
 * @param {string} options.rootMargin - Margem do root (ex: '100px')
 * @returns {[React.RefObject, boolean]} - [ref do elemento, se está visível]
 */
function useIntersectionObserver(options = {}) {
  const [isIntersecting, setIsIntersecting] = useState(false)
  const elementRef = useRef(null)
  const observerRef = useRef(null)

  useEffect(() => {
    const element = elementRef.current
    if (!element) return

    // Criar opções padrão mescladas com opções fornecidas
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '100px',
      ...options
    }

    // Desconectar observer anterior se existir
    if (observerRef.current) {
      observerRef.current.disconnect()
    }

    // Verificar se IntersectionObserver está disponível
    if (typeof IntersectionObserver === 'undefined') {
      console.warn('IntersectionObserver não está disponível neste navegador')
      return
    }

    // Criar novo observer
    try {
      const observer = new IntersectionObserver(
        ([entry]) => {
          setIsIntersecting(entry.isIntersecting)
        },
        observerOptions
      )

      observerRef.current = observer
      observer.observe(element)
    } catch (error) {
      console.error('Erro ao criar IntersectionObserver:', error)
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
        observerRef.current = null
      }
    }
  }, [options.threshold, options.rootMargin])

  return [elementRef, isIntersecting]
}

export default useIntersectionObserver
