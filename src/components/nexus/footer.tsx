'use client'

import { useState, useEffect } from 'react'
import { Wifi, AlertTriangle, Gauge } from 'lucide-react'

export function NexusFooter() {
  const [uptime, setUptime] = useState('00:00:00')

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
            <span className="text-[10px] font-bold tabular-nums text-emerald-400">2</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
            <span className="text-[10px]">MID:</span>
            <span className="text-[10px] font-bold tabular-nums text-blue-400">3</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
            <span className="text-[10px]">FAST:</span>
            <span className="text-[10px] font-bold tabular-nums text-orange-400">2</span>
          </span>
        </div>

        <span className="text-border">|</span>

        {/* Error Count */}
        <div className="flex items-center gap-1">
          <AlertTriangle className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          <span className="text-[10px]">Errors (5m):</span>
          <span className="text-[10px] font-bold tabular-nums text-emerald-600 dark:text-emerald-400">0</span>
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
        <span className="text-[10px] text-muted-foreground/60">Powered by z-ai</span>
      </div>
    </footer>
  )
}
