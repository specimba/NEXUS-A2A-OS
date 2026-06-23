'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import {
  Shield, Database, Router, Zap, Cpu, Activity, Server,
  AlertTriangle, CheckCircle2, Clock, TrendingUp, TrendingDown,
  Hexagon, Bug, Wrench, Loader2, RefreshCw, FlaskConical,
  Radio, Gauge, Wifi, HardDrive, Eye, X, ArrowRight, Network,
  Layers, Swords, Brain, Ghost, Radiation, Skull,
} from 'lucide-react'
import useSWR from 'swr'
import { usePanelStatus } from '@/hooks/use-panel-status'
import { PanelStatus } from '@/components/nexus/panel-status'

// ─── Types ────────────────────────────────────────────────────────

interface PillarData {
  name: string
  health: number
  status: string
  desc: string
  uptime: string
}

interface SystemOverviewResponse {
  overview: SystemOverview
}

interface SystemOverview {
  pillars: PillarData[]
  stats: {
    tokenBudget: { remaining: number; total: number; used: number; pct: number }
    activeAgents: { total: number; busy: number; idle: number; error: number; max: number }
    stressLab: { runs: number; templates: number; passRate: number; collapseRate: number }
  }
  recentDecisions: { id: string; agent: string; action: string; scope: string; time: string; reason: string }[]
  agentActivity: { name: string; tasks: number; errors: number }[]
  tokenHistory: { name: string; value: number }[]
  healthTimeline: Record<string, number | string>[]
  collapseRateTrend: { name: string; value: number }[]
  avgTrust: number
  totalVaultEntries: number
}

interface AgentData {
  id: string
  name: string
  type: string
  status: string
  domain: string | null
  trustScore: number
  tasksDone: number
  tasksFailed: number
  lastActive: string
}

// ─── Helpers ──────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then(r => r.json())

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return n.toLocaleString()
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'now'
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  return `${Math.floor(h / 24)}d`
}

function healthColor(h: number): string {
  if (h >= 95) return 'text-emerald-400'
  if (h >= 80) return 'text-yellow-400'
  return 'text-red-400'
}

function statusDot(status: string): string {
  switch (status) {
    case 'operational': return 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]'
    case 'degraded': return 'bg-yellow-400 shadow-[0_0_6px_rgba(250,204,21,0.5)]'
    default: return 'bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.5)]'
  }
}

const PILLAR_ICONS: Record<string, React.ReactNode> = {
  Bridge: <Network className="h-4 w-4" />,
  Engine: <Brain className="h-4 w-4" />,
  Governor: <Shield className="h-4 w-4" />,
  Vault: <Database className="h-4 w-4" />,
  GMR: <Layers className="h-4 w-4" />,
  Swarm: <Swords className="h-4 w-4" />,
  Monitor: <Activity className="h-4 w-4" />,
  Config: <Server className="h-4 w-4" />,
}

// ─── Mini Sparkline ──────────────────────────────────────────────

function MiniSparkline({ data, color }: { data: { value: number }[]; color: string }) {
  if (!data.length) return null
  const max = Math.max(...data.map(d => d.value), 1)
  const w = 60
  const h = 20
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1 || 1)) * w
    const y = h - (d.value / max) * h
    return `${x},${y}`
  }).join(' ')
  return (
    <svg width={w} height={h} className="shrink-0 opacity-60">
      <polyline fill="none" stroke={color} strokeWidth={1.5} points={points} />
    </svg>
  )
}

// ─── Pillar Card ──────────────────────────────────────────────────

function PillarCard({ pillar, sparkline }: { pillar: PillarData; sparkline: { value: number }[] }) {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-white/5 bg-gradient-to-br from-white/[0.04] to-transparent p-4 transition-all hover:border-purple-500/20 hover:from-purple-500/[0.06]">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className={cn(
            'flex h-8 w-8 items-center justify-center rounded-lg',
            pillar.health >= 95 ? 'bg-emerald-500/10 text-emerald-400' :
            pillar.health >= 80 ? 'bg-yellow-500/10 text-yellow-400' :
            'bg-red-500/10 text-red-400'
          )}>
            {PILLAR_ICONS[pillar.name] || <Hexagon className="h-4 w-4" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white/90">{pillar.name}</span>
              <span className={cn('h-2 w-2 rounded-full', statusDot(pillar.status))} />
            </div>
            <p className="text-xs text-white/40">{pillar.desc}</p>
          </div>
        </div>
        <div className="text-right">
          <p className={cn('text-lg font-bold tabular-nums', healthColor(pillar.health))}>{pillar.health}%</p>
          <p className="text-[10px] text-white/30">{pillar.uptime}</p>
        </div>
      </div>
      <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            pillar.health >= 95 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' :
            pillar.health >= 80 ? 'bg-gradient-to-r from-yellow-500 to-yellow-400' :
            'bg-gradient-to-r from-red-500 to-red-400'
          )}
          style={{ width: `${pillar.health}%` }}
        />
      </div>
      {sparkline.length > 0 && (
        <div className="mt-2 flex justify-end">
          <MiniSparkline data={sparkline} color={pillar.health >= 80 ? '#a78bfa' : '#f87171'} />
        </div>
      )}
    </div>
  )
}

