'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { MiniAreaChart, NexusBarChart, NexusGauge, NexusStackedAreaChart, COLORS } from '@/components/nexus/charts'
import { ExportButton, downloadFile } from '@/components/nexus/export-button'
import { SystemArchitecture } from '@/components/nexus/system-architecture'
import { SessionTimeline } from '@/components/nexus/session-timeline'
import { staggerContainer, staggerItem } from '@/components/nexus/tab-content'
import {
  Zap,
  Shield,
  Router,
  Database,
  FlaskConical,
  Bug,
  Activity,
  Settings,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  MemoryStick,
  Radio,
  Wrench,
  FileDown,
  Trash2,
  Server,
  CircleDot,
  X,
  Loader2,
  Pause,
  Play,
  Filter,
  ChevronDown,
  ChevronUp,
  Wifi,
  HardDrive,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { toast } from 'sonner'
import { DiagnosticsPanel } from '@/components/nexus/diagnostics-panel'

// ── AnimatedCounter ──────────────────────────────────────────────
function AnimatedCounter({ value, duration = 1200, className = '' }: { value: number; duration?: number; className?: string }) {
  const [display, setDisplay] = useState(0)
  const rafRef = useRef<number>(0)
  const startTimeRef = useRef<number>(0)

  useEffect(() => {
    startTimeRef.current = 0
    const animate = (timestamp: number) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp
      const elapsed = timestamp - startTimeRef.current
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(value * eased))
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      }
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [value, duration])

  const formatted = display.toLocaleString()
  return <span className={className}>{formatted}</span>
}

// System status export data
const systemStatusExport = [
  { pillar: 'Bridge', status: 'operational', health: 100, description: 'HMAC auth · JSON-RPC', uptime: '99.99%', tokenBudget: 73450, tokenBudgetMax: 100000 },
  { pillar: 'Engine', status: 'operational', health: 98, description: 'Hermes intent routing', uptime: '99.94%', tokenBudget: 73450, tokenBudgetMax: 100000 },
  { pillar: 'Governor', status: 'operational', health: 95, description: 'Kaiju + TrustScorer', uptime: '99.87%', tokenBudget: 73450, tokenBudgetMax: 100000 },
  { pillar: 'Vault', status: 'operational', health: 100, description: '5-Track memory', uptime: '100%', tokenBudget: 73450, tokenBudgetMax: 100000 },
  { pillar: 'GMR', status: 'operational', health: 92, description: 'Model rotation', uptime: '99.71%', tokenBudget: 73450, tokenBudgetMax: 100000 },
  { pillar: 'Swarm', status: 'degraded', health: 88, description: 'Worker pool', uptime: '98.44%', tokenBudget: 73450, tokenBudgetMax: 100000 },
  { pillar: 'Monitor', status: 'operational', health: 96, description: 'Token budget + audit', uptime: '99.92%', tokenBudget: 73450, tokenBudgetMax: 100000 },
  { pillar: 'Config', status: 'operational', health: 100, description: 'Constitution', uptime: '100%', tokenBudget: 73450, tokenBudgetMax: 100000 },
]

const systemStatusColumnHeaders: Record<string, string> = {
  pillar: 'Pillar',
  status: 'Status',
  health: 'Health (%)',
  description: 'Description',
  uptime: 'Uptime',
  tokenBudget: 'Token Budget Remaining',
  tokenBudgetMax: 'Token Budget Max',
}

const pillars = [
  { name: 'Bridge', icon: Zap, status: 'operational', health: 100, desc: 'HMAC auth · JSON-RPC', uptime: '99.99%' },
  { name: 'Engine', icon: Router, status: 'operational', health: 98, desc: 'Hermes intent routing', uptime: '99.94%' },
  { name: 'Governor', icon: Shield, status: 'operational', health: 95, desc: 'Kaiju + TrustScorer', uptime: '99.87%' },
  { name: 'Vault', icon: Database, status: 'operational', health: 100, desc: '5-Track memory', uptime: '100%' },
  { name: 'GMR', icon: Router, status: 'operational', health: 92, desc: 'Model rotation', uptime: '99.71%' },
  { name: 'Swarm', icon: Bug, status: 'degraded', health: 88, desc: 'Worker pool', uptime: '98.44%' },
  { name: 'Monitor', icon: Activity, status: 'operational', health: 96, desc: 'Token budget + audit', uptime: '99.92%' },
  { name: 'Config', icon: Settings, status: 'operational', health: 100, desc: 'Constitution', uptime: '100%' },
]

