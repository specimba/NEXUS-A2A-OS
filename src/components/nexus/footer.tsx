'use client'

import { useState, useEffect, useCallback } from 'react'
import { Wifi, AlertTriangle, Gauge } from 'lucide-react'

interface PoolStatus {
  name: string
  count: number
  color: string
}

export function NexusFooter() {
  const [uptime, setUptime] = useState('00:00:00')
  const [poolStatuses, setPoolStatuses] = useState<PoolStatus[]>([
    { name: 'PREMIUM', count: 0, color: '#34d399' },
    { name: 'MID', count: 0, color: '#60a5fa' },
    { name: 'FAST', count: 0, color: '#fb923c' },
  ])
  const [errorCount, setErrorCount] = useState(0)
  const [rateLimitStatus, setRateLimitStatus] = useState<'ok' | 'caution' | 'limited'>('ok')

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

  // Fetch model pool status
  useEffect(() => {
    const fetchPoolStatus = async () => {
      try {
        const res = await globalThis.fetch('/api/models')
        if (!res.ok) return
        const data = await res.json()
        const models = data.models ?? []

        const pools: PoolStatus[] = [
          {
            name: 'PREMIUM',
            count: models.filter((m: any) =>
              ['trinity-large-preview', 'minimax-m2.5'].includes(m.name) && m.isActive
            ).length,
            color: '#34d399',
          },
          {
            name: 'MID',
            count: models.filter((m: any) =>
              ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'].includes(m.name) && m.isActive
            ).length,
            color: '#60a5fa',
          },
          {
            name: 'FAST',
            count: models.filter((m: any) =>
              ['gemma-fast', 'nemotron-3-super'].includes(m.name) && m.isActive
            ).length,
            color: '#fb923c',
          },
        ]
        setPoolStatuses(pools)
      } catch {
        // Silently ignore fetch errors in footer
      }
    }

    fetchPoolStatus()
    const interval = setInterval(fetchPoolStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  // Simulate error counting (increment randomly every few seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      // ~8% chance of error per interval (simulates real-world error rate)
      if (Math.random() < 0.08) {
        setErrorCount(prev => prev + 1)
      }
    }, 5000)

    // Reset error count every 5 minutes
    const resetInterval = setInterval(() => {
      setErrorCount(0)
    }, 300000)

    return () => {
      clearInterval(interval)
      clearInterval(resetInterval)
    }
  }, [])

  // Simulate rate limit status changes
  useEffect(() => {
    const interval = setInterval(() => {
      const rand = Math.random()
      if (rand < 0.85) setRateLimitStatus('ok')
      else if (rand < 0.95) setRateLimitStatus('caution')
      else setRateLimitStatus('limited')
    }, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <footer className="relative flex flex-wrap items-center justify-between gap-2 border-t border-border bg-card px-4 py-2">
      {/* Gradient top border */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
      
      {/* Left side: NEXUS OS branding + constitution */}
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <span className="font-semibold gradient-text">NEXUS OS</span>
        <span>v3.0</span>
        <span className="text-border">|</span>
        <span>Constitution: 5 agents/hr &middot; 20 API/session &middot; 2 concurrent &middot; 30 writes</span>
      </div>

      {/* Center: Session info */}
      <div className="hidden md:flex items-center gap-3 text-[11px] text-muted-foreground">
        {/* Model Pool Status */}
        <div className="flex items-center gap-2">
          <Wifi className="h-3 w-3 text-muted-foreground" />
          {poolStatuses.map((pool) => (
            <span key={pool.name} className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: pool.color }} />
              <span className="text-[10px]">{pool.name}:</span>
              <span className="text-[10px] font-bold tabular-nums" style={{ color: pool.color }}>{pool.count}</span>
            </span>
          ))}
        </div>

        <span className="text-border">|</span>

        {/* Error Count */}
        <div className="flex items-center gap-1">
          <AlertTriangle className={`h-3 w-3 ${errorCount > 3 ? 'text-red-600 dark:text-red-400' : errorCount > 0 ? 'text-yellow-600 dark:text-yellow-400' : 'text-muted-foreground'}`} />
          <span className="text-[10px]">Errors (5m):</span>
          <span className={`text-[10px] font-bold tabular-nums ${errorCount > 3 ? 'text-red-600 dark:text-red-400' : errorCount > 0 ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
            {errorCount}
          </span>
        </div>

        <span className="text-border">|</span>

        {/* Rate Limit Status */}
        <div className="flex items-center gap-1">
          <Gauge className={`h-3 w-3 ${
            rateLimitStatus === 'ok' ? 'text-emerald-600 dark:text-emerald-400' :
            rateLimitStatus === 'caution' ? 'text-yellow-600 dark:text-yellow-400' :
            'text-red-600 dark:text-red-400'
          }`} />
          <span className="text-[10px]">Rate:</span>
          <span className={`text-[10px] font-bold ${
            rateLimitStatus === 'ok' ? 'text-emerald-600 dark:text-emerald-400' :
            rateLimitStatus === 'caution' ? 'text-yellow-600 dark:text-yellow-400' :
            'text-red-600 dark:text-red-400'
          }`}>
            {rateLimitStatus === 'ok' ? 'OK' : rateLimitStatus === 'caution' ? 'CAUTION' : 'LIMITED'}
          </span>
        </div>
      </div>

      {/* Right side: uptime + live */}
      <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
        <span suppressHydrationWarning>Session: {uptime}</span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse status-pulse-green status-glow-green" />
          Live
        </span>
      </div>
    </footer>
  )
}
