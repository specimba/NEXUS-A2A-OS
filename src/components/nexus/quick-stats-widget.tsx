'use client'

import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, Coins, Users, Clock } from 'lucide-react'
import { useMediaQuery } from '@/hooks/use-media'
import { useApiData } from '@/hooks/use-api-data'

interface TokensApiResponse {
  budget: {
    id: string
    totalBudget: number
    usedBudget: number
    remainingBudget: number
    isActive: boolean
  } | null
  usageLogs: unknown[]
  agentUsage: { name: string; totalTokens: number }[]
}

export function QuickStatsWidget() {
  const [collapsed, setCollapsed] = useState(false)
  const [uptime, setUptime] = useState({ days: 0, hours: 3, minutes: 42 })
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const { data } = useApiData<TokensApiResponse>('/api/tokens', 60000)

  // Simulated uptime ticker
  useEffect(() => {
    const interval = setInterval(() => {
      setUptime((prev) => {
        const totalMinutes = prev.days * 1440 + prev.hours * 60 + prev.minutes + 1
        return {
          days: Math.floor(totalMinutes / 1440),
          hours: Math.floor((totalMinutes % 1440) / 60),
          minutes: totalMinutes % 60,
        }
      })
    }, 60000)
    return () => clearInterval(interval)
  }, [])

  // Token budget from API
  const tokenBudget = {
    used: data?.budget?.usedBudget ?? 45200,
    total: data?.budget?.totalBudget ?? 100000,
  }
  const tokenPercent = (tokenBudget.used / tokenBudget.total) * 100

  // Active agents from API
  const activeAgents = data?.agentUsage?.filter(a => a.totalTokens > 0).length ?? 3
  const totalAgents = data?.agentUsage?.length ?? 5

  // Hide on mobile
  if (!isDesktop) {
    return null
  }

  return (
    <div className="fixed bottom-16 left-4 z-40 hidden lg:block animate-slide-up">
      <div className="glass-card rounded-xl border border-border/40 shadow-xl overflow-hidden">
        {/* Header with collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Quick Stats
          </span>
          {collapsed ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>

        {/* Stats content */}
        {!collapsed && (
          <div className="px-3 pb-3 space-y-2.5 min-w-[200px]">
            {/* Token Budget */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px]">
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Coins className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                  Token Budget
                </span>
                <span className="tabular-nums font-medium">
                  <span className="text-emerald-600 dark:text-emerald-400">{(tokenBudget.total - tokenBudget.used).toLocaleString()}</span>
                  <span className="text-muted-foreground">/{tokenBudget.total.toLocaleString()}</span>
                </span>
              </div>
              <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-500"
                  style={{ width: `${tokenPercent}%` }}
                />
              </div>
            </div>

            {/* Active Agents */}
            <div className="flex items-center justify-between text-[10px]">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Users className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                Active Agents
              </span>
              <span className="tabular-nums font-medium">
                <span className="text-blue-600 dark:text-blue-400">{activeAgents}</span>
                <span className="text-muted-foreground">/{totalAgents}</span>
              </span>
            </div>

            {/* System Uptime */}
            <div className="flex items-center justify-between text-[10px]">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Clock className="h-3 w-3 text-purple-600 dark:text-purple-400" />
                System Uptime
              </span>
              <span className="tabular-nums font-medium text-purple-600 dark:text-purple-400">
                {uptime.days > 0 && `${uptime.days}d `}
                {uptime.hours}h {uptime.minutes}m
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