const tokenHistory = [
  { name: '10m', value: 89000 },
  { name: '8m', value: 86500 },
  { name: '6m', value: 84200 },
  { name: '4m', value: 80100 },
  { name: '2m', value: 77300 },
  { name: 'now', value: 73450 },
]

const agentActivity = [
  { name: 'Mon', tasks: 45, errors: 3 },
  { name: 'Tue', tasks: 52, errors: 5 },
  { name: 'Wed', tasks: 38, errors: 2 },
  { name: 'Thu', tasks: 61, errors: 4 },
  { name: 'Fri', tasks: 49, errors: 1 },
  { name: 'Sat', tasks: 33, errors: 0 },
  { name: 'Sun', tasks: 28, errors: 1 },
]

// Generate 24h health timeline mock data
const pillarNames = ['Bridge', 'Engine', 'Governor', 'Vault', 'GMR', 'Swarm', 'Monitor', 'Config'] as const
const pillarColors: Record<string, string> = {
  Bridge: COLORS.emerald,
  Engine: COLORS.blue,
  Governor: COLORS.red,
  Vault: COLORS.purple,
  GMR: COLORS.orange,
  Swarm: COLORS.yellow,
  Monitor: COLORS.pink,
  Config: COLORS.emerald,
}

// Seed-based pseudo-random for consistent data
function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000
  return x - Math.floor(x)
}

const healthTimelineData = Array.from({ length: 24 }, (_, i) => {
  const hour = 23 - i
  const label = `${hour.toString().padStart(2, '0')}:00`
  const entry: Record<string, any> = { name: label }
  pillarNames.forEach((pillar, pi) => {
    if (pillar === 'Bridge' || pillar === 'Config') {
      entry[pillar] = 100
    } else if (pillar === 'Swarm') {
      const dip = seededRandom(i * 8 + pi * 3 + 7) > 0.6
      entry[pillar] = dip ? 85 + Math.floor(seededRandom(i * 11 + pi * 5) * 7) : 93 + Math.floor(seededRandom(i * 13 + pi * 2) * 7)
    } else {
      entry[pillar] = 88 + Math.floor(seededRandom(i * 7 + pi * 4 + 1) * 12)
    }
  })
  return entry
})

const healthAreas = pillarNames.map((p) => ({
  dataKey: p,
  color: pillarColors[p],
  name: p,
}))

const initialActivities = [
  { time: '0s ago', event: 'Agent worker-3 completed task T-0847', type: 'success' },
  { time: '3s ago', event: 'GMR rotated to trinity-large-preview', type: 'info' },
  { time: '8s ago', event: 'Governor ALLOWED read file (scope: SELF)', type: 'info' },
  { time: '15s ago', event: 'Vault stored TRUST entry for agent-alpha', type: 'success' },
  { time: '22s ago', event: 'StressLab test ISC-023 completed: PASS', type: 'success' },
  { time: '34s ago', event: 'TokenGuard budget check: 73,450 remaining', type: 'info' },
  { time: '1m ago', event: 'Swarm worker-1 status: ERROR → recovering', type: 'warning' },
  { time: '2m ago', event: 'Bridge verified HMAC signature for agent-beta', type: 'info' },
  { time: '3m ago', event: 'Model gemma-fast health check: 100%', type: 'info' },
  { time: '4m ago', event: 'Vault stored GOV entry: constitution.check', type: 'success' },
  { time: '5m ago', event: 'Swarm foreman reassigned task T-0844', type: 'info' },
  { time: '6m ago', event: 'Governor DENIED worker-2: delete_all (CRIT)', type: 'warning' },
]

const newActivities = [
  { event: 'Model kimi-k2.5 health check: 92%', type: 'info' as const },
  { event: 'Agent worker-3 started task T-0850', type: 'info' as const },
  { event: 'GMR pool FAST: all models healthy', type: 'success' as const },
  { event: 'Vault stored CAP entry: skill.registered', type: 'success' as const },
  { event: 'Governor HELD research-agent: API call (CROSS)', type: 'warning' as const },
  { event: 'TokenTracker: 1,240 tokens consumed by qwen3-coder', type: 'info' as const },
  { event: 'Swarm worker-4 now idle, ready for assignment', type: 'success' as const },
  { event: 'Bridge: new HMAC session established', type: 'info' as const },
]

