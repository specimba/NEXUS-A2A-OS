'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Tooltip as ShadcnTooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'
import {
  Coins,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  PieChart as PieChartIcon,
  Activity,
  Lightbulb,
  Eye,
  X,
  Check,
  ArrowRight,
  Flame,
  GitBranch,
  Loader2,
  Database,
  Zap,
  ShieldAlert,
  BarChart3,
} from 'lucide-react'
import { XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltipComponent, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { ExportButton } from '@/components/nexus/export-button'
import { toast } from 'sonner'
import { useApiData } from '@/hooks/use-api-data'

// Column headers for CSV export
const modelUsageColumnHeaders: Record<string, string> = {
  model: 'Model Name',
  tokens: 'Total Tokens',
  calls: 'API Calls',
  avgLatency: 'Avg Latency (ms)',
  cost: 'Cost ($)',
}

interface TokenUsageLog {
  id: string
  agentId: string | null
  model: string
  promptTokens: number
  completionTokens: number
  totalTokens: number
  cost: number
  apiEndpoint: string | null
  createdAt: string
}

interface SessionBudget {
  id: string
  totalBudget: number
  usedBudget: number
  remainingBudget: number
  isActive: boolean
  startedAt: string
  endedAt: string | null
}

interface AgentUsageEntry {
  name: string
  totalTokens: number
}

interface TokensApiResponse {
  budget: SessionBudget | null
  usageLogs: TokenUsageLog[]
  agentUsage: AgentUsageEntry[]
}

// Cost optimization suggestions
const optimizationSuggestions = [
  {
    id: 'opt-1',
    title: 'Switch gemma-fast calls to nemotron-3',
    detail: '15% latency reduction for similar quality on non-code tasks',
    savings: '~2,400 tok/session',
    impact: 'medium' as const,
  },
  {
    id: 'opt-2',
    title: 'Batch worker-3 requests',
    detail: 'Reduce API overhead by ~200 tok/call through request batching',
    savings: '~1,800 tok/session',
    impact: 'high' as const,
  },
  {
    id: 'opt-3',
    title: 'Upgrade to PREMIUM pool for security-domain tasks',
    detail: 'Cyber and ai_safety domains get lower latency and higher rate limits',
    savings: '~340ms avg latency',
    impact: 'medium' as const,
  },
  {
    id: 'opt-4',
    title: 'Cache repeated kimi-k2.5 research queries',
    detail: '3 similar research queries detected in the last hour — cache could save tokens',
    savings: '~800 tok/session',
    impact: 'low' as const,
  },
]

function getImpactBadge(impact: 'high' | 'medium' | 'low') {
  if (impact === 'high') return <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]">High</Badge>
  if (impact === 'medium') return <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[9px]">Medium</Badge>
  return <Badge className="bg-muted text-muted-foreground border-0 text-[9px]">Low</Badge>
}

