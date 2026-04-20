'use client'

import { useState } from 'react'
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
} from 'lucide-react'
import { XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltipComponent, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { ExportButton } from '@/components/nexus/export-button'
import { toast } from 'sonner'

// Column headers for CSV export
const modelUsageColumnHeaders: Record<string, string> = {
  model: 'Model Name',
  tokens: 'Total Tokens',
  calls: 'API Calls',
  avgLatency: 'Avg Latency (ms)',
  cost: 'Cost ($)',
}

const hourlyUsage = [
  { hour: '08:00', tokens: 1200 },
  { hour: '09:00', tokens: 3400 },
  { hour: '10:00', tokens: 5600 },
  { hour: '11:00', tokens: 4800 },
  { hour: '12:00', tokens: 2100 },
  { hour: '13:00', tokens: 3800 },
  { hour: '14:00', tokens: 6200 },
  { hour: '15:00', tokens: 4500 },
  { hour: '16:00', tokens: 5100 },
  { hour: '17:00', tokens: 3200 },
]

const agentUsage = [
  { name: 'worker-3', tokens: 18600, pct: 25.3, trend: 'up' as const, model: 'qwen3-coder', color: COLORS.emerald },
  { name: 'worker-1', tokens: 12400, pct: 16.9, trend: 'up' as const, model: 'trinity-large', color: COLORS.blue },
  { name: 'coordinator', tokens: 8200, pct: 11.2, trend: 'down' as const, model: 'gemma-fast', color: COLORS.purple },
  { name: 'worker-2', tokens: 8200, pct: 11.2, trend: 'up' as const, model: 'nemotron-3', color: COLORS.orange },
  { name: 'research-agent', tokens: 5100, pct: 6.9, trend: 'down' as const, model: 'kimi-k2.5', color: COLORS.pink },
]

const modelUsage = [
  {
    model: 'gemma-fast',
    tokens: 22400,
    calls: 1024,
    avgLatency: 340,
    cost: 0,
    trend: [
      { name: '0', value: 2800 }, { name: '1', value: 3200 }, { name: '2', value: 2600 },
      { name: '3', value: 3800 }, { name: '4', value: 4200 }, { name: '5', value: 3400 },
      { name: '6', value: 3900 }, { name: '7', value: 4500 },
    ],
  },
  {
    model: 'trinity-large',
    tokens: 18200,
    calls: 512,
    avgLatency: 1350,
    cost: 0,
    trend: [
      { name: '0', value: 2400 }, { name: '1', value: 2000 }, { name: '2', value: 2800 },
      { name: '3', value: 2200 }, { name: '4', value: 2600 }, { name: '5', value: 3000 },
      { name: '6', value: 2800 }, { name: '7', value: 3200 },
    ],
  },
  {
    model: 'qwen3-coder',
    tokens: 15800,
    calls: 347,
    avgLatency: 1200,
    cost: 0,
    trend: [
      { name: '0', value: 1800 }, { name: '1', value: 2200 }, { name: '2', value: 2600 },
      { name: '3', value: 2000 }, { name: '4', value: 2400 }, { name: '5', value: 2800 },
      { name: '6', value: 2200 }, { name: '7', value: 2600 },
    ],
  },
  {
    model: 'nemotron-3',
    tokens: 8900,
    calls: 234,
    avgLatency: 890,
    cost: 0,
    trend: [
      { name: '0', value: 1200 }, { name: '1', value: 1000 }, { name: '2', value: 1400 },
      { name: '3', value: 1100 }, { name: '4', value: 1300 }, { name: '5', value: 1500 },
      { name: '6', value: 1200 }, { name: '7', value: 1000 },
    ],
  },
  {
    model: 'kimi-k2.5',
    tokens: 5400,
    calls: 156,
    avgLatency: 980,
    cost: 0,
    trend: [
      { name: '0', value: 800 }, { name: '1', value: 600 }, { name: '2', value: 900 },
      { name: '3', value: 700 }, { name: '4', value: 500 }, { name: '5', value: 800 },
      { name: '6', value: 600 }, { name: '7', value: 700 },
    ],
  },
  {
    model: 'gpt-oss-120b',
    tokens: 3200,
    calls: 298,
    avgLatency: 760,
    cost: 0,
    trend: [
      { name: '0', value: 400 }, { name: '1', value: 500 }, { name: '2', value: 300 },
      { name: '3', value: 600 }, { name: '4', value: 400 }, { name: '5', value: 500 },
      { name: '6', value: 350 }, { name: '7', value: 450 },
    ],
  },
]

const budgetAlerts = [
  { level: 'warning' as const, msg: 'worker-2 approaching rate limit (85% of hourly budget)', time: '5m ago' },
  { level: 'info' as const, msg: 'Session budget 73.4% consumed — 26,550 remaining', time: '1m ago' },
  { level: 'info' as const, msg: 'FREE_RESEARCH pool: all models within limits', time: '3m ago' },
]

// Heatmap data: 5 agents x 8 hours
const heatmapAgents = ['worker-3', 'worker-1', 'coordinator', 'worker-2', 'research-agent']
const heatmapHours = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']
const heatmapData: Record<string, number[]> = {
  'worker-3':      [4200, 5800, 3100, 4600, 6200, 5400, 4900, 3600],
  'worker-1':      [2800, 3600, 2200, 3100, 4200, 3800, 3200, 2400],
  'coordinator':   [1600, 2200, 1800, 2400, 2800, 2000, 1800, 1400],
  'worker-2':      [1400, 2600, 1200, 2200, 3800, 2800, 2400, 1800],
  'research-agent':[800,  1200, 600,  1000, 1600, 1200, 900,  600],
}
const heatmapMax = 6200

// Token Flow Sankey data
const flowModels = [
  { id: 'gemma-fast', tokens: 22400, color: COLORS.emerald },
  { id: 'trinity-large', tokens: 18200, color: COLORS.blue },
  { id: 'qwen3-coder', tokens: 15800, color: COLORS.orange },
  { id: 'nemotron-3', tokens: 8900, color: COLORS.purple },
  { id: 'kimi-k2.5', tokens: 5400, color: COLORS.pink },
  { id: 'gpt-oss-120b', tokens: 3200, color: COLORS.yellow },
]

const flowAgents = [
  { id: 'worker-3', tokens: 18600, color: COLORS.emerald },
  { id: 'worker-1', tokens: 12400, color: COLORS.blue },
  { id: 'coordinator', tokens: 8200, color: COLORS.purple },
  { id: 'worker-2', tokens: 8200, color: COLORS.orange },
  { id: 'research-agent', tokens: 5100, color: COLORS.pink },
]

const flowTasks = [
  { id: 'Code Gen', tokens: 24200, color: '#34d399' },
  { id: 'Research', tokens: 18600, color: '#60a5fa' },
  { id: 'Analysis', tokens: 14200, color: '#a78bfa' },
  { id: 'Review', tokens: 9800, color: '#fb923c' },
  { id: 'Testing', tokens: 6700, color: '#f472b6' },
]

// Flows: model → agent (left connections) and agent → task (right connections)
const modelToAgentFlows = [
  { from: 'gemma-fast', to: 'worker-3', volume: 8400 },
  { from: 'gemma-fast', to: 'worker-1', volume: 7200 },
  { from: 'gemma-fast', to: 'coordinator', volume: 4100 },
  { from: 'gemma-fast', to: 'worker-2', volume: 2700 },
  { from: 'trinity-large', to: 'worker-3', volume: 6200 },
  { from: 'trinity-large', to: 'worker-1', volume: 4800 },
  { from: 'trinity-large', to: 'research-agent', volume: 4200 },
  { from: 'trinity-large', to: 'coordinator', volume: 3000 },
  { from: 'qwen3-coder', to: 'worker-3', volume: 4000 },
  { from: 'qwen3-coder', to: 'worker-2', volume: 3800 },
  { from: 'qwen3-coder', to: 'coordinator', volume: 3200 },
  { from: 'qwen3-coder', to: 'worker-1', volume: 2800 },
  { from: 'qwen3-coder', to: 'research-agent', volume: 2000 },
  { from: 'nemotron-3', to: 'worker-2', volume: 3200 },
  { from: 'nemotron-3', to: 'coordinator', volume: 2900 },
  { from: 'nemotron-3', to: 'research-agent', volume: 2800 },
  { from: 'kimi-k2.5', to: 'research-agent', volume: 3200 },
  { from: 'kimi-k2.5', to: 'coordinator', volume: 2200 },
  { from: 'gpt-oss-120b', to: 'worker-2', volume: 1800 },
  { from: 'gpt-oss-120b', to: 'research-agent', volume: 1400 },
]

const agentToTaskFlows = [
  { from: 'worker-3', to: 'Code Gen', volume: 10200 },
  { from: 'worker-3', to: 'Research', volume: 4800 },
  { from: 'worker-3', to: 'Testing', volume: 3600 },
  { from: 'worker-1', to: 'Code Gen', volume: 6200 },
  { from: 'worker-1', to: 'Analysis', volume: 3800 },
  { from: 'worker-1', to: 'Review', volume: 2400 },
  { from: 'coordinator', to: 'Review', volume: 4600 },
  { from: 'coordinator', to: 'Analysis', volume: 2200 },
  { from: 'coordinator', to: 'Research', volume: 1400 },
  { from: 'worker-2', to: 'Research', volume: 5200 },
  { from: 'worker-2', to: 'Testing', volume: 1800 },
  { from: 'worker-2', to: 'Code Gen', volume: 1200 },
  { from: 'research-agent', to: 'Research', volume: 3200 },
  { from: 'research-agent', to: 'Analysis', volume: 1900 },
]

const maxFlowVolume = Math.max(...modelToAgentFlows.map(f => f.volume), ...agentToTaskFlows.map(f => f.volume))

function TokenFlowSankey() {
  return (
    <Card className="relative overflow-hidden border-emerald-600/20">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-emerald-400" /> Token Flow Sankey
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="grid grid-cols-3 gap-2">
          {/* Models Column */}
          <div className="space-y-1.5">
            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground text-center mb-2">Models</p>
            {flowModels.map((m) => (
              <div
                key={m.id}
                className="flex items-center gap-2 rounded-lg border border-border/50 bg-gradient-to-r from-muted/30 to-transparent px-2.5 py-2 hover:border-emerald-600/30 transition-colors"
              >
                <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                <span className="text-[11px] font-medium truncate flex-1">{m.id}</span>
                <span className="text-[10px] font-bold tabular-nums text-muted-foreground">{(m.tokens / 1000).toFixed(1)}k</span>
              </div>
            ))}
          </div>

          {/* Connections Column */}
          <div className="relative flex flex-col items-center justify-center">
            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground text-center mb-2">Flow</p>
            <div className="flex flex-col items-center gap-1 py-2">
              {/* Model→Agent flows */}
              <div className="flex flex-wrap items-center justify-center gap-0.5">
                {modelToAgentFlows.slice(0, 6).map((f, i) => (
                  <div
                    key={`ma-${i}`}
                    className="h-1 rounded-full bg-emerald-400"
                    style={{
                      width: `${Math.max(8, (f.volume / maxFlowVolume) * 40)}px`,
                      opacity: 0.2 + (f.volume / maxFlowVolume) * 0.6,
                    }}
                  />
                ))}
              </div>
              <ArrowRight className="h-4 w-4 text-emerald-400/50 my-1" />
              <div className="flex flex-wrap items-center justify-center gap-0.5">
                {agentToTaskFlows.slice(0, 6).map((f, i) => (
                  <div
                    key={`at-${i}`}
                    className="h-1 rounded-full bg-blue-400"
                    style={{
                      width: `${Math.max(8, (f.volume / maxFlowVolume) * 40)}px`,
                      opacity: 0.2 + (f.volume / maxFlowVolume) * 0.6,
                    }}
                  />
                ))}
              </div>
              <ArrowRight className="h-4 w-4 text-blue-400/50 my-1" />
            </div>
            <p className="text-[9px] text-muted-foreground text-center mt-1">Opacity = flow volume</p>
          </div>

          {/* Agents Column */}
          <div className="space-y-1.5">
            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground text-center mb-2">Agents → Tasks</p>
            {/* Show agents with their primary task destination */}
            {flowAgents.map((a) => {
              const primaryTask = agentToTaskFlows
                .filter(f => f.from === a.id)
                .sort((a, b) => b.volume - a.volume)[0]
              return (
                <div
                  key={a.id}
                  className="flex items-center gap-2 rounded-lg border border-border/50 bg-gradient-to-r from-muted/30 to-transparent px-2.5 py-2 hover:border-emerald-600/30 transition-colors"
                >
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: a.color }} />
                  <span className="text-[11px] font-medium truncate">{a.id}</span>
                  <span className="text-[9px] text-muted-foreground ml-auto shrink-0">→ {primaryTask?.to}</span>
                  <span className="text-[10px] font-bold tabular-nums text-muted-foreground shrink-0">{(a.tokens / 1000).toFixed(1)}k</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Task destination summary row */}
        <div className="mt-4 pt-3 border-t border-border/50">
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-2">Task Destinations</p>
          <div className="flex flex-wrap gap-2">
            {flowTasks.map((t) => (
              <div
                key={t.id}
                className="flex items-center gap-1.5 rounded-md border border-border/50 bg-muted/20 px-2.5 py-1.5"
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: t.color }} />
                <span className="text-[11px] font-medium">{t.id}</span>
                <span className="text-[10px] tabular-nums text-muted-foreground">{(t.tokens / 1000).toFixed(1)}k</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
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

function getHeatmapColor(value: number): string {
  if (value === 0) return 'transparent'
  const intensity = Math.min(value / heatmapMax, 1)
  if (intensity < 0.25) return 'rgba(52, 211, 153, 0.15)'
  if (intensity < 0.5) return 'rgba(52, 211, 153, 0.3)'
  if (intensity < 0.75) return 'rgba(52, 211, 153, 0.5)'
  return 'rgba(52, 211, 153, 0.75)'
}

function getImpactBadge(impact: 'high' | 'medium' | 'low') {
  if (impact === 'high') return <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px]">High</Badge>
  if (impact === 'medium') return <Badge className="bg-yellow-600/15 text-yellow-400 border-0 text-[9px]">Medium</Badge>
  return <Badge className="bg-muted text-muted-foreground border-0 text-[9px]">Low</Badge>
}

export function TokensTab() {
  const totalUsed = 73500
  const totalBudget = 100000
  const remaining = totalBudget - totalUsed
  const pct = (totalUsed / totalBudget) * 100
  const burnRate = 142 // tokens/min simulated

  const [dismissedAlerts, setDismissedAlerts] = useState<Set<number>>(new Set())

  const handleDismissAlert = (index: number) => {
    setDismissedAlerts(prev => new Set(prev).add(index))
    toast.success('Alert dismissed')
  }

  const handleApplySuggestion = (id: string, title: string) => {
    toast.success(`Optimization applied: ${title}`, {
      description: 'Changes will take effect on next session cycle',
    })
  }

  const visibleAlerts = budgetAlerts.filter((_, i) => !dismissedAlerts.has(i))

  return (
    <div className="space-y-6 p-6 grid-pattern">
      {/* Main Budget Card with Chart */}
      <Card className="relative overflow-hidden border-emerald-600/20">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
        <CardContent className="relative p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Session Token Budget</h2>
              <p className="text-sm text-muted-foreground">Current active session monitoring</p>
            </div>
            <Coins className="h-8 w-8 text-emerald-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-bold tabular-nums">{totalUsed.toLocaleString()}</span>
            <span className="text-lg text-muted-foreground mb-1">/ {totalBudget.toLocaleString()}</span>
          </div>
          {/* Burn rate indicator */}
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] gap-1">
              <TrendingUp className="h-3 w-3 text-red-400" />
              {burnRate.toLocaleString()} tok/min
            </Badge>
            <span className="text-[10px] text-muted-foreground">
              ~{Math.round(remaining / burnRate)} min remaining at current rate
            </span>
          </div>
          <Progress value={pct} className="mt-3 h-3" />
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>{pct.toFixed(1)}% used</span>
            <span className="text-emerald-400 font-medium">{remaining.toLocaleString()} remaining</span>
          </div>
          {/* Hourly usage chart */}
          <div className="mt-6">
            <p className="text-xs text-muted-foreground mb-2">Hourly Token Consumption</p>
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
                  }}
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

      {/* Token Flow Sankey */}
      <TokenFlowSankey />

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Per-Agent Breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <PieChartIcon className="h-4 w-4" /> Per-Agent Token Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {agentUsage.map((a) => (
                <div key={a.name} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: a.color }} />
                      <span className="text-sm font-medium">{a.name}</span>
                      <Badge variant="outline" className="text-[9px]">{a.model}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold tabular-nums">{a.tokens.toLocaleString()}</span>
                      {a.trend === 'up' ? (
                        <TrendingUp className="h-3 w-3 text-red-400" />
                      ) : (
                        <TrendingDown className="h-3 w-3 text-emerald-400" />
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Progress value={a.pct * 3.3} className="h-2 flex-1" />
                    <span className="text-[10px] text-muted-foreground w-8 tabular-nums">{a.pct}%</span>
                  </div>
                </div>
              ))}
            </div>
            {/* Agent usage bar chart */}
            <div className="mt-6">
              <NexusBarChart
                data={agentUsage.map(a => ({ name: a.name.split('-')[0], value: a.tokens }))}
                height={100}
              />
            </div>
          </CardContent>
        </Card>

        {/* Budget Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Budget Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2.5">
              {visibleAlerts.map((alert, i) => (
                <div
                  key={i}
                  className={`rounded-lg px-3 py-2.5 ${
                    alert.level === 'warning'
                      ? 'bg-yellow-600/10 border border-yellow-600/15'
                      : 'bg-accent/30 border border-border/50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {alert.level === 'warning' && <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-yellow-400" />}
                    {alert.level === 'info' && <Activity className="h-3.5 w-3.5 shrink-0 text-blue-400" />}
                    <span className="text-[11px] leading-snug flex-1">{alert.msg}</span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between">
                    <p className="text-[10px] text-muted-foreground">{alert.time}</p>
                    <div className="flex items-center gap-1">
                      {alert.level === 'warning' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-5 gap-1 text-[9px] text-yellow-400 hover:text-yellow-300 hover:bg-yellow-600/10 px-1.5"
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
                      <span className={l.used >= l.max ? 'text-red-400 font-medium' : ''}>{l.used} / {l.max}</span>
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
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Flame className="h-4 w-4" /> Token Usage Heatmap
            </CardTitle>
            <Badge variant="outline" className="text-[9px]">Last 8 hours</Badge>
          </div>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <TooltipProvider delayDuration={150}>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="p-1.5 text-left text-[10px] font-medium text-muted-foreground w-24">Agent</th>
                    {heatmapHours.map(h => (
                      <th key={h} className="p-1.5 text-center text-[10px] font-medium text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatmapAgents.map(agent => (
                    <tr key={agent}>
                      <td className="p-1.5 text-[11px] font-medium truncate">{agent}</td>
                      {heatmapData[agent]?.map((value, colIdx) => (
                        <td key={colIdx} className="p-1.5 text-center">
                          <ShadcnTooltip>
                            <TooltipTrigger asChild>
                              <div
                                className="mx-auto h-8 w-full max-w-[48px] rounded-md border border-border/30 transition-colors hover:border-emerald-500/40 cursor-default"
                                style={{ backgroundColor: getHeatmapColor(value) }}
                              />
                            </TooltipTrigger>
                            <TooltipContent side="top" className="text-[10px]">
                              <p className="font-medium">{agent}</p>
                              <p className="text-muted-foreground">{heatmapHours[colIdx]}: {value.toLocaleString()} tokens</p>
                            </TooltipContent>
                          </ShadcnTooltip>
                        </td>
                      ))}
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

      {/* Per-Model Usage with Sparklines */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Per-Model Token Consumption</CardTitle>
            <ExportButton data={modelUsage.map(({ trend, ...rest }) => rest)} filename="token-usage" columnHeaders={modelUsageColumnHeaders} />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[11px]">Model</TableHead>
                  <TableHead className="text-[11px]">Tokens</TableHead>
                  <TableHead className="text-[11px]">API Calls</TableHead>
                  <TableHead className="text-[11px]">Avg Latency</TableHead>
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
                    <TableCell className="text-xs">{m.avgLatency}ms</TableCell>
                    <TableCell className="text-xs text-emerald-400">${m.cost.toFixed(4)}</TableCell>
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
                        <Progress value={(m.tokens / totalUsed) * 100} className="h-1.5 flex-1" />
                        <span className="text-[10px] text-muted-foreground w-8 tabular-nums">{((m.tokens / totalUsed) * 100).toFixed(0)}%</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Cost Optimization Suggestions */}
      <Card className="border-emerald-600/20">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-400" /> Cost Optimization
            </CardTitle>
            <Badge variant="outline" className="text-[9px]">{optimizationSuggestions.length} suggestions</Badge>
          </div>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid gap-3 sm:grid-cols-2">
            {optimizationSuggestions.map((s) => (
              <div
                key={s.id}
                className="rounded-lg border border-border/50 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent p-3.5 hover:border-emerald-600/30 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Lightbulb className="h-3.5 w-3.5 shrink-0 text-yellow-400" />
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
                    className="h-7 gap-1 text-[10px] shrink-0 border-emerald-600/30 text-emerald-400 hover:bg-emerald-600/10 hover:text-emerald-300"
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
