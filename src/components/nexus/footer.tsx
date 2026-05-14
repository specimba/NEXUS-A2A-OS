'use client'

import { useState, useEffect, useRef } from 'react'
import { Wifi, AlertTriangle, Gauge, Network, Heart, Clock, RefreshCw, Download, Terminal, Cpu, HardDrive, Zap } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

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

/** Animated counter component with smooth number transitions */
function AnimatedNumber({ value }: { value: string | number }) {
  return (
    <motion.span
      key={String(value)}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="inline-block tabular-nums"
    >
      {value}
    </motion.span>
  )
}

/** Mini usage bar for CPU/Memory */
function MiniUsageBar({ label, value, icon }: {
  label: string
  value: number
  icon: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-[9px] text-muted-foreground w-6 uppercase">{label}</span>
      <div className="h-1 w-12 rounded-full bg-muted overflow-hidden">
        <motion.div
          className={cn('h-full rounded-full', value > 80 ? 'bg-red-500' : value > 60 ? 'bg-yellow-500' : 'bg-emerald-500')}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className={cn(
        'text-[9px] font-bold tabular-nums w-7 text-right',
        value > 80 ? 'text-red-500' : value > 60 ? 'text-yellow-500' : 'text-emerald-600 dark:text-emerald-400'
      )}>
        {value}%
      </span>
    </div>
  )
}

