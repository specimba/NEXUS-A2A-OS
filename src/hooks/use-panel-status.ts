'use client'

import { useEffect, useState } from 'react'

export interface PanelResult {
  relayed?: boolean
  source?: string
  brainApiStatus?: 'LIVE' | 'MOCK' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN' | string
  latencyMs?: number
  error?: string
}

export interface PanelStatusSnapshot {
  probedAt: string
  overall: 'LIVE' | 'MOCK' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'
  counts: Record<string, number>
  panels: Record<string, PanelResult>
}

let cache: PanelStatusSnapshot | null = null
let cacheTime = 0
let fetchPromise: Promise<PanelStatusSnapshot | null> | null = null
const CACHE_TTL_MS = 25_000
const listeners = new Set<(snapshot: PanelStatusSnapshot | null) => void>()

async function fetchPanelStatus(): Promise<PanelStatusSnapshot | null> {
  try {
    const response = await fetch('/api/panel-status', { cache: 'no-store' })
    if (!response.ok) return null
    return await response.json() as PanelStatusSnapshot
  } catch {
    return null
  }
}

function notify(snapshot: PanelStatusSnapshot | null) {
  for (const listener of listeners) listener(snapshot)
}

async function refreshIfNeeded(force = false): Promise<void> {
  const now = Date.now()
  if (!force && cache && now - cacheTime < CACHE_TTL_MS) return
  if (fetchPromise) {
    await fetchPromise
    return
  }

  fetchPromise = fetchPanelStatus()
  const result = await fetchPromise
  fetchPromise = null
  cache = result
  cacheTime = Date.now()
  notify(result)
}

export function usePanelStatus() {
  const [snapshot, setSnapshot] = useState<PanelStatusSnapshot | null>(cache)

  useEffect(() => {
    listeners.add(setSnapshot)
    refreshIfNeeded()
    const intervalId = setInterval(() => refreshIfNeeded(), 30_000)
    return () => {
      listeners.delete(setSnapshot)
      clearInterval(intervalId)
    }
  }, [])

  return {
    snapshot,
    overall: snapshot?.overall ?? 'UNKNOWN',
    counts: snapshot?.counts ?? {},
    getPanel: (key: string) => snapshot?.panels?.[key],
    refresh: () => refreshIfNeeded(true),
    lastRefresh: cacheTime > 0 ? new Date(cacheTime) : null,
  }
}
