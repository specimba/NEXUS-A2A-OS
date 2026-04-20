'use client'

import { useState, useEffect } from 'react'

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
    <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border bg-card px-4 py-2">
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <span className="font-semibold text-emerald-500">NEXUS OS</span>
        <span>v3.0</span>
        <span className="text-border">|</span>
        <span>Constitution: 5 agents/hr &middot; 20 API/session &middot; 2 concurrent &middot; 30 writes</span>
      </div>
      <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
        <span>Session: {uptime}</span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Live
        </span>
      </div>
    </footer>
  )
}