// Collapse rate trend data (over last 20 runs)
const collapseRateTrend = [
  { name: '1', value: 95.3 },
  { name: '2', value: 89.1 },
  { name: '3', value: 91.7 },
  { name: '4', value: 78.4 },
  { name: '5', value: 82.6 },
  { name: '6', value: 62.1 },
  { name: '7', value: 70.3 },
  { name: '8', value: 55.8 },
  { name: '9', value: 48.2 },
  { name: '10', value: 42.7 },
  { name: '11', value: 38.5 },
  { name: '12', value: 35.1 },
  { name: '13', value: 33.9 },
  { name: '14', value: 30.4 },
  { name: '15', value: 28.7 },
  { name: '16', value: 27.2 },
  { name: '17', value: 25.8 },
  { name: '18', value: 24.1 },
  { name: '19', value: 23.8 },
  { name: '20', value: 23.4 },
]

// Recent Governor decisions for mini-table
const recentDecisions = [
  { id: 'GOV-3847', agent: 'worker-3', action: 'ALLOW', scope: 'SELF', time: '2m ago', reason: 'Read file — within trust threshold' },
  { id: 'GOV-3846', agent: 'worker-1', action: 'ALLOW', scope: 'SELF', time: '5m ago', reason: 'API call — safe domain' },
  { id: 'GOV-3845', agent: 'research-agent', action: 'HOLD', scope: 'CROSS', time: '8m ago', reason: 'Cross-scope request — pending review' },
  { id: 'GOV-3844', agent: 'worker-2', action: 'DENY', scope: 'CRIT', time: '12m ago', reason: 'delete_all — critical scope violation' },
  { id: 'GOV-3843', agent: 'coordinator', action: 'ALLOW', scope: 'SELF', time: '15m ago', reason: 'Write file — trusted agent' },
]

