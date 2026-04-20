'use client'

import { useNexusStore } from '@/store/nexus-store'
import { Moon, Sun, Menu, Activity } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useEffect, useRef, useState } from 'react'

const tabTitles: Record<string, string> = {
  overview: 'System Overview',
  stresslab: 'StressLab Arena',
  gmr: 'GMR Router Panel',
  governor: 'Governor Dashboard',
  vault: 'Vault Browser',
  research: 'Research Pipeline',
  swarm: 'Swarm Monitor',
  tokens: 'Token Budget',
}

export function NexusHeader() {
  const { activeTab, setSidebarOpen } = useNexusStore()
  const { setTheme } = useTheme()
  const [time, setTime] = useState('')

  useEffect(() => {
    const update = () =>
      setTime(new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="flex h-14 items-center gap-3 border-b border-border/60 bg-card/80 backdrop-blur-sm px-4">
      {/* Mobile menu trigger */}
      <Button variant="ghost" size="icon" className="h-8 w-8 md:hidden" onClick={() => setSidebarOpen(true)}>
        <Menu className="h-4 w-4" />
      </Button>

      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-foreground truncate">{tabTitles[activeTab] || 'NEXUS OS'}</h1>
      </div>

      {/* Token budget indicator */}
      <div className="hidden items-center gap-2 rounded-lg bg-gradient-to-r from-emerald-600/10 to-emerald-600/5 border border-emerald-600/10 px-3 py-1.5 sm:flex">
        <Activity className="h-3.5 w-3.5 text-emerald-400" />
        <span className="text-xs font-medium text-emerald-400">73,450</span>
        <span className="text-[10px] text-muted-foreground">/ 100,000</span>
      </div>

      {/* Active agents */}
      <Badge variant="outline" className="hidden gap-1.5 sm:flex text-[10px]">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        3 agents
      </Badge>

      {/* Clock */}
      <span className="hidden font-mono text-xs text-muted-foreground md:block tabular-nums">{time}</span>

      {/* Theme toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8"
        onClick={() => setTheme('dark')}
      >
        <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      </Button>
    </header>
  )
}
