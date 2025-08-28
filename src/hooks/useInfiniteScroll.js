
import { useState, useEffect, useCallback } from 'react'

const useInfiniteScroll = (fetchData, initialPage = 1, pageSize = 50) => {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [page, setPage] = useState(initialPage)
  const [error, setError] = useState(null)

  const loadData = useCallback(async (pageNum = page, reset = false) => {
    if (loading) return

    try {
      setLoading(true)
      setError(null)
      
      const response = await fetchData(pageNum, pageSize)
      const newData = response.data || []
      
      if (reset) {
        setData(newData)
      } else {
        setData(prevData => [...prevData, ...newData])
      }
      
      // Se retornou menos dados que o tamanho da página, não há mais dados
      setHasMore(newData.length === pageSize)
      
    } catch (err) {
      setError(err)
      console.error('Erro ao carregar dados:', err)
    } finally {
      setLoading(false)
    }
  }, [fetchData, page, pageSize, loading])

  const loadMore = useCallback(() => {
    if (hasMore && !loading) {
      const nextPage = page + 1
      setPage(nextPage)
      loadData(nextPage, false)
    }
  }, [hasMore, loading, page, loadData])

  const refresh = useCallback(() => {
    setPage(initialPage)
    setHasMore(true)
    loadData(initialPage, true)
  }, [initialPage, loadData])

  const reset = useCallback(() => {
    setData([])
    setPage(initialPage)
    setHasMore(true)
    setError(null)
  }, [initialPage])

  // Carregar dados iniciais
  useEffect(() => {
    loadData(initialPage, true)
  }, [])

  return {
    data,
    loading,
    hasMore,
    error,
    loadMore,
    refresh,
    reset,
    page
  }
}

export default useInfiniteScroll
