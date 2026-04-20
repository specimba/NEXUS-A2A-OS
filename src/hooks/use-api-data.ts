'use client'

import { useState, useEffect, useCallback } from 'react'

interface SystemData {
  agents: Record<string, unknown>[]
  models: Record<string, unknown>[]
  templates: Record<string, unknown>[]
  papers: Record<string, unknown>[]
  budget: Record<string, unknown>
  constitution: Record<string, unknown>
  state: Record<string, unknown>
}

export function useSystemData(refreshInterval = 30000) {
  const [data, setData] = useState<SystemData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await globalThis.fetch('/api/system')
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
    } catch (e) {
      console.error('System data fetch error:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, refreshInterval)
    return () => clearInterval(interval)
  }, [fetchData, refreshInterval])

  return { data, loading, refetch: fetchData }
}

export function useApiData<T = Record<string, unknown>>(url: string, refreshInterval = 30000) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await globalThis.fetch(url)
      if (res.ok) {
        const json = await res.json()
        setData(json)
      }
    } catch (e) {
      console.error(`API fetch error (${url}):`, e)
    } finally {
      setLoading(false)
    }
  }, [url])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, refreshInterval)
    return () => clearInterval(interval)
  }, [fetchData, refreshInterval])

  return { data, loading, refetch: fetchData }
}
