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
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const res = await globalThis.fetch('/api/system')
      if (res.ok) {
        const json = await res.json()
        setData(json)
      } else {
        const errText = await res.text().catch(() => 'Unknown error')
        setError(`System API error: ${res.status} ${errText}`)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Network error'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, refreshInterval)
    return () => clearInterval(interval)
  }, [fetchData, refreshInterval])

  return { data, loading, error, refetch: fetchData }
}

export function useApiData<T = Record<string, unknown>>(url: string, refreshInterval = 30000) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      const res = await globalThis.fetch(url)
      if (res.ok) {
        const json = await res.json()
        setData(json)
      } else {
        const errData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        setError(errData.error || `API error: ${res.status}`)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Network error — check your connection'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [url])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, refreshInterval)
    return () => clearInterval(interval)
  }, [fetchData, refreshInterval])

  return { data, loading, error, refetch: fetchData }
}