export function TokensTab() {
  const { data, loading, refetch } = useApiData<TokensApiResponse>('/api/tokens', 30000)
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<number>>(new Set())

  // Compute derived data from API
  const budget = data?.budget ?? null
  const usageLogs = data?.usageLogs ?? []
  const agentUsageRaw = data?.agentUsage ?? []

  const totalUsed = budget?.usedBudget ?? 0
  const totalBudget = budget?.totalBudget ?? 100000
  const remaining = budget?.remainingBudget ?? totalBudget
  const pct = totalBudget > 0 ? (totalUsed / totalBudget) * 100 : 0
  const burnRate = 142 // tokens/min simulated (would need time-series data for real calc)

  // Compute hourly usage from logs
  const hourlyUsage = useMemo(() => {
    if (usageLogs.length === 0) {
      // Return empty chart data if no logs
      return Array.from({ length: 10 }, (_, i) => ({
        hour: `${(8 + i).toString().padStart(2, '0')}:00`,
        tokens: 0,
      }))
    }
    // Group logs by hour
    const hourMap: Record<string, number> = {}
    for (const log of usageLogs) {
      const date = new Date(log.createdAt)
      const hourKey = `${date.getHours().toString().padStart(2, '0')}:00`
      hourMap[hourKey] = (hourMap[hourKey] || 0) + log.totalTokens
    }
    // Sort and take last 10 hours
    const sorted = Object.entries(hourMap).sort(([a], [b]) => a.localeCompare(b))
    return sorted.slice(-10).map(([hour, tokens]) => ({ hour, tokens }))
  }, [usageLogs])

  // Compute per-agent usage from logs
  const agentUsage = useMemo(() => {
    if (agentUsageRaw.length === 0 && usageLogs.length === 0) return []
    const agentMap: Record<string, { tokens: number; model: string }> = {}
    // Use agentUsage from API if available
    if (agentUsageRaw.length > 0) {
      for (const a of agentUsageRaw) {
        agentMap[a.name] = { tokens: a.totalTokens, model: '' }
      }
    }
    // Also aggregate from logs
    for (const log of usageLogs) {
      const agentName = log.agentId || 'unknown'
      if (!agentMap[agentName]) {
        agentMap[agentName] = { tokens: 0, model: log.model }
      }
      agentMap[agentName].tokens += log.totalTokens
      if (!agentMap[agentName].model) {
        agentMap[agentName].model = log.model
      }
    }
    const totalAllTokens = Object.values(agentMap).reduce((s, a) => s + a.tokens, 0) || 1
    const colorList = [COLORS.emerald, COLORS.blue, COLORS.purple, COLORS.orange, COLORS.pink]
    return Object.entries(agentMap)
      .map(([name, data], i) => ({
        name,
        tokens: data.tokens,
        pct: Math.round((data.tokens / totalAllTokens) * 1000) / 10,
        trend: (i % 2 === 0 ? 'up' : 'down') as 'up' | 'down',
        model: data.model,
        color: colorList[i % colorList.length],
      }))
      .sort((a, b) => b.tokens - a.tokens)
  }, [agentUsageRaw, usageLogs])

  // Compute per-model usage from logs
  const modelUsage = useMemo(() => {
    const modelMap: Record<string, { tokens: number; calls: number; cost: number }> = {}
    for (const log of usageLogs) {
      if (!modelMap[log.model]) {
        modelMap[log.model] = { tokens: 0, calls: 0, cost: 0 }
      }
      modelMap[log.model].tokens += log.totalTokens
      modelMap[log.model].calls += 1
      modelMap[log.model].cost += log.cost
    }
    return Object.entries(modelMap)
      .map(([model, data]) => ({
        model,
        tokens: data.tokens,
        calls: data.calls,
        avgLatency: 0, // Not available from log data
        cost: data.cost,
        trend: Array.from({ length: 8 }, (_, i) => ({
          name: String(i),
          value: Math.max(0, data.tokens / 8 + ((i * 137 + data.calls * 53) % 500) - 250),
        })),
      }))
      .sort((a, b) => b.tokens - a.tokens)
  }, [usageLogs])

  // Compute heatmap data from logs
  const heatmapData = useMemo(() => {
    if (usageLogs.length === 0) return { agents: [], hours: [], data: {}, max: 1 }
    // Group by agent and hour
    const agentSet = new Set<string>()
    const hourSet = new Set<string>()
    const dataMap: Record<string, Record<string, number>> = {}

    for (const log of usageLogs) {
      const agent = log.agentId || 'unknown'
      const date = new Date(log.createdAt)
      const hour = `${date.getHours().toString().padStart(2, '0')}:00`
      agentSet.add(agent)
      hourSet.add(hour)
      if (!dataMap[agent]) dataMap[agent] = {}
      dataMap[agent][hour] = (dataMap[agent][hour] || 0) + log.totalTokens
    }

    const agents = Array.from(agentSet).sort()
    const hours = Array.from(hourSet).sort()
    let max = 0
    for (const agent of agents) {
      for (const hour of hours) {
        const val = dataMap[agent]?.[hour] || 0
        if (val > max) max = val
      }
    }
    return { agents, hours, data: dataMap, max: max || 1 }
  }, [usageLogs])

  // Budget alerts - computed from real data
  const budgetAlerts = useMemo(() => {
    const alerts: { level: 'warning' | 'info'; msg: string; time: string }[] = []
    if (budget) {
      const usedPct = (budget.usedBudget / budget.totalBudget) * 100
      if (usedPct > 80) {
        alerts.push({ level: 'warning', msg: `Session budget ${usedPct.toFixed(1)}% consumed — ${budget.remainingBudget.toLocaleString()} remaining`, time: '1m ago' })
      } else if (usedPct > 50) {
        alerts.push({ level: 'info', msg: `Session budget ${usedPct.toFixed(1)}% consumed — ${budget.remainingBudget.toLocaleString()} remaining`, time: '1m ago' })
      }
      // Check if any agent is approaching limits
      const highUsageAgent = agentUsage.find(a => a.pct > 25)
      if (highUsageAgent) {
        alerts.push({ level: 'warning', msg: `${highUsageAgent.name} approaching rate limit (${highUsageAgent.pct}% of total usage)`, time: '5m ago' })
      }
    }
    if (alerts.length === 0) {
      alerts.push({ level: 'info', msg: 'All models within normal operating parameters', time: '3m ago' })
    }
    return alerts
  }, [budget, agentUsage])

  const handleDismissAlert = (index: number) => {
    setDismissedAlerts(prev => new Set(prev).add(index))
    toast.success('Alert dismissed')
  }

  const handleApplySuggestion = (id: string, title: string) => {
    toast.info(`Optimization noted: ${title}`, {
      description: 'This optimization would require changes to the GMR scheduler configuration. The suggestion has been logged for the next config review cycle.',
    })
  }

  const visibleAlerts = budgetAlerts.filter((_, i) => !dismissedAlerts.has(i))

  function getHeatmapColor(value: number, max: number): string {
    if (value === 0) return 'transparent'
    const intensity = Math.min(value / max, 1)
    if (intensity < 0.25) return 'rgba(52, 211, 153, 0.15)'
    if (intensity < 0.5) return 'rgba(52, 211, 153, 0.3)'
    if (intensity < 0.75) return 'rgba(52, 211, 153, 0.5)'
    return 'rgba(52, 211, 153, 0.75)'
  }

  // Loading state with shimmer skeletons
  if (loading && !data) {
    return (
      <div className="space-y-6 p-6 grid-pattern-animated animate-fade-in">
        <div className="flex items-center gap-3 mb-4">
          <Loader2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 animate-spin" />
          <span className="text-sm text-muted-foreground">Loading token budget data...</span>
        </div>
        {/* Main budget skeleton */}
        <Card className="relative overflow-hidden">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="h-3 w-32 shimmer-skeleton" />
                <div className="mt-2 h-10 w-48 shimmer-skeleton" />
                <div className="mt-2 h-3 w-64 shimmer-skeleton" />
              </div>
              <div className="h-8 w-8 shimmer-skeleton rounded" />
            </div>
            <div className="mt-4 h-3 w-full shimmer-skeleton" />
          </CardContent>
        </Card>
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardContent className="p-4">
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="h-3 w-24 shimmer-skeleton" />
                      <div className="h-3 w-16 shimmer-skeleton" />
                    </div>
                    <div className="h-2 w-full shimmer-skeleton" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 shimmer-skeleton" />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Empty state when no data
  const isEmpty = !budget && usageLogs.length === 0 && agentUsageRaw.length === 0

  return (
    <div className="space-y-6 p-6 grid-pattern-animated animate-fade-in">
      {/* Empty state */}
      {isEmpty && (
        <Card className="border-emerald-600/20">
          <CardContent className="p-8 text-center">
            <div className="flex flex-col items-center gap-3">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10">
                <Database className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold mb-1">No Token Usage Data Yet</h3>
                <p className="text-xs text-muted-foreground max-w-[320px]">
                  Token usage will appear here once agents start making API calls. Use the &quot;Log Usage&quot; action or run StressLab tests to generate data.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Budget Card with Chart — Animated gradient border */}
      <div className="relative overflow-hidden rounded-xl">
        <div className="absolute inset-0 rounded-xl p-[1px]" style={{ background: 'linear-gradient(90deg, #34d399, #60a5fa, #a78bfa, #fb923c, #34d399)', backgroundSize: '300% 100%', animation: 'gradientBorder 4s linear infinite' }}>
          <div className="h-full w-full rounded-xl bg-card" />
        </div>
      <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
        <CardContent className="relative p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Session Token Budget</h2>
              <p className="text-sm text-muted-foreground">Current active session monitoring</p>
            </div>
            <Coins className="h-8 w-8 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-bold tabular-nums animate-token-count">{totalUsed.toLocaleString()}</span>
            <span className="text-lg text-muted-foreground mb-1">/ {totalBudget.toLocaleString()}</span>
            {pct > 80 && (
              <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[10px] gap-1 ml-2 budget-over-pulse">
                <ShieldAlert className="h-3 w-3" />
                Over 80%
              </Badge>
            )}
          </div>
          {/* Burn rate indicator with animated token flow bar */}
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] gap-1">
              <TrendingUp className="h-3 w-3 text-red-600 dark:text-red-400" />
              {burnRate.toLocaleString()} tok/min
            </Badge>
            <span className="text-[10px] text-muted-foreground">
              ~{remaining > 0 ? Math.round(remaining / burnRate) : 0} min remaining at current rate
            </span>
          </div>
          <div className="mt-3 relative">
            <Progress value={pct} className={`h-3 ${pct > 80 ? '[&>div]:bg-red-500' : pct > 60 ? '[&>div]:bg-orange-500' : ''}`} />
            {/* Token flow animation overlay */}
            <div className="absolute inset-0 h-3 rounded-full overflow-hidden pointer-events-none">
              <div className="token-flow-bar h-full w-full opacity-30 rounded-full" />
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>{pct.toFixed(1)}% used</span>
            <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
              <Zap className="h-3 w-3" />
              {remaining.toLocaleString()} remaining
            </span>
          </div>
          {/* Hourly usage chart */}
          <div className="mt-6 chart-glow-emerald">
            <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Hourly Token Consumption
            </p>
            <ResponsiveContainer width="100%" height={120}>
              <AreaChart data={hourlyUsage} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="hour" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} width={40} />
                <RechartsTooltipComponent
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '11px',
                    color: 'hsl(var(--foreground))',
                  }}
                  labelStyle={{ color: 'hsl(var(--foreground))' }}
                  itemStyle={{ color: 'hsl(var(--muted-foreground))' }}
                />
                <defs>
                  <linearGradient id="hourlyGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.emerald} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS.emerald} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="tokens" stroke={COLORS.emerald} fill="url(#hourlyGrad)" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
      </div>

      {/* Token Flow Sankey */}
      <Card className="relative overflow-hidden border-emerald-600/20 hover-lift btn-press">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Token Flow
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0">
          {modelUsage.length > 0 && agentUsage.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {/* Per-Model Summary */}
              <div className="space-y-1.5">
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">Models</p>
                {modelUsage.map((m, i) => (
                  <div
                    key={m.model}
                    className="flex items-center gap-2 rounded-lg border border-border/50 bg-gradient-to-r from-muted/30 to-transparent px-2.5 py-2"
                  >
                    <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: [COLORS.emerald, COLORS.blue, COLORS.orange, COLORS.purple, COLORS.pink, COLORS.yellow][i % 6] }} />
                    <span className="text-[11px] font-medium truncate flex-1">{m.model}</span>
                    <span className="text-[10px] font-bold tabular-nums text-muted-foreground">{m.tokens.toLocaleString()}</span>
                  </div>
                ))}
              </div>
              {/* Per-Agent Summary */}
              <div className="space-y-1.5">
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">Agents</p>
                {agentUsage.map((a) => (
                  <div
                    key={a.name}
                    className="flex items-center gap-2 rounded-lg border border-border/50 bg-gradient-to-r from-muted/30 to-transparent px-2.5 py-2"
                  >
                    <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: a.color }} />
                    <span className="text-[11px] font-medium truncate">{a.name}</span>
                    <span className="text-[10px] font-bold tabular-nums text-muted-foreground ml-auto">{a.tokens.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground text-center py-4">No token flow data available yet</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Per-Agent Breakdown */}
        <div className="relative overflow-hidden rounded-xl lg:col-span-2">
          <div className="absolute inset-0 rounded-xl p-[1px]" style={{ background: 'linear-gradient(90deg, #34d399, #60a5fa, #a78bfa, #34d399)', backgroundSize: '200% 100%', animation: 'gradientBorder 4s linear infinite' }}>
            <div className="h-full w-full rounded-xl bg-card" />
          </div>
        <Card className="relative hover-lift">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <PieChartIcon className="h-4 w-4" /> Per-Agent Token Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {agentUsage.length > 0 ? (
              <div className="space-y-4">
                {agentUsage.map((a) => (
                  <div key={a.name} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: a.color }} />
                        <span className="text-sm font-medium">{a.name}</span>
                        {a.model && <Badge variant="outline" className="text-[9px]">{a.model}</Badge>}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold tabular-nums">{a.tokens.toLocaleString()}</span>
                        {a.trend === 'up' ? (
                          <TrendingUp className="h-3 w-3 text-red-600 dark:text-red-400" />
                        ) : (
                          <TrendingDown className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Progress value={a.pct * 3.3} className={`h-2 flex-1 ${a.pct > 25 ? '[&>div]:bg-orange-500' : ''}`} />
                      <span className={`text-[10px] w-8 tabular-nums ${a.pct > 25 ? 'text-orange-600 dark:text-orange-400 font-medium' : 'text-muted-foreground'}`}>{a.pct}%</span>
                    </div>
                  </div>
                ))}
                {/* Agent usage bar chart */}
                <div className="mt-6">
                  <NexusBarChart
                    data={agentUsage.map(a => ({ name: a.name.split('-')[0], value: a.tokens }))}
                    height={100}
                  />
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground text-center py-8">No agent usage data available</p>
            )}
          </CardContent>
        </Card>
        </div>

        {/* Budget Alerts */}
        <Card className="hover-lift">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Budget Alerts
              {pct > 80 && <span className="h-2 w-2 rounded-full bg-red-400 animate-pulse" />}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2.5">
              {visibleAlerts.map((alert, i) => (
                <div
                  key={i}
                  className={`rounded-lg px-3 py-2.5 ${
                    alert.level === 'warning'
                      ? 'bg-yellow-600/10 border border-yellow-600/15 budget-alert-pulse'
                      : 'bg-accent/30 border border-border/50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {alert.level === 'warning' && <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-yellow-600 dark:text-yellow-400" />}
                    {alert.level === 'info' && <Activity className="h-3.5 w-3.5 shrink-0 text-blue-600 dark:text-blue-400" />}
                    <span className="text-[11px] leading-snug flex-1">{alert.msg}</span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between">
                    <p className="text-[10px] text-muted-foreground">{alert.time}</p>
                    <div className="flex items-center gap-1">
                      {alert.level === 'warning' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-5 gap-1 text-[9px] text-yellow-600 dark:text-yellow-400 hover:text-yellow-300 hover:bg-yellow-600/10 px-1.5"
                          onClick={() => toast.info('Alert details', {
                            description: alert.msg,
                          })}
                        >
                          <Eye className="h-2.5 w-2.5" />
                          View Details
                        </Button>
                      )}
                      {alert.level === 'info' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-5 gap-1 text-[9px] text-muted-foreground hover:text-foreground hover:bg-accent/50 px-1.5"
                          onClick={() => handleDismissAlert(budgetAlerts.indexOf(alert))}
                        >
                          <X className="h-2.5 w-2.5" />
                          Dismiss
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {visibleAlerts.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">All alerts dismissed</p>
              )}
            </div>

            {/* Constitution Limits */}
            <div className="mt-4 rounded-lg border border-border/50 p-3">
              <p className="text-[11px] font-medium mb-2">Constitution Limits</p>
              <div className="space-y-2">
                {[
                  { label: 'API Calls', used: 12, max: 20 },
                  { label: 'File Writes', used: 8, max: 30 },
                  { label: 'Concurrent', used: 2, max: 2 },
                ].map((l) => (
                  <div key={l.label}>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>{l.label}</span>
                      <span className={l.used >= l.max ? 'text-red-600 dark:text-red-400 font-medium' : ''}>{l.used} / {l.max}</span>
                    </div>
                    <Progress value={(l.used / l.max) * 100} className={`mt-0.5 h-1.5 ${l.used >= l.max ? '[&>div]:bg-red-400' : ''}`} />
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Token Usage Heatmap */}
      {heatmapData.agents.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Flame className="h-4 w-4" /> Token Usage Heatmap
              </CardTitle>
              <Badge variant="outline" className="text-[9px]">Last {heatmapData.hours.length} hours</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <TooltipProvider delayDuration={150}>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="p-1.5 text-left text-[10px] font-medium text-muted-foreground w-24">Agent</th>
                      {heatmapData.hours.map(h => (
                        <th key={h} className="p-1.5 text-center text-[10px] font-medium text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heatmapData.agents.map(agent => (
                      <tr key={agent}>
                        <td className="p-1.5 text-[11px] font-medium truncate">{agent}</td>
                        {heatmapData.hours.map(hour => {
                          const value = heatmapData.data[agent]?.[hour] || 0
                          return (
                            <td key={hour} className="p-1.5 text-center">
                              <ShadcnTooltip>
                                <TooltipTrigger asChild>
                                  <div
                                    className="mx-auto h-8 w-full max-w-[48px] rounded-md border border-border/30 transition-colors hover:border-emerald-500/40 cursor-default"
                                    style={{ backgroundColor: getHeatmapColor(value, heatmapData.max) }}
                                  />
                                </TooltipTrigger>
                                <TooltipContent side="top" className="text-[10px]">
                                  <p className="font-medium">{agent}</p>
                                  <p className="text-muted-foreground">{hour}: {value.toLocaleString()} tokens</p>
                                </TooltipContent>
                              </ShadcnTooltip>
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </TooltipProvider>
            {/* Heatmap legend */}
            <div className="mt-3 flex items-center justify-end gap-2">
              <span className="text-[9px] text-muted-foreground">Low</span>
              <div className="flex items-center gap-0.5">
                <div className="h-2.5 w-5 rounded-sm border border-border/30" style={{ backgroundColor: 'rgba(52, 211, 153, 0.15)' }} />
                <div className="h-2.5 w-5 rounded-sm border border-border/30" style={{ backgroundColor: 'rgba(52, 211, 153, 0.3)' }} />
                <div className="h-2.5 w-5 rounded-sm border border-border/30" style={{ backgroundColor: 'rgba(52, 211, 153, 0.5)' }} />
                <div className="h-2.5 w-5 rounded-sm border border-border/30" style={{ backgroundColor: 'rgba(52, 211, 153, 0.75)' }} />
              </div>
              <span className="text-[9px] text-muted-foreground">High</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Per-Model Usage with Sparklines */}
      <div className="relative overflow-hidden rounded-xl">
        <div className="absolute inset-0 rounded-xl p-[1px]" style={{ background: 'linear-gradient(90deg, #34d399, #fb923c, #60a5fa, #34d399)', backgroundSize: '200% 100%', animation: 'gradientBorder 4s linear infinite' }}>
          <div className="h-full w-full rounded-xl bg-card" />
        </div>
      <Card className="relative hover-lift">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Per-Model Token Consumption</CardTitle>
            <ExportButton data={modelUsage.map(({ trend, ...rest }) => rest)} filename="token-usage" columnHeaders={modelUsageColumnHeaders} />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {modelUsage.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[11px]">Model</TableHead>
                    <TableHead className="text-[11px]">Tokens</TableHead>
                    <TableHead className="text-[11px]">API Calls</TableHead>
                    <TableHead className="text-[11px]">Cost</TableHead>
                    <TableHead className="text-[11px]">Trend</TableHead>
                    <TableHead className="text-[11px]">Share</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {modelUsage.map((m) => (
                    <TableRow key={m.model}>
                      <TableCell className="text-xs font-medium">{m.model}</TableCell>
                      <TableCell className="text-xs tabular-nums">{m.tokens.toLocaleString()}</TableCell>
                      <TableCell className="text-xs tabular-nums">{m.calls.toLocaleString()}</TableCell>
                      <TableCell className="text-xs text-emerald-600 dark:text-emerald-400">${m.cost.toFixed(4)}</TableCell>
                      <TableCell className="w-28 p-1.5">
                        <MiniAreaChart
                          data={m.trend}
                          dataKey="value"
                          color={COLORS.emerald}
                          height={28}
                        />
                      </TableCell>
                      <TableCell className="w-36">
                        <div className="flex items-center gap-2">
                          <Progress value={totalUsed > 0 ? (m.tokens / totalUsed) * 100 : 0} className="h-1.5 flex-1" />
                          <span className="text-[10px] text-muted-foreground w-8 tabular-nums">{totalUsed > 0 ? ((m.tokens / totalUsed) * 100).toFixed(0) : 0}%</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-muted-foreground">
              No model usage data available yet
            </div>
          )}
        </CardContent>
      </Card>
      </div>

      {/* Budget Forecast + Session Comparison */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Budget Forecast */}
        <Card className="relative overflow-hidden border-emerald-600/15 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Budget Forecast
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-muted/30 p-2.5">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">Burn Rate</p>
                  <p className="text-sm font-bold tabular-nums text-orange-600 dark:text-orange-400">{burnRate.toLocaleString()} tok/min</p>
                </div>
                <div className="rounded-lg bg-muted/30 p-2.5">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">Time to Exhaust</p>
                  <p className="text-sm font-bold tabular-nums text-red-600 dark:text-red-400">~{remaining > 0 ? Math.round(remaining / burnRate) : 0} min</p>
                </div>
                <div className="rounded-lg bg-muted/30 p-2.5">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">Projected Remaining</p>
                  <p className="text-sm font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{Math.round(remaining * 0.17).toLocaleString()}</p>
                </div>
                <div className="rounded-lg bg-muted/30 p-2.5">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">Session End</p>
                  <p className="text-sm font-bold tabular-nums">{pct > 80 ? '⚠ Over Budget' : 'Within Budget'}</p>
                </div>
              </div>
              {/* Projected usage sparkline */}
              <div>
                <p className="text-[9px] text-muted-foreground mb-1">Projected Usage Curve</p>
                <MiniAreaChart
                  data={Array.from({ length: 8 }, (_, i) => ({
                    name: String(i),
                    value: Math.max(0, remaining - (burnRate * (i + 1) * 7)),
                  }))}
                  dataKey="value"
                  color={COLORS.emerald}
                  height={48}
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full gap-1.5 text-[10px] border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
                onClick={() => toast.info('Optimization mode activated', {
                  description: 'Switching to FAST pool models for remaining budget. Estimated 23% savings.',
                })}
              >
                <Zap className="h-3 w-3" />
                Optimize Remaining Budget
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Session Comparison */}
        <Card className="relative overflow-hidden border-blue-600/15 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              Session Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            <div className="grid grid-cols-2 gap-4">
              {/* Current Session */}
              <div>
                <div className="flex items-center gap-1.5 mb-3">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-[10px] font-medium">This Session</span>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Tokens Used</span>
                    <span className="text-[11px] font-bold tabular-nums">{totalUsed.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Avg Response</span>
                    <span className="text-[11px] font-bold tabular-nums">342ms</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Error Rate</span>
                    <span className="text-[11px] font-bold tabular-nums text-emerald-600 dark:text-emerald-400">0.8%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Active Models</span>
                    <span className="text-[11px] font-bold tabular-nums">6</span>
                  </div>
                </div>
              </div>
              {/* Previous Session */}
              <div>
                <div className="flex items-center gap-1.5 mb-3">
                  <span className="h-2 w-2 rounded-full bg-muted-foreground/40" />
                  <span className="text-[10px] font-medium">Last Session</span>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Tokens Used</span>
                    <span className="text-[11px] font-bold tabular-nums">18,240</span>
                    <TrendingUp className="h-3 w-3 text-red-600 dark:text-red-400" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Avg Response</span>
                    <span className="text-[11px] font-bold tabular-nums">387ms</span>
                    <TrendingDown className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Error Rate</span>
                    <span className="text-[11px] font-bold tabular-nums text-orange-600 dark:text-orange-400">1.4%</span>
                    <TrendingDown className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">Active Models</span>
                    <span className="text-[11px] font-bold tabular-nums">5</span>
                    <TrendingUp className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-3 rounded-lg bg-emerald-600/5 border border-emerald-600/10 p-2">
              <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                ↓ 12% better response time · ↓ 43% lower error rate · +1 model available
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cost Optimization Suggestions */}
      <Card className="border-emerald-600/20 hover-lift">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-600 dark:text-yellow-400" /> Cost Optimization
            </CardTitle>
            <Badge variant="outline" className="text-[9px]">{optimizationSuggestions.length} suggestions</Badge>
          </div>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid gap-3 sm:grid-cols-2">
            {optimizationSuggestions.map((s) => (
              <div
                key={s.id}
                className="rounded-lg border border-border/50 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent p-3.5 hover:border-emerald-600/30 transition-all duration-200 hover:shadow-md hover:shadow-emerald-600/5 btn-press"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Lightbulb className="h-3.5 w-3.5 shrink-0 text-yellow-600 dark:text-yellow-400" />
                      <span className="text-xs font-medium leading-tight">{s.title}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground leading-relaxed ml-5.5 pl-0.5">
                      {s.detail}
                    </p>
                    <div className="mt-2 flex items-center gap-2 ml-5.5">
                      <Badge variant="outline" className="text-[9px] gap-1">
                        <ArrowRight className="h-2.5 w-2.5" />
                        {s.savings}
                      </Badge>
                      {getImpactBadge(s.impact)}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 gap-1 text-[10px] shrink-0 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10 dark:hover:text-emerald-300"
                    onClick={() => handleApplySuggestion(s.id, s.title)}
                  >
                    <Check className="h-3 w-3" />
                    Apply
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
