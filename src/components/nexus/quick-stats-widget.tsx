'use client'

import { useState, useEffect, useMemo } from 'react'
import { ChevronDown, ChevronUp, Coins, Users, Clock, Activity, Wifi, WifiOff } from 'lucide-react'
import { useMediaQuery } from '@/hooks/use-media'
import { useApiData } from '@/hooks/use-api-data'

interface SystemApiResponse {
  overview?: {
    requestCount?: number
    activeConnections?: number
    systemStartTime?: string | null
    stats?: {
      tokenBudget?: { remaining: number; total: number; used: number; pct: number }
      activeAgents?: { total: number; busy: number; idle: number; error: number; max: number }
    }
    performanceMetrics?: {
      avgResponseTime: number
      errorRate: number
      throughput: number
    }
  }
}

export function QuickStatsWidget() {
  const [collapsed, setCollapsed] = useState(false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  // Fetch real data from /api/system with 15s refresh
  const { data: systemData } = useApiData<SystemApiResponse>('/api/system', 15000)

  // Token budget from system API
  const tokenBudget = useMemo(() => ({
    used: systemData?.overview?.stats?.tokenBudget?.used ?? 0,
    total: systemData?.overview?.stats?.tokenBudget?.total ?? 100000,
    remaining: systemData?.overview?.stats?.tokenBudget?.remaining ?? 100000,
    pct: systemData?.overview?.stats?.tokenBudget?.pct ?? 0,
  }), [systemData])

  const tokenPercent = tokenBudget.total > 0 ? (tokenBudget.used / tokenBudget.total) * 100 : 0

  // Active agents from system API
  const activeAgents = systemData?.overview?.stats?.activeAgents ?? { total: 0, busy: 0, idle: 0, error: 0, max: 5 }

  // Uptime from system API start time — derived from tick counter
  const [tick, setTick] = useState(0)

  // Tick every second for live uptime display
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  // Derive uptime values from tick + systemStartTime
  const uptime = useMemo(() => {
    // Use tick as dependency to trigger recalculation every second
    void tick
    const startTime = systemData?.overview?.systemStartTime
    if (!startTime) return { days: 0, hours: 0, minutes: 0, seconds: 0 }
    const start = new Date(startTime).getTime()
    if (isNaN(start)) return { days: 0, hours: 0, minutes: 0, seconds: 0 }
    const diff = Date.now() - start
    if (diff < 0) return { days: 0, hours: 0, minutes: 0, seconds: 0 }
    const totalSec = Math.floor(diff / 1000)
    const days = Math.floor(totalSec / 86400)
    const hours = Math.floor((totalSec % 86400) / 3600)
    const minutes = Math.floor((totalSec % 3600) / 60)
    const seconds = totalSec % 60
    return { days, hours, minutes, seconds }
  }, [tick, systemData?.overview?.systemStartTime])

  // Request count and active connections
  const requestCount = systemData?.overview?.requestCount ?? 0
  const activeConnections = systemData?.overview?.activeConnections ?? 0

  // Performance metrics
  const throughput = systemData?.overview?.performanceMetrics?.throughput ?? 0
  const errorRate = systemData?.overview?.performanceMetrics?.errorRate ?? 0

  // Connection status
  const isLive = !!systemData

  // Hide on mobile
  if (!isDesktop) {
    return null
  }

  return (
    <div className="fixed bottom-16 left-4 z-40 hidden lg:block animate-slide-up">
      <div className="glass-card rounded-xl border border-border/40 shadow-xl overflow-hidden min-w-[220px]">
        {/* Header with collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-orange-400'} transition-colors`} />
            Quick Stats
            <span className={`text-[8px] font-bold tracking-wider px-1 py-0 rounded ${isLive ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-orange-600/15 text-orange-600 dark:text-orange-400'}`}>
              {isLive ? 'LIVE' : 'OFFLINE'}
            </span>
          </span>
          {collapsed ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>

        {/* Stats content */}
        {!collapsed && (
          <div className="px-3 pb-3 space-y-2.5">
            {/* Token Budget */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px]">
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Coins className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                  Token Budget
                </span>
                <span className="tabular-nums font-medium">
                  <span className="text-emerald-600 dark:text-emerald-400">{tokenBudget.remaining.toLocaleString()}</span>
                  <span className="text-muted-foreground">/{tokenBudget.total.toLocaleString()}</span>
                </span>
              </div>
              <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-500"
                  style={{ width: `${tokenPercent}%` }}
                />
              </div>
              <p className="text-[9px] text-muted-foreground tabular-nums">{tokenBudget.pct.toFixed(1)}% used</p>
            </div>

            {/* Active Agents */}
            <div className="flex items-center justify-between text-[10px]">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Users className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                Active Agents
              </span>
              <span className="tabular-nums font-medium">
                <span className="text-blue-600 dark:text-blue-400">{activeAgents.busy}</span>
                <span className="text-muted-foreground"> busy · </span>
                <span className="text-muted-foreground">{activeAgents.idle} idle</span>
              </span>
            </div>

            {/* System Uptime */}
            <div className="flex items-center justify-between text-[10px]">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Clock className="h-3 w-3 text-purple-600 dark:text-purple-400" />
                Uptime
              </span>
              <span className="tabular-nums font-medium text-purple-600 dark:text-purple-400">
                {uptime.days > 0 && `${uptime.days}d `}
                {uptime.hours}h {uptime.minutes}m
              </span>
            </div>

            {/* Throughput */}
            <div className="flex items-center justify-between text-[10px]">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Activity className="h-3 w-3 text-orange-600 dark:text-orange-400" />
                Throughput
              </span>
              <span className="tabular-nums font-medium text-orange-600 dark:text-orange-400">
                {throughput} req/min
              </span>
            </div>

            {/* Error Rate */}
            <div className="flex items-center justify-between text-[10px]">
              <span className="flex items-center gap-1 text-muted-foreground">
                {errorRate < 1 ? (
                  <Wifi className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <WifiOff className="h-3 w-3 text-red-600 dark:text-red-400" />
                )}
                Error Rate
              </span>
              <span className={`tabular-nums font-medium ${errorRate < 1 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                {errorRate}%
              </span>
            </div>

            {/* Requests today */}
            <div className="flex items-center justify-between text-[10px]">
              <span className="flex items-center gap-1 text-muted-foreground">
                <span className="h-3 w-3 flex items-center justify-center text-emerald-600 dark:text-emerald-400">⬡</span>
                Requests (24h)
              </span>
              <span className="tabular-nums font-medium text-emerald-600 dark:text-emerald-400">
                {requestCount.toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