export function NexusFooter() {
  const [uptime, setUptime] = useState('00:00:00')
  const [clock, setClock] = useState('')
  const [relayStatus, setRelayStatus] = useState<RelayStatus | null>(null)
  const startTimeRef = useRef(Date.now())

  // Simulated system metrics
  const [cpuUsage, setCpuUsage] = useState(34)
  const [memUsage, setMemUsage] = useState(58)
  const [networkLatency, setNetworkLatency] = useState(42)
  const [lastIncidentAgo, setLastIncidentAgo] = useState('2h 14m ago')

  // Real-time clock
  useEffect(() => {
    const updateClock = () => {
      setClock(
        new Date().toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      )
    }
    updateClock()
    const interval = setInterval(updateClock, 1000)
    return () => clearInterval(interval)
  }, [])

  // Session uptime counter
  useEffect(() => {
    const update = () => {
      const diff = Date.now() - startTimeRef.current
      const h = Math.floor(diff / 3600000).toString().padStart(2, '0')
      const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0')
      const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0')
      setUptime(`${h}:${m}:${s}`)
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  // Simulate CPU/Memory fluctuation
  useEffect(() => {
    const interval = setInterval(() => {
      setCpuUsage(prev => Math.min(95, Math.max(10, prev + Math.floor(Math.random() * 9) - 4)))
      setMemUsage(prev => Math.min(90, Math.max(30, prev + Math.floor(Math.random() * 5) - 2)))
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  // Simulate network latency fluctuation
  useEffect(() => {
    const interval = setInterval(() => {
      setNetworkLatency(prev => Math.min(200, Math.max(15, prev + Math.floor(Math.random() * 21) - 10)))
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  // Simulate last incident countdown
  useEffect(() => {
    const incidentTime = Date.now() - (2 * 3600000 + 14 * 60000) // 2h14m ago
    const interval = setInterval(() => {
      const diff = Date.now() - incidentTime
      const hours = Math.floor(diff / 3600000)
      const minutes = Math.floor((diff % 3600000) / 60000)
      setLastIncidentAgo(`${hours}h ${minutes}m ago`)
    }, 60000)
    return () => clearInterval(interval)
  }, [])

  // Client-side data — no API call needed
  useEffect(() => {
    // Static mock data replacing fetch('/api/modelrelay/status')
    setRelayStatus({
      availableProviders: 13,
      totalModels: 24,
      freeModels: 18,
      activeStrategy: 'quota_aware',
      statistics: {
        totalRequests: 1247,
        successfulRequests: 1234,
        failedRequests: 0,
      },
    })
  }, [])

  const poolPremium = 2 // From ModelRelay config: zai, nvidia premium models
  const poolMid = 7 // openrouter, sambanova, deepseek, fireworks, etc.
  const poolFast = 4 // groq, cerebras
  const errorCount = relayStatus?.statistics?.failedRequests || 0

  // Quick action handlers
  const handleRefresh = () => {
    window.dispatchEvent(new CustomEvent('nexus:refresh-all'))
  }

  const handleExport = () => {
    // Use the nexus store export dialog
    window.dispatchEvent(new CustomEvent('nexus:open-export'))
  }

  const handleTerminal = () => {
    // Navigate to AI chat tab
    window.dispatchEvent(new CustomEvent('nexus:open-terminal'))
  }

  // Latency color
  const latencyColor = networkLatency > 100 ? 'text-red-500' : networkLatency > 60 ? 'text-yellow-500' : 'text-emerald-600 dark:text-emerald-400'

  return (
    <TooltipProvider delayDuration={300}>
      <footer className="relative flex flex-wrap items-center justify-between gap-2 border-t border-border bg-card px-4 py-2">
        {/* Gradient top border */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />

        {/* Left side: branding + constitution */}
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className="font-semibold text-emerald-600 dark:text-emerald-400">NEXUS OS v3.1</span>
          <span className="hidden sm:inline">— Cloud Intelligence Dashboard</span>
          <span className="text-border">|</span>
          <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
            <Heart className="h-3 w-3 fill-emerald-500/80 animate-pulse" />
            Operational
          </span>
          <span className="text-border">|</span>
          <span className="hidden md:inline">Constitution: 5 agents/hr &middot; 20 API/session &middot; 2 concurrent &middot; 30 writes</span>
        </div>

        {/* Center: System metrics */}
        <div className="hidden md:flex items-center gap-3 text-[11px] text-muted-foreground">
          {/* CPU / Memory bars */}
          <div className="flex flex-col gap-0.5">
            <MiniUsageBar label="CPU" value={cpuUsage} icon={<Cpu className="h-2.5 w-2.5" />} />
            <MiniUsageBar label="MEM" value={memUsage} icon={<HardDrive className="h-2.5 w-2.5" />} />
          </div>

          <span className="text-border">|</span>

          {/* Real-time clock */}
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <span className="font-mono text-[10px] tabular-nums">{clock}</span>
          </div>

          <span className="text-border">|</span>

          {/* Model Pool Status */}
          <div className="flex items-center gap-2">
            <Wifi className="h-3 w-3 text-muted-foreground" />
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span className="text-[10px]">PREMIUM:</span>
              <span className="text-[10px] font-bold tabular-nums text-emerald-400">
                <AnimatedNumber value={poolPremium} />
              </span>
            </span>
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
              <span className="text-[10px]">MID:</span>
              <span className="text-[10px] font-bold tabular-nums text-blue-400">
                <AnimatedNumber value={poolMid} />
              </span>
            </span>
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
              <span className="text-[10px]">FAST:</span>
              <span className="text-[10px] font-bold tabular-nums text-orange-400">
                <AnimatedNumber value={poolFast} />
              </span>
            </span>
          </div>

          <span className="text-border">|</span>

          {/* ModelRelay Status */}
          <div className="flex items-center gap-1">
            <Network className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            <span className="text-[10px]">Relay:</span>
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
              <AnimatePresence mode="wait">
                <AnimatedNumber value={relayStatus ? `${relayStatus.availableProviders} providers` : '...'} />
              </AnimatePresence>
            </span>
            <span className="text-[10px] text-muted-foreground">
              &middot; <AnimatedNumber value={relayStatus?.totalModels || '—'} /> models
            </span>
          </div>

          <span className="text-border">|</span>

          {/* Error Count */}
          <div className="flex items-center gap-1">
            <AlertTriangle className={cn('h-3 w-3', errorCount > 0 ? 'text-red-500' : 'text-emerald-600 dark:text-emerald-400')} />
            <span className="text-[10px]">Errors:</span>
            <span className={cn('text-[10px] font-bold tabular-nums', errorCount > 0 ? 'text-red-500' : 'text-emerald-600 dark:text-emerald-400')}>
              <AnimatePresence mode="wait">
                <AnimatedNumber value={errorCount} />
              </AnimatePresence>
            </span>
          </div>

          <span className="text-border">|</span>

          {/* Network Latency */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 cursor-default">
                <Zap className={cn('h-3 w-3', latencyColor)} />
                <span className="text-[10px]">Ping:</span>
                <span className={cn('text-[10px] font-bold tabular-nums', latencyColor)}>
                  <AnimatePresence mode="wait">
                    <AnimatedNumber value={networkLatency} />
                  </AnimatePresence>
                  ms
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent>Network latency to gateway (simulated)</TooltipContent>
          </Tooltip>
        </div>

        {/* Right side: uptime, last incident, quick actions, live */}
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          {/* Last incident */}
          <span className="hidden lg:flex items-center gap-1 text-[10px]">
            <AlertTriangle className="h-3 w-3 text-yellow-500/70" />
            <span>Last incident:</span>
            <span className="font-medium text-yellow-600 dark:text-yellow-400">{lastIncidentAgo}</span>
          </span>

          <span className="hidden lg:inline text-border">|</span>

          {/* Quick action buttons */}
          <div className="hidden sm:flex items-center gap-0.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-emerald-600 dark:hover:text-emerald-400"
                  onClick={handleRefresh}
                >
                  <RefreshCw className="h-3 w-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Refresh Data</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-emerald-600 dark:hover:text-emerald-400"
                  onClick={handleExport}
                >
                  <Download className="h-3 w-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Export Data</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-emerald-600 dark:hover:text-emerald-400"
                  onClick={handleTerminal}
                >
                  <Terminal className="h-3 w-3" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Open Terminal</TooltipContent>
            </Tooltip>
          </div>

          <span className="text-border">|</span>

          {/* Session uptime - monospace HH:MM:SS */}
          <span className="font-mono text-[10px] tabular-nums" suppressHydrationWarning>
            Session: <AnimatedNumber value={uptime} />
          </span>

          <span className="text-border">|</span>

          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 pulse-dot" />
            Live
          </span>
          <span className="text-border">|</span>
          <span className="text-[10px] text-muted-foreground/60">z-ai SDK</span>
        </div>
      </footer>
    </TooltipProvider>
  )
}
