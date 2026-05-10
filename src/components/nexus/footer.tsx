'use client'

import { useState, useEffect, useCallback } from 'react'
import { Wifi, AlertTriangle, Gauge, Network } from 'lucide-react'

interface RelayStatus {
  availableProviders: number
  totalModels: number
  freeModels: number
  activeStrategy: string
  statistics: {
    totalRequests: number
    successfulRequests: number
    failedRequests: number
  }
}

export function NexusFooter() {
  const [uptime, setUptime] = useState('00:00:00')
  const [relayStatus, setRelayStatus] = useState<RelayStatus | null>(null)

  useEffect(() => {
    const start = Date.now()
    const update = () => {
      const diff = Date.now() - start
      const h = Math.floor(diff / 3600000).toString().padStart(2, '0')
      const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0')
      const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0')
      setUptime(`${h}:${m}:${s}`)
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  const fetchRelayStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/modelrelay/status')
      if (res.ok) {
        const data = await res.json()
        setRelayStatus(data)
      }
    } catch {}
  }, [])

  useEffect(() => {
    const load = async () => { await fetchRelayStatus() }
    load()
    const interval = setInterval(fetchRelayStatus, 60000)
    return () => clearInterval(interval)
  }, [fetchRelayStatus])

  const poolPremium = 2 // From ModelRelay config: zai, nvidia premium models
  const poolMid = 7 // openrouter, sambanova, deepseek, fireworks, etc.
  const poolFast = 4 // groq, cerebras
  const errorCount = relayStatus?.statistics?.failedRequests || 0

  return (
    <footer className="relative flex flex-wrap items-center justify-between gap-2 border-t border-border bg-card px-4 py-2">
      {/* Gradient top border */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />

      {/* Left side: branding + constitution */}
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <span className="font-semibold text-emerald-600 dark:text-emerald-400">NEXUS OS v3.1</span>
        <span>— Cloud Intelligence Dashboard</span>
        <span className="text-border">|</span>
        <span>Constitution: 5 agents/hr &middot; 20 API/session &middot; 2 concurrent &middot; 30 writes</span>
      </div>

      {/* Center: Session info */}
      <div className="hidden md:flex items-center gap-3 text-[11px] text-muted-foreground">
        {/* Model Pool Status */}
        <div className="flex items-center gap-2">
          <Wifi className="h-3 w-3 text-muted-foreground" />
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="text-[10px]">PREMIUM:</span>
            <span className="text-[10px] font-bold tabular-nums text-emerald-400">{poolPremium}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
            <span className="text-[10px]">MID:</span>
            <span className="text-[10px] font-bold tabular-nums text-blue-400">{poolMid}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
            <span className="text-[10px]">FAST:</span>
            <span className="text-[10px] font-bold tabular-nums text-orange-400">{poolFast}</span>
          </span>
        </div>

        <span className="text-border">|</span>

        {/* ModelRelay Status */}
        <div className="flex items-center gap-1">
          <Network className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          <span className="text-[10px]">Relay:</span>
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
            {relayStatus ? `${relayStatus.availableProviders} providers` : '...'}
          </span>
          <span className="text-[10px] text-muted-foreground">
            &middot; {relayStatus?.totalModels || '—'} models
          </span>
        </div>

        <span className="text-border">|</span>

        {/* Error Count */}
        <div className="flex items-center gap-1">
          <AlertTriangle className={cn('h-3 w-3', errorCount > 0 ? 'text-red-500' : 'text-emerald-600 dark:text-emerald-400')} />
          <span className="text-[10px]">Errors:</span>
          <span className={cn('text-[10px] font-bold tabular-nums', errorCount > 0 ? 'text-red-500' : 'text-emerald-600 dark:text-emerald-400')}>{errorCount}</span>
        </div>

        <span className="text-border">|</span>

        {/* Rate Limit Status */}
        <div className="flex items-center gap-1">
          <Gauge className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          <span className="text-[10px]">Rate:</span>
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">OK</span>
        </div>
      </div>

      {/* Right side: uptime + live */}
      <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
        <span suppressHydrationWarning>Session: {uptime}</span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Live
        </span>
        <span className="text-border">|</span>
        <span className="text-[10px] text-muted-foreground/60">z-ai SDK</span>
      </div>
    </footer>
  )
}

function cn(...inputs: (string | boolean | undefined | null)[]) {
  return inputs.filter(Boolean).join(' ')
}