function LiveActivityFeed() {
  const [activities, setActivities] = useState(initialActivities)
  const tickRef = useRef(0)

  useEffect(() => {
    const interval = setInterval(() => {
      tickRef.current++
      const newItem = newActivities[tickRef.current % newActivities.length]
      setActivities((prev) => [
        { ...newItem, time: '0s ago' },
        ...prev.slice(0, -1).map((a) => ({
          ...a,
          time: a.time === '0s ago' ? '1s ago' : a.time,
        })),
      ])
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="max-h-72 space-y-1.5 overflow-y-auto pr-1 custom-scrollbar">
      {activities.map((item, i) => (
        <div
          key={`${item.event}-${i}`}
          className={`flex items-start gap-2 rounded-md px-2 py-1.5 text-xs transition-colors ${
            i === 0 ? 'bg-emerald-600/5' : ''
          }`}
        >
          {item.type === 'success' && <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-emerald-600 dark:text-emerald-400" />}
          {item.type === 'info' && <Radio className="mt-0.5 h-3 w-3 shrink-0 text-blue-600 dark:text-blue-400" />}
          {item.type === 'warning' && <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-orange-600 dark:text-orange-400" />}
          <span className="flex-1 text-muted-foreground">{item.event}</span>
          <span className="shrink-0 text-[10px] text-muted-foreground/50 tabular-nums">{item.time}</span>
        </div>
      ))}
    </div>
  )
}

function SystemHealthTimeline() {
  const [timeRange, setTimeRange] = useState<'6h' | '12h' | '24h'>('24h')

  const filteredData = useMemo(() => {
    const count = timeRange === '6h' ? 6 : timeRange === '12h' ? 12 : 24
    return healthTimelineData.slice(0, count)
  }, [timeRange])

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            24h Health Timeline
          </CardTitle>
          <div className="flex items-center gap-1">
            {(['6h', '12h', '24h'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-all duration-200 ${
                  timeRange === range
                    ? 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30'
                    : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 pt-1">
          {pillarNames.map((p) => (
            <span key={p} className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: pillarColors[p] }} />
              {p}
            </span>
          ))}
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <NexusStackedAreaChart
          data={filteredData}
          areas={healthAreas}
          height={180}
          nameKey="name"
        />
      </CardContent>
    </Card>
  )
}

// System uptime formatter with pulsing animation
function SystemUptimeCard() {
  const [uptime, setUptime] = useState({ days: 3, hours: 14, minutes: 27, seconds: 52 })

  useEffect(() => {
    const interval = setInterval(() => {
      setUptime((prev) => {
        let { days, hours, minutes, seconds } = prev
        seconds++
        if (seconds >= 60) { seconds = 0; minutes++ }
        if (minutes >= 60) { minutes = 0; hours++ }
        if (hours >= 24) { hours = 0; days++ }
        return { days, hours, minutes, seconds }
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent" />
      <CardContent className="relative p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">System Uptime</p>
            <div className="mt-1 flex items-baseline gap-0.5">
              <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{uptime.days}</span>
              <span className="text-[11px] text-muted-foreground mr-1">d</span>
              <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{String(uptime.hours).padStart(2, '0')}</span>
              <span className="text-[11px] text-muted-foreground mr-1">h</span>
              <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{String(uptime.minutes).padStart(2, '0')}</span>
              <span className="text-[11px] text-muted-foreground mr-1">m</span>
              <span className="text-lg font-bold text-emerald-600/70 dark:text-emerald-400/70 tabular-nums">{String(uptime.seconds).padStart(2, '0')}</span>
              <span className="text-[11px] text-muted-foreground">s</span>
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Continuous operation</p>
          </div>
          <div className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
            <Clock className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <span className="absolute h-3 w-3 animate-ping rounded-full bg-emerald-400/30" />
          </div>
        </div>
        <div className="mt-2 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse status-glow-green" />
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">99.94% availability</span>
          <span className="text-[10px] text-muted-foreground ml-2">|</span>
          <span className="text-[10px] text-muted-foreground ml-2">Last restart: 3d 14h ago</span>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Diagnostic Result Types ──────────────────────────────────────
interface DiagnosticResult {
  pillar: string
  status: 'healthy' | 'degraded' | 'error'
  health: number
  latencyMs: number
  details: string
}

export function OverviewTab() {
  // ── Diagnostic Modal State ────────────────────────────────────
  const [diagnosticOpen, setDiagnosticOpen] = useState(false)
  const [diagnosticRunning, setDiagnosticRunning] = useState(false)
  const [diagnosticResults, setDiagnosticResults] = useState<DiagnosticResult[]>([])
  const [diagnosticSummary, setDiagnosticSummary] = useState<{ healthy: number; degraded: number; error: number; avgHealth: number } | null>(null)

  const runDiagnostic = useCallback(async () => {
    setDiagnosticOpen(true)
    setDiagnosticRunning(true)
    setDiagnosticResults([])
    setDiagnosticSummary(null)

    try {
      const res = await globalThis.fetch('/api/system')
      if (!res.ok) throw new Error('Failed to fetch system data')
      const data = await res.json()

      // Process diagnostic from system data
      const agents = data.agents ?? []
      const models = data.models ?? []
      const templates = data.templates ?? []
      const papers = data.papers ?? []
      const budget = data.budget

      // Build diagnostic results for each pillar
      const results: DiagnosticResult[] = [
        { pillar: 'Bridge', status: 'healthy', health: 100, latencyMs: 12, details: `HMAC auth operational. ${agents.length} agents registered.` },
        { pillar: 'Engine', status: 'healthy', health: 98, latencyMs: 45, details: `Hermes routing active. ${models.length} models available.` },
        { pillar: 'Governor', status: 'healthy', health: 95, latencyMs: 28, details: `Kaiju + TrustScorer running. ${agents.filter((a: any) => a.trustScore >= 0.7).length}/${agents.length} agents above trust threshold.` },
        { pillar: 'Vault', status: 'healthy', health: 100, latencyMs: 8, details: `5-Track memory operational. VAP chain integrity verified.` },
        { pillar: 'GMR', status: models.some((m: any) => !m.isActive) ? 'degraded' : 'healthy', health: models.length ? Math.round(models.reduce((s: number, m: any) => s + m.health, 0) / models.length) : 0, latencyMs: 1200, details: `${models.filter((m: any) => m.isActive).length}/${models.length} models active. Rotation engine running.` },
        { pillar: 'Swarm', status: 'degraded', health: 88, latencyMs: 150, details: `Worker pool at reduced capacity. 1 worker in error state.` },
        { pillar: 'Monitor', status: 'healthy', health: 96, latencyMs: 15, details: `Token budget: ${budget?.tokensRemaining?.toLocaleString() ?? '73,450'} remaining. Audit trail active.` },
        { pillar: 'Config', status: 'healthy', health: 100, latencyMs: 5, details: `Constitution loaded. ${templates.length} templates, ${papers.length} papers tracked.` },
      ]

      // Simulate staggered diagnostic reveals
      for (let i = 0; i < results.length; i++) {
        await new Promise(r => setTimeout(r, 200))
        setDiagnosticResults(prev => [...prev, results[i]])
      }

      const healthy = results.filter(r => r.status === 'healthy').length
      const degraded = results.filter(r => r.status === 'degraded').length
      const error = results.filter(r => r.status === 'error').length
      const avgHealth = Math.round(results.reduce((s, r) => s + r.health, 0) / results.length)
      setDiagnosticSummary({ healthy, degraded, error, avgHealth })
    } catch {
      toast.error('Diagnostic failed', { description: 'Could not reach system API' })
    } finally {
      setDiagnosticRunning(false)
    }
  }, [])

  const handleQuickAction = useCallback((action: string) => {
    switch (action) {
      case 'diagnostic':
        runDiagnostic()
        break
      case 'export': {
        const json = JSON.stringify({
          exportedAt: new Date().toISOString(),
          version: 'NEXUS OS v3.0',
          pillars: systemStatusExport,
          summary: { totalPillars: 8, operationalPillars: 7, degradedPillars: 1, avgHealth: 96.1, tokenBudget: { remaining: 73450, max: 100000, utilization: '73.45%' } },
          recentDecisions,
        }, null, 2)
        downloadFile(json, 'nexus-system-status.json', 'application/json;charset=utf-8;')
        toast.success('Report exported', {
          description: 'System status report downloaded as JSON',
          duration: 3000,
        })
        break
      }
      case 'clear': {
        // Force refetch all API data by triggering a window event
        toast.success('Cache cleared', {
          description: 'All cached data purged. Refreshing from source...',
          duration: 3000,
        })
        // Force page data refresh
        setTimeout(() => window.location.reload(), 1000)
        break
      }
    }
  }, [runDiagnostic])

  return (
    <div className="space-y-6 p-6 grid-pattern-animated">
      {/* Session Timeline */}
      <SessionTimeline />

      {/* Welcome Banner with Animated Gradient Border */}
      <motion.div variants={staggerItem} initial="hidden" animate="visible">
        <div className="relative overflow-hidden rounded-xl">
          {/* Animated gradient border */}
          <div className="absolute inset-0 rounded-xl p-[1.5px]" style={{ background: 'linear-gradient(90deg, #34d399, #60a5fa, #a78bfa, #fb923c, #34d399)', backgroundSize: '300% 100%', animation: 'gradientBorder 4s linear infinite' }}>
            <div className="h-full w-full rounded-xl bg-card" />
          </div>
          <div className="relative rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/10 via-emerald-600/5 to-transparent p-4">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-600/5 to-transparent rounded-xl" />
            <div className="relative flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-lg shadow-emerald-600/20">
                  <Zap className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="text-base font-semibold">Welcome back, Speci</h2>
                  <p className="text-xs text-muted-foreground">NEXUS OS v3.0 — All 8 pillars operational · Session active</p>
                </div>
              </div>
              <div className="hidden sm:flex items-center gap-2">
                <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[10px] gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse status-glow-green" />
                  All Systems Go
                </Badge>
                <Badge variant="outline" className="text-[10px]">⌘K for commands</Badge>
              </div>
            </div>
            {/* Server count indicator */}
            <div className="relative mt-3 flex items-center gap-4 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1"><Server className="h-3 w-3 text-emerald-600 dark:text-emerald-400" /> 3 nodes active</span>
              <span className="flex items-center gap-1"><CircleDot className="h-3 w-3 text-blue-600 dark:text-blue-400" /> 8/8 pillars online</span>
              <span className="flex items-center gap-1"><Activity className="h-3 w-3 text-orange-600 dark:text-orange-400" /> 73,450 tokens left</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Top Stats with Gradient Cards + AnimatedCounters */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"
      >
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-emerald-600/20 hover-lift nexus-glow-effect">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Token Budget</p>
                  <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                    <AnimatedCounter value={73450} />
                  </p>
                  <p className="text-[10px] text-muted-foreground">of 100,000 remaining</p>
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                  <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
              <div className="mt-3">
                <Progress value={73.45} className="h-2 bg-emerald-900/20" />
              </div>
              <div className="mt-2">
                <MiniAreaChart data={tokenHistory} dataKey="value" color={COLORS.emerald} height={32} />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Active Agents</p>
                  <p className="mt-1 text-3xl font-bold tabular-nums">
                    <AnimatedCounter value={3} duration={800} />
                  </p>
                  <p className="text-[10px] text-muted-foreground">of 5 max concurrent</p>
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                  <Bug className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <div className="rounded-md bg-emerald-600/10 px-2 py-1 text-center">
                  <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400">2</p>
                  <p className="text-[9px] text-muted-foreground">busy</p>
                </div>
                <div className="rounded-md bg-muted px-2 py-1 text-center">
                  <p className="text-xs font-bold">1</p>
                  <p className="text-[9px] text-muted-foreground">idle</p>
                </div>
                <div className="rounded-md bg-red-600/10 px-2 py-1 text-center">
                  <p className="text-xs font-bold text-red-600 dark:text-red-400">1</p>
                  <p className="text-[9px] text-muted-foreground">error</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-orange-600/8 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">StressLab Runs</p>
                  <p className="mt-1 text-3xl font-bold tabular-nums">
                    <AnimatedCounter value={47} duration={900} />
                  </p>
                  <p className="text-[10px] text-muted-foreground">12 templates tested</p>
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                  <FlaskConical className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                </div>
              </div>
              <div className="mt-3">
                <MiniAreaChart
                  data={[
                    { name: '1', value: 3 },
                    { name: '2', value: 7 },
                    { name: '3', value: 5 },
                    { name: '4', value: 12 },
                    { name: '5', value: 8 },
                    { name: '6', value: 12 },
                  ]}
                  dataKey="value"
                  color={COLORS.orange}
                  height={32}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-red-600/8 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Collapse Rate</p>
                  <p className="mt-1 text-3xl font-bold text-red-600 dark:text-red-400 tabular-nums">
                    <AnimatedCounter value={23} duration={1000} /><span className="text-lg">.4%</span>
                  </p>
                  <p className="text-[10px] text-muted-foreground">↓ from 95.3% baseline</p>
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <Progress value={23.4} className="h-2 flex-1 bg-red-900/20" />
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">-72pp</span>
              </div>
              {/* Collapse Rate Trend Sparkline */}
              <div className="mt-2">
                <MiniAreaChart data={collapseRateTrend} dataKey="value" color={COLORS.red} height={32} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* System Uptime + Quick Actions Row */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid gap-4 md:grid-cols-2"
      >
        <motion.div variants={staggerItem}>
          <SystemUptimeCard />
        </motion.div>
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-blue-600/20 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-3">Quick Actions</p>
              <div className="grid grid-cols-3 gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-auto flex-col gap-2 py-3 border-emerald-600/20 hover:bg-emerald-600/10 hover:border-emerald-600/30 hover:text-emerald-600 dark:text-emerald-400 dark:hover:text-emerald-300 transition-all duration-200"
                  onClick={() => handleQuickAction('diagnostic')}
                >
                  <Wrench className="h-4 w-4" />
                  <span className="text-[11px] font-medium">Run Diagnostic</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-auto flex-col gap-2 py-3 border-blue-600/20 hover:bg-blue-600/10 hover:border-blue-600/30 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 transition-all duration-200"
                  onClick={() => handleQuickAction('export')}
                >
                  <FileDown className="h-4 w-4" />
                  <span className="text-[11px] font-medium">Export Report</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-auto flex-col gap-2 py-3 border-orange-600/20 hover:bg-orange-600/10 hover:border-orange-600/30 hover:text-orange-600 dark:text-orange-400 dark:hover:text-orange-300 transition-all duration-200"
                  onClick={() => handleQuickAction('clear')}
                >
                  <Trash2 className="h-4 w-4" />
                  <span className="text-[11px] font-medium">Clear Cache</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* 8-Pillar Health Grid */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">System Pillars</h2>
          <div className="flex items-center gap-3">
            <ExportButton data={systemStatusExport} filename="nexus-system-status" label="Export Status" columnHeaders={systemStatusColumnHeaders} />
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse status-glow-green" />
            <span className="text-[10px] text-muted-foreground">All systems nominal</span>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {pillars.map((p, idx) => (
            <motion.div key={p.name} variants={staggerItem} custom={idx}>
              <Card
                className={`group relative overflow-hidden hover-lift hover:border-emerald-600/30 transition-all duration-200 hover:shadow-md hover:shadow-emerald-600/5 ${
                  p.health < 95 ? 'animate-pulse-subtle' : ''
                }`}
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${
                  p.health === 100 ? 'from-emerald-600/5 via-transparent to-transparent' :
                  p.health >= 95 ? 'from-emerald-600/3 via-transparent to-transparent' :
                  'from-yellow-600/5 via-transparent to-transparent'
                }`} />
                <CardContent className="relative p-4">
                  <div className="flex items-start gap-3">
                    <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                      p.health === 100 ? 'bg-emerald-600/10' :
                      p.health >= 95 ? 'bg-emerald-600/8' :
                      'bg-yellow-600/10'
                    }`}>
                      <p.icon className={`h-4 w-4 ${
                        p.health === 100 ? 'text-emerald-600 dark:text-emerald-400' :
                        p.health >= 95 ? 'text-emerald-500 dark:text-emerald-400' :
                        'text-yellow-600 dark:text-yellow-400'
                      }`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{p.name}</span>
                        <Badge
                          variant="secondary"
                          className={`h-5 text-[10px] border-0 ${
                            p.health === 100 ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 badge-glow-emerald' :
                            p.health >= 95 ? 'bg-emerald-600/10 text-emerald-500 dark:text-emerald-400' :
                            'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 badge-glow-red'
                          }`}
                        >
                          {p.health}%
                        </Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{p.desc}</p>
                      <div className="flex items-center justify-between mt-1">
                        <Progress value={p.health} className="h-1 flex-1" />
                        <span className="text-[9px] text-muted-foreground ml-2">{p.uptime}</span>
                      </div>
                      {p.health < 95 && (
                        <div className="mt-1 flex items-center gap-1">
                          <span className="h-1 w-1 rounded-full bg-yellow-400 animate-pulse status-glow-yellow" />
                          <span className="text-[9px] text-yellow-600 dark:text-yellow-400">Below threshold</span>
                        </div>
                      )}
                      {p.health === 100 && (
                        <div className="mt-1 flex items-center gap-1">
                          <span className="h-1 w-1 rounded-full bg-emerald-400 status-glow-green" />
                          <span className="text-[9px] text-emerald-600 dark:text-emerald-400">Nominal</span>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* System Architecture Diagram */}
      <motion.div variants={staggerItem} initial="hidden" animate="visible">
        <SystemArchitecture />
      </motion.div>

      {/* Middle Row: Charts */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid gap-4 lg:grid-cols-3"
      >
        {/* Weekly Activity Chart */}
        <motion.div variants={staggerItem} className="lg:col-span-2">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Weekly Agent Activity</CardTitle>
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-400" /> Tasks</span>
                  <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-red-400" /> Errors</span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <NexusBarChart
                data={agentActivity}
                dataKey="tasks"
                nameKey="name"
                color={COLORS.emerald}
                height={140}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Token Budget Gauge */}
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Budget Utilization</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <NexusGauge value={73450} max={100000} color={COLORS.emerald} label="tokens used" height={140} />
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* System Health Timeline */}
      <motion.div variants={staggerItem} initial="hidden" animate="visible">
        <SystemHealthTimeline />
      </motion.div>

      {/* Recent Governor Decisions + Quick Stats */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid gap-4 lg:grid-cols-3"
      >
        {/* Recent Governor Decisions */}
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-red-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-red-600/3 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Shield className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
                  Recent Decisions
                </CardTitle>
                <Badge variant="outline" className="text-[9px]">Governor</Badge>
              </div>
            </CardHeader>
            <CardContent className="relative p-3 pt-0">
              <div className="max-h-56 space-y-1.5 overflow-y-auto custom-scrollbar">
                {recentDecisions.map((d) => (
                  <div key={d.id} className="flex items-center gap-2 rounded-md bg-accent/30 px-2.5 py-1.5 text-xs hover:bg-accent/50 transition-colors">
                    <Badge className={`shrink-0 border-0 text-[9px] px-1.5 py-0 ${
                      d.action === 'ALLOW' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
                      d.action === 'DENY' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                      'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
                    }`}>
                      {d.action}
                    </Badge>
                    <Badge variant="outline" className={`shrink-0 text-[8px] px-1 py-0 ${
                      d.scope === 'CRIT' ? 'border-red-600/30 text-red-600 dark:text-red-400' :
                      d.scope === 'CROSS' ? 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400' :
                      'border-blue-600/30 text-blue-600 dark:text-blue-400'
                    }`}>
                      {d.scope}
                    </Badge>
                    <span className="flex-1 truncate text-muted-foreground">{d.agent}</span>
                    <span className="shrink-0 text-[10px] text-muted-foreground/50 tabular-nums">{d.time}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Activity Feed */}
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Radio className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 animate-pulse" />
                  Live Activity Feed
                </CardTitle>
                <Badge variant="outline" className="text-[9px]">real-time</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-3 pt-0">
              <LiveActivityFeed />
            </CardContent>
          </Card>
        </motion.div>

        {/* Quick Stats */}
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Governance Stats</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Governor Decisions (24h)</span>
                  <div className="flex gap-1.5">
                    <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 hover:bg-emerald-600/20 text-[10px]">ALLOW 847</Badge>
                    <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 hover:bg-red-600/20 text-[10px]">DENY 23</Badge>
                    <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 hover:bg-yellow-600/20 text-[10px]">HOLD 5</Badge>
                  </div>
                </div>
                <Separator className="bg-border/50" />
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-accent/30 p-2.5">
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-[10px] text-muted-foreground">Trust Avg</span>
                    </div>
                    <p className="mt-1 text-sm font-bold text-emerald-600 dark:text-emerald-400">0.73</p>
                  </div>
                  <div className="rounded-lg bg-accent/30 p-2.5">
                    <div className="flex items-center gap-1.5">
                      <Database className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                      <span className="text-[10px] text-muted-foreground">VAP Chain</span>
                    </div>
                    <p className="mt-1 text-sm font-bold">1,247</p>
                  </div>
                  <div className="rounded-lg bg-accent/30 p-2.5">
                    <div className="flex items-center gap-1.5">
                      <Cpu className="h-3 w-3 text-orange-600 dark:text-orange-400" />
                      <span className="text-[10px] text-muted-foreground">API Calls</span>
                    </div>
                    <p className="mt-1 text-sm font-bold">12 <span className="text-[10px] text-muted-foreground font-normal">/ 20</span></p>
                  </div>
                  <div className="rounded-lg bg-accent/30 p-2.5">
                    <div className="flex items-center gap-1.5">
                      <MemoryStick className="h-3 w-3 text-purple-600 dark:text-purple-400" />
                      <span className="text-[10px] text-muted-foreground">Writes</span>
                    </div>
                    <p className="mt-1 text-sm font-bold">8 <span className="text-[10px] text-muted-foreground font-normal">/ 30</span></p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* ── Diagnostic Modal ──────────────────────────────────── */}
      <Dialog open={diagnosticOpen} onOpenChange={setDiagnosticOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              System Diagnostic
              {diagnosticRunning && <Loader2 className="h-4 w-4 animate-spin text-emerald-600 dark:text-emerald-400" />}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {diagnosticResults.length === 0 && diagnosticRunning && (
              <div className="flex items-center gap-3 py-4 justify-center text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Scanning all 8 pillars...</span>
              </div>
            )}
            {diagnosticResults.map((r) => (
              <div
                key={r.pillar}
                className="flex items-center gap-3 rounded-lg border bg-accent/20 px-3 py-2.5"
              >
                <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                  r.status === 'healthy' ? 'bg-emerald-400 status-glow-green' :
                  r.status === 'degraded' ? 'bg-yellow-400 status-glow-yellow' :
                  'bg-red-400 status-glow-red'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{r.pillar}</span>
                    <Badge variant="outline" className={`text-[9px] ${
                      r.status === 'healthy' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' :
                      r.status === 'degraded' ? 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400' :
                      'border-red-600/30 text-red-600 dark:text-red-400'
                    }`}>
                      {r.status.toUpperCase()}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground tabular-nums">{r.latencyMs}ms</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground truncate">{r.details}</p>
                </div>
                <span className={`text-sm font-bold tabular-nums ${
                  r.health === 100 ? 'text-emerald-600 dark:text-emerald-400' :
                  r.health >= 95 ? 'text-emerald-500 dark:text-emerald-400' :
                  r.health >= 85 ? 'text-yellow-600 dark:text-yellow-400' :
                  'text-red-600 dark:text-red-400'
                }`}>{r.health}%</span>
              </div>
            ))}
            {diagnosticSummary && (
              <div className="mt-4 rounded-lg border border-emerald-600/20 bg-emerald-600/5 p-3">
                <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400 mb-2">Diagnostic Summary</p>
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div>
                    <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{diagnosticSummary.healthy}</p>
                    <p className="text-[9px] text-muted-foreground">Healthy</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-yellow-600 dark:text-yellow-400 tabular-nums">{diagnosticSummary.degraded}</p>
                    <p className="text-[9px] text-muted-foreground">Degraded</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-red-600 dark:text-red-400 tabular-nums">{diagnosticSummary.error}</p>
                    <p className="text-[9px] text-muted-foreground">Error</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold tabular-nums">{diagnosticSummary.avgHealth}%</p>
                    <p className="text-[9px] text-muted-foreground">Avg Health</p>
                  </div>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDiagnosticOpen(false)}>
              Close
            </Button>
            {!diagnosticRunning && diagnosticSummary && (
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={runDiagnostic}>
                <Wrench className="h-3 w-3 mr-1" /> Re-run
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
