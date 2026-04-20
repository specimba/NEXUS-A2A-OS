'use client'

import { useState, useEffect, useCallback } from 'react'

interface SystemData {
  agents: any[]
  models: any[]
  templates: any[]
  papers: any[]
  budget: any
  constitution: any
  state: any
}

export function useSystemData(refreshInterval = 30000) {
  const [data, setData] = useState<SystemData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const res = await fetch('/api/system')
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
    fetch()
    const interval = setInterval(fetch, refreshInterval)
    return () => clearInterval(interval)
  }, [fetch, refreshInterval])

  return { data, loading, refetch: fetch }
}

export function useApiData<T = any>(url: string, refreshInterval = 30000) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const res = await fetch(url)
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
    fetch()
    const interval = setInterval(fetch, refreshInterval)
    return () => clearInterval(interval)
  }, [fetch, refreshInterval])

  return { data, loading, refetch: fetch }
}