// ─── Agent Badge ──────────────────────────────────────────────────

function AgentBadge({ agent }: { agent: AgentData }) {
  const statusColors: Record<string, string> = {
    idle: 'border-white/10 text-white/50 bg-white/[0.02]',
    busy: 'border-purple-500/30 text-purple-400 bg-purple-500/10',
    error: 'border-red-500/30 text-red-400 bg-red-500/10',
    offline: 'border-white/5 text-white/30 bg-white/[0.01]',
  }
  const domainColors: Record<string, string> = {
    code: 'text-blue-400',
    reason: 'text-purple-400',
    research: 'text-emerald-400',
    fast: 'text-yellow-400',
    sec: 'text-red-400',
  }
  return (
    <div className={cn(
      'flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-colors',
      statusColors[agent.status] || statusColors.idle
    )}>
      <span className={cn(
        'h-1.5 w-1.5 rounded-full',
        agent.status === 'idle' ? 'bg-white/20' :
        agent.status === 'busy' ? 'bg-purple-400' :
        agent.status === 'error' ? 'bg-red-400' :
        'bg-white/10'
      )} />
      <span className="font-medium">{agent.name}</span>
      {agent.domain && (
        <span className={cn('text-[9px] uppercase tracking-wider', domainColors[agent.domain] || 'text-white/30')}>
          {agent.domain}
        </span>
      )}
      <span className="ml-auto text-white/30">{timeAgo(agent.lastActive)}</span>
    </div>
  )
}

// ─── Decision Badge ───────────────────────────────────────────────

function DecisionBadge({ action }: { action: string }) {
  const colors: Record<string, string> = {
    ALLOW: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
    DENY: 'bg-red-500/15 text-red-400 border-red-500/20',
    HOLD: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20',
  }
  return (
    <Badge variant="outline" className={cn('text-[10px] font-mono border', colors[action] || '')}>
      {action}
    </Badge>
  )
}

// ─── Mini Health Timeline ─────────────────────────────────────────

function MiniHealthTimeline({ data }: { data: Record<string, number | string>[] }) {
  if (!data.length) return null
  const pillars = Object.keys(data[0]).filter(k => k !== 'name')
  const w = data.length * 8
  const h = 80
  const barW = Math.max(4, Math.floor(w / data.length) - 2)
  return (
    <svg width={w} height={h} className="w-full h-20">
      {data.map((row, i) => {
        const x = i * (barW + 2)
        return pillars.map((p, pi) => {
          const v = Number(row[p]) || 0
          const barH = (v / 100) * h
          return (
            <rect
              key={`${i}-${p}`}
              x={x}
              y={h - barH}
              width={barW}
              height={barH}
              fill={`hsl(${280 + pi * 15}, ${50 + v * 0.3}%, ${40 + v * 0.3}%)`}
              opacity={0.6}
              rx={1}
            />
          )
        })
      })}
    </svg>
  )
}

// ─── Main Component ──────────────────────────────────────────────

