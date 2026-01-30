import React, { useEffect, useRef, useState } from 'react'

const useIntersectionObserver = (options = {}) => {
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

    // Criar novo observer
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsIntersecting(entry.isIntersecting)
      },
      observerOptions
    )

    observerRef.current = observer
    observer.observe(element)

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
        observerRef.current = null
      }
    }
  }, []) // Executar apenas uma vez na montagem

  return [elementRef, isIntersecting]
}

export default useIntersectionObserver