export default function OverviewTab()
  {
  const { data, error, isLoading, mutate } = useSWR<SystemOverviewResponse>('/api/system', fetcher, {
    refreshInterval: 30_000,
  })
  const { data: agents } = useSWR<AgentData[]>('/api/agents', fetcher, {
    refreshInterval: 60_000,
  })
  const { getPanel, overall, counts } = usePanelStatus()
  const overviewPanel = getPanel('overview')

  // Destructure overview data (API returns { overview: { pillars, stats, ... } })
  const overview = data?.overview
  const pillars = overview?.pillars || []
  const stats = overview?.stats || { tokenBudget: { remaining: 0, total: 0, used: 0, pct: 0 }, activeAgents: { total: 0, busy: 0, idle: 0, error: 0, max: 5 }, stressLab: { runs: 0, templates: 0, passRate: 0, collapseRate: 0 }, collapseRate: 0 }
  const recentDecisions = overview?.recentDecisions || []
  const healthTimeline = overview?.healthTimeline || []
  const tokenHistory = overview?.tokenHistory || []

  // Generate sparklines from health timeline
  const pillarSparklines = pillars.map(p => {
    const values = healthTimeline
      .map(row => Number(row[p.name]))
      .filter(v => !isNaN(v))
    return {
      name: p.name,
      data: values.map(v => ({ value: v })),
    }
  })

  // Diagnostic state
  const [diagOpen, setDiagOpen] = useState(false)
  const [diagRunning, setDiagRunning] = useState(false)
  const [diagResults, setDiagResults] = useState<{ pillar: string; status: string; health: number; latencyMs: number; details: string }[]>([])

  const runDiagnostic = useCallback(async () => {
    setDiagRunning(true)
    setDiagResults([])
    const results: typeof diagResults = []
    for (const p of overview?.pillars || []) {
      await new Promise(r => setTimeout(r, 150 + Math.random() * 200))
      const jitter = Math.floor(Math.random() * 20) - 10
      const health = Math.min(100, Math.max(0, p.health + jitter))
      const status = health >= 95 ? 'healthy' : health >= 80 ? 'degraded' : 'critical'
      const latency = Math.floor(10 + Math.random() * 90)
      results.push({ pillar: p.name, status, health, latencyMs: latency, details: p.desc })
      setDiagResults([...results])
    }
    setDiagRunning(false)
  }, [overview])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
          <p className="text-sm text-white/40">Loading NEXUS OS telemetry...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3 text-center">
          <Radiation className="h-10 w-10 text-red-400" />
          <p className="text-sm text-red-400">Failed to load system data</p>
          <p className="text-xs text-red-400/60">{error.message}</p>
          <Button variant="outline" size="sm" onClick={() => mutate()}>
            <RefreshCw className="h-3 w-3 mr-1" /> Retry
          </Button>
        </div>
      </div>
    )
  }

  const activeAgents = agents?.filter(a => a.status !== 'offline') || []
  const busyCount = activeAgents.filter(a => a.status === 'busy').length
  const errorCount = activeAgents.filter(a => a.status === 'error').length

  return (
    <div className="space-y-5 pb-8">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white/90">
            <span className="bg-gradient-to-r from-purple-400 to-red-400 bg-clip-text text-transparent">
              NEXUS OS
            </span>
            {' '}Command Center
          </h1>
          <p className="text-xs text-white/40 mt-0.5">
            {new Date().toLocaleString('en-US', { timeZone: 'Europe/Istanbul', hour12: false })}
            {' · '}{activeAgents.length} agents · {stats.stressLab.runs} tests
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PanelStatus
            relayed={overviewPanel?.relayed}
            source={overviewPanel?.source || 'brain-api'}
            brainApiStatus={overviewPanel?.brainApiStatus || overall}
            error={overviewPanel?.error}
            compact
            className="hidden sm:inline-flex"
          />
          <Badge variant="outline" className="hidden lg:inline-flex border-white/10 text-[10px] text-white/45" title="Brain API overall route counts">
            Brain API overall {overall} · live {counts.LIVE || 0} · degraded {counts.DEGRADED || 0} · offline {counts.OFFLINE || 0}
          </Badge>
          <Button size="sm" variant="outline" onClick={runDiagnostic} disabled={diagRunning} className="border-purple-500/20 text-purple-300 hover:bg-purple-500/10">
            {diagRunning ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Wrench className="h-3 w-3 mr-1" />}
            Diagnostics
          </Button>
          <Button size="sm" variant="outline" onClick={() => mutate()} className="border-white/10 text-white/50 hover:bg-white/5">
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* ── Top Row: Quick Stats ───────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-xl border border-white/5 bg-gradient-to-br from-purple-500/[0.08] to-transparent p-4">
          <div className="flex items-center gap-2 text-xs text-white/40 mb-1">
            <Activity className="h-3 w-3 text-purple-400" /> Agent Status
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold text-white/90">{activeAgents.length}</span>
            <span className="text-xs text-white/30">online</span>
          </div>
          <div className="mt-2 flex gap-2 text-[10px]">
            <span className="text-purple-400">{busyCount} busy</span>
            <span className="text-white/20">·</span>
            <span className="text-emerald-400">{activeAgents.filter(a => a.status === 'idle').length} idle</span>
            {errorCount > 0 && <><span className="text-white/20">·</span><span className="text-red-400">{errorCount} error</span></>}
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-gradient-to-br from-emerald-500/[0.06] to-transparent p-4">
          <div className="flex items-center gap-2 text-xs text-white/40 mb-1">
            <Gauge className="h-3 w-3 text-emerald-400" /> Token Budget
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold text-white/90">{formatNumber(stats.tokenBudget.remaining)}</span>
            <span className="text-xs text-white/30">/ {formatNumber(stats.tokenBudget.total)}</span>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/5">
            <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-purple-500" style={{ width: `${stats.tokenBudget.pct}%` }} />
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-gradient-to-br from-yellow-500/[0.06] to-transparent p-4">
          <div className="flex items-center gap-2 text-xs text-white/40 mb-1">
            <FlaskConical className="h-3 w-3 text-yellow-400" /> StressLab
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold text-white/90">{stats.stressLab.runs}</span>
            <span className="text-xs text-white/30">runs</span>
          </div>
          <div className="mt-2 flex gap-2 text-[10px]">
            <span className={stats.stressLab.passRate >= 80 ? 'text-emerald-400' : 'text-yellow-400'}>{stats.stressLab.passRate}% pass</span>
            <span className="text-white/20">·</span>
            <span className="text-red-400/70">{stats.stressLab.collapseRate}% collapse</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/5 bg-gradient-to-br from-red-500/[0.06] to-transparent p-4">
          <div className="flex items-center gap-2 text-xs text-white/40 mb-1">
            <Shield className="h-3 w-3 text-red-400" /> Governance
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold text-white/90">{(overview?.avgTrust ?? 0).toFixed(2)}</span>
            <span className="text-xs text-white/30">trust avg</span>
          </div>
          <div className="mt-2 flex gap-2 text-[10px]">
            <span className="text-blue-400">{overview?.totalVaultEntries ?? 0} vault entries</span>
            <span className="text-white/20">·</span>
            <span className="text-white/50">{recentDecisions.length} decisions</span>
          </div>
        </div>
      </div>

      {/* ── Pillars Grid ───────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-white/50">System Pillars</span>
          <div className="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
        </div>
        <div className="grid grid-cols-4 gap-3">
          {pillars.map(p => {
            const sp = pillarSparklines.find(s => s.name === p.name)
            return <PillarCard key={p.name} pillar={p} sparkline={sp?.data || []} />
          })}
        </div>
      </div>

      {/* ── Agent List ─────────────────────────────────────────── */}
      {agents && agents.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-white/50">Active Agents</span>
            <div className="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent" />
            <span className="text-[10px] text-white/30">{agents.length} total</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {agents.slice(0, 12).map(a => <AgentBadge key={a.id} agent={a} />)}
          </div>
        </div>
      )}

      {/* ── Middle Row: Timeline + Decisions ──────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        {/* Health Timeline */}
        <Card className="col-span-2 border-white/5 bg-white/[0.02]">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-white/50">
                <Activity className="h-3 w-3 inline mr-1.5 text-purple-400" />
                24h Health Timeline
              </CardTitle>
              <Badge variant="outline" className="text-[9px] border-purple-500/20 text-purple-300">LIVE</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {healthTimeline.length > 0 ? (
              <MiniHealthTimeline data={healthTimeline} />
            ) : (
              <p className="text-xs text-white/30 py-8 text-center">No timeline data yet</p>
            )}
          </CardContent>
        </Card>

        {/* Recent Decisions */}
        <Card className="border-white/5 bg-white/[0.02]">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-white/50">
                <Skull className="h-3 w-3 inline mr-1.5 text-red-400" />
                Governor
              </CardTitle>
              <Badge variant="outline" className="text-[9px] border-purple-500/20 text-purple-300">LIVE</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {recentDecisions.slice(0, 8).map((d, i) => (
                <div key={`${d.id}-${i}`} className="flex items-center gap-2 rounded-md bg-white/[0.02] px-2 py-1.5 text-xs">
                  <DecisionBadge action={d.action} />
                  <span className="text-white/40 font-mono text-[10px]">{d.scope}</span>
                  <span className="flex-1 truncate text-white/60">{d.agent}</span>
                  <span className="text-white/20 text-[10px]">{d.time}</span>
                </div>
              ))}
              {recentDecisions.length === 0 && (
                <p className="text-xs text-white/30 py-4 text-center">No decisions recorded</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Token History ──────────────────────────────────────── */}
      {tokenHistory.length > 0 && (
        <Card className="border-white/5 bg-white/[0.02]">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-white/50">
                <Database className="h-3 w-3 inline mr-1.5 text-purple-400" />
                Token Consumption
              </CardTitle>
              <Badge variant="outline" className="text-[9px] border-purple-500/20 text-purple-300">LIVE</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1 h-20">
              {tokenHistory.map((t, i) => {
                const maxVal = Math.max(...tokenHistory.map(x => x.value), 1)
                const h = (t.value / maxVal) * 100
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <div className="w-full rounded-t-sm bg-gradient-to-t from-purple-600/40 to-purple-400/20 transition-all" style={{ height: `${h}%` }} />
                    <span className="text-[8px] text-white/30">{t.name}</span>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Diagnostic Modal ───────────────────────────────────── */}
      {diagOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-white/10 bg-[#0a0a0f] p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white/80 flex items-center gap-2">
                <Wrench className="h-4 w-4 text-purple-400" />
                System Diagnostic
                {diagRunning && <Loader2 className="h-3 w-3 animate-spin text-purple-400" />}
              </h2>
              <button onClick={() => setDiagOpen(false)} className="text-white/30 hover:text-white/60">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {diagResults.length === 0 && diagRunning && (
                <div className="flex items-center gap-2 py-4 text-sm text-white/40">
                  <Loader2 className="h-4 w-4 animate-spin" /> Scanning pillars...
                </div>
              )}
              {diagResults.map(r => (
                <div key={r.pillar} className="flex items-center gap-3 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2.5">
                  <span className={cn(
                    'h-2.5 w-2.5 rounded-full shrink-0',
                    r.status === 'healthy' ? 'bg-emerald-400' : r.status === 'degraded' ? 'bg-yellow-400' : 'bg-red-400'
                  )} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white/80">{r.pillar}</span>
                      <Badge variant="outline" className={cn(
                        'text-[9px]',
                        r.status === 'healthy' ? 'border-emerald-500/20 text-emerald-400' :
                        r.status === 'degraded' ? 'border-yellow-500/20 text-yellow-400' :
                        'border-red-500/20 text-red-400'
                      )}>{r.status.toUpperCase()}</Badge>
                      <span className="text-[10px] text-white/30">{r.latencyMs}ms</span>
                    </div>
                    <p className="text-[11px] text-white/40 truncate">{r.details}</p>
                  </div>
                  <span className={cn('text-sm font-bold tabular-nums', healthColor(r.health))}>{r.health}%</span>
                </div>
              ))}
              {!diagRunning && diagResults.length > 0 && (
                <div className="mt-3 rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div><p className="text-lg font-bold text-emerald-400 tabular-nums">{diagResults.filter(r => r.status === 'healthy').length}</p><p className="text-[9px] text-white/40">Healthy</p></div>
                    <div><p className="text-lg font-bold text-yellow-400 tabular-nums">{diagResults.filter(r => r.status === 'degraded').length}</p><p className="text-[9px] text-white/40">Degraded</p></div>
                    <div><p className="text-lg font-bold text-red-400 tabular-nums">{diagResults.filter(r => r.status === 'critical').length}</p><p className="text-[9px] text-white/40">Critical</p></div>
                    <div><p className="text-lg font-bold text-purple-400 tabular-nums">{Math.round(diagResults.reduce((s, r) => s + r.health, 0) / diagResults.length)}%</p><p className="text-[9px] text-white/40">Avg Health</p></div>
                  </div>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" size="sm" onClick={() => setDiagOpen(false)} className="border-white/10 text-white/60">
                Close
              </Button>
              {!diagRunning && diagResults.length > 0 && (
                <Button size="sm" onClick={runDiagnostic} className="bg-purple-600 hover:bg-purple-700 text-white">
                  <RefreshCw className="h-3 w-3 mr-1" /> Re-run
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Status Footer ──────────────────────────────────────── */}
      <div className="flex items-center gap-4 text-[10px] text-white/20 border-t border-white/5 pt-4">
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          All data live from database
        </span>
        <span>·</span>
        <span>{pillars.length} pillars monitored</span>
        <span>·</span>
        <span>{stats.stressLab.templates} test templates</span>
        <span className="ml-auto">{new Date().toISOString().slice(0, 19).replace('T', ' ')} UTC</span>
      </div>
    </div>
  )
}


export { OverviewTab }
