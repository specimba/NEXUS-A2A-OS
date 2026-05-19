'use client'

import { useState, useEffect, useRef, useCallback, Suspense, useMemo } from 'react'
import dynamic from 'next/dynamic'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { CommandDialog, CommandInput, CommandList, CommandGroup, CommandItem, CommandEmpty, CommandShortcut } from '@/components/ui/command'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'
import { QuickStatsWidget } from '@/components/nexus/quick-stats-widget'
import {
  Activity, Cpu, HardDrive, Zap, Wifi, Shield, Users, AlertTriangle,
  CheckCircle2, Clock, ArrowUpRight, ArrowDownRight, BarChart3,
  Radio, Bell, XCircle, Info, Search, Settings, Moon, Sun,
  RefreshCw, Download, Terminal, ChevronRight, ChevronDown,
  Heart, Network, Scale, BookOpen, Rocket, Globe, Server,
  TriangleAlert, Eye, Layers, Database, Key, Gauge, Boxes,
  Cog, Brain, MessageSquare, TrendingUp, AlertCircle, Monitor,
  GitBranch, Package, Lock, FileText, Target, Sparkles,
  Menu, X, Command, Timer, ShieldCheck, Flame,
  Loader2, Archive, Bug, LayoutGrid,
  ArrowUp, ArrowDown, Disc, RadioTower, Stethoscope,
  CheckCheck, Trash2, ExternalLink,
} from 'lucide-react'

// ─── Dynamic imports for full tab components (ssr: false avoids hydration mismatch) ──
const FullStressLabTab = dynamic(
  () => import('@/components/nexus/tabs/stresslab-tab').then(m => ({ default: m.StressLabTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

const FullResearchTab = dynamic(
  () => import('@/components/nexus/tabs/research-tab').then(m => ({ default: m.ResearchTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

const FullVaultTab = dynamic(
  () => import('@/components/nexus/tabs/vault-tab').then(m => ({ default: m.VaultTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

const FullSwarmTab = dynamic(
  () => import('@/components/nexus/tabs/swarm-tab').then(m => ({ default: m.SwarmTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

const FullArchitectureTab = dynamic(
  () => import('@/components/nexus/tabs/architecture-tab').then(m => ({ default: m.ArchitectureTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

const FullAIChatTab = dynamic(
  () => import('@/components/nexus/tabs/ai-chat-tab').then(m => ({ default: m.AiChatTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

const FullRateLimitTab = dynamic(
  () => import('@/components/nexus/tabs/rate-limit-tab').then(m => ({ default: m.RateLimitTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

const FullKpiTab = dynamic(
  () => import('@/components/nexus/tabs/kpi-tab').then(m => ({ default: m.KpiTab })),
  { ssr: false, loading: () => <TabLoader /> }
)

function TabLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-6 w-6 animate-spin text-emerald-500" />
        <span className="text-sm text-muted-foreground">Loading tab...</span>
      </div>
    </div>
  )
}

// ─── Static Data (no Date.now() / Math.random() at module level) ──────────

const TABS = [
  { id: 'overview', label: 'Overview', icon: Activity, group: 'Core' },
  { id: 'architecture', label: 'Architecture', icon: LayoutGrid, group: 'Core' },
  { id: 'agents', label: 'Agents', icon: Users, group: 'Core' },
  { id: 'providers', label: 'Providers', icon: Server, group: 'Routing' },
  { id: 'gmr', label: 'GMR Router', icon: Network, group: 'Routing' },
  { id: 'governor', label: 'Governor', icon: Shield, group: 'Governance' },
  { id: 'vault', label: 'Vault', icon: Archive, group: 'Governance' },
  { id: 'research', label: 'Research', icon: BookOpen, group: 'Intelligence' },
  { id: 'aichat', label: 'AI Assistant', icon: Brain, group: 'Intelligence' },
  { id: 'swarm', label: 'Swarm', icon: Bug, group: 'Operations' },
  { id: 'tokens', label: 'Tokens', icon: Zap, group: 'Metrics' },
  { id: 'ratelimits', label: 'Rate Limits', icon: Gauge, group: 'Metrics' },
  { id: 'kpi', label: 'KPI Dashboard', icon: Target, group: 'Metrics' },
  { id: 'stresslab', label: 'StressLab', icon: Flame, group: 'Testing' },
] as const

type TabId = typeof TABS[number]['id']

const healthPillars = [
  { name: 'Bridge', health: 98, status: 'healthy', icon: '🔗', version: 'v3.1.2' },
  { name: 'Engine', health: 95, status: 'healthy', icon: '⚙️', version: 'v2.8.1' },
  { name: 'Governor', health: 100, status: 'healthy', icon: '🛡️', version: 'v4.0.0' },
  { name: 'Vault', health: 97, status: 'healthy', icon: '🔐', version: 'v2.5.3' },
  { name: 'GMR', health: 91, status: 'healthy', icon: '🚦', version: 'v1.9.7' },
  { name: 'Swarm', health: 82, status: 'degraded', icon: '🐝', version: 'v1.3.2' },
  { name: 'Monitor', health: 94, status: 'healthy', icon: '📊', version: 'v2.1.0' },
  { name: 'Config', health: 100, status: 'healthy', icon: '🔧', version: 'v1.0.5' },
]

const providers = [
  { name: 'z-ai (GLM-4.7)', status: 'active', models: 3, latency: 45, pool: 'PREMIUM', trust: 0.98 },
  { name: 'OpenRouter', status: 'active', models: 5, latency: 120, pool: 'MID', trust: 0.92 },
  { name: 'Cerebras', status: 'active', models: 2, latency: 28, pool: 'FAST', trust: 0.89 },
  { name: 'Groq', status: 'active', models: 3, latency: 35, pool: 'FAST', trust: 0.91 },
  { name: 'Mistral', status: 'active', models: 4, latency: 85, pool: 'MID', trust: 0.94 },
  { name: 'Fireworks', status: 'degraded', models: 3, latency: 210, pool: 'MID', trust: 0.78 },
  { name: 'Scaleway', status: 'unknown', models: 1, latency: 0, pool: 'MID', trust: 0.45 },
  { name: 'DashScope', status: 'active', models: 2, latency: 95, pool: 'MID', trust: 0.87 },
  { name: 'SambaNova', status: 'active', models: 2, latency: 62, pool: 'FAST', trust: 0.90 },
  { name: 'NVIDIA NIM', status: 'active', models: 3, latency: 78, pool: 'PREMIUM', trust: 0.96 },
  { name: 'BitDeer', status: 'inactive', models: 0, latency: 0, pool: 'MID', trust: 0.0 },
  { name: 'Codestral', status: 'active', models: 1, latency: 92, pool: 'MID', trust: 0.88 },
  { name: 'DeepSeek', status: 'active', models: 2, latency: 110, pool: 'MID', trust: 0.85 },
]

const agents = [
  { name: 'worker-1', status: 'active', trust: 0.92, tasks: 47, domain: 'Research', model: 'trinity-large' },
  { name: 'worker-2', status: 'warning', trust: 0.78, tasks: 31, domain: 'Coding', model: 'qwen3-coder' },
  { name: 'worker-3', status: 'active', trust: 0.85, tasks: 38, domain: 'Analysis', model: 'gemma-fast' },
  { name: 'coordinator', status: 'active', trust: 0.95, tasks: 12, domain: 'Governance', model: 'glm-4.7' },
]

const constitutionalRules = [
  { id: 'CR-001', name: 'No Unattended Self-Modification', severity: 'critical' },
  { id: 'CR-002', name: 'Human Approval for Destructive Actions', severity: 'critical' },
  { id: 'CR-003', name: 'Token Budget Hard Limit', severity: 'warning' },
  { id: 'CR-004', name: 'Trust Score Decay Enforcement', severity: 'info' },
  { id: 'CR-005', name: 'Agent Autonomy Boundary', severity: 'critical' },
  { id: 'CR-006', name: 'Rate Limit Circuit Breaker', severity: 'warning' },
]

const alertFeedData = [
  { id: 1, severity: 'warning' as const, message: 'Memory usage approaching 80% threshold', source: 'System', offsetMs: 30000 },
  { id: 2, severity: 'info' as const, message: 'Model failover triggered for gemma-fast', source: 'ModelRelay', offsetMs: 90000 },
  { id: 3, severity: 'critical' as const, message: 'Provider dashscope rate limit exceeded', source: 'Gateway', offsetMs: 180000 },
  { id: 4, severity: 'success' as const, message: 'Constitutional check passed for all rules', source: 'Governor', offsetMs: 240000 },
  { id: 5, severity: 'info' as const, message: 'Token budget reset for new cycle', source: 'Tokens', offsetMs: 360000 },
  { id: 6, severity: 'warning' as const, message: 'Agent worker-2 trust score below 0.8', source: 'Governor', offsetMs: 480000 },
]

const systemPerformanceData = [
  { time: '00:00', cpu: 28, memory: 55, latency: 120 },
  { time: '02:00', cpu: 25, memory: 52, latency: 115 },
  { time: '04:00', cpu: 22, memory: 48, latency: 110 },
  { time: '06:00', cpu: 35, memory: 58, latency: 135 },
  { time: '08:00', cpu: 42, memory: 65, latency: 155 },
  { time: '10:00', cpu: 38, memory: 62, latency: 148 },
  { time: '12:00', cpu: 45, memory: 68, latency: 165 },
  { time: '14:00', cpu: 40, memory: 64, latency: 152 },
  { time: '16:00', cpu: 36, memory: 60, latency: 142 },
  { time: '18:00', cpu: 32, memory: 58, latency: 138 },
  { time: '20:00', cpu: 30, memory: 56, latency: 130 },
  { time: '22:00', cpu: 34, memory: 62, latency: 142 },
]

const requestVolumeData = [
  { hour: '12h', requests: 245 },
  { hour: '10h', requests: 289 },
  { hour: '8h', requests: 425 },
  { hour: '6h', requests: 298 },
  { hour: '4h', requests: 467 },
  { hour: '2h', requests: 342 },
  { hour: 'Now', requests: 315 },
]

// StressLab and Research data now comes from their full tab components (dynamic imports)

// ─── Helper functions ──────────────────────────────────────────────────────

function getRelativeTime(timestamp: number): string {
  if (timestamp === 0) return '...'
  const diff = Date.now() - timestamp
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}

// ─── Lightweight SVG Chart Components ──────────────────────────────────────

function SparklineSVG({ data, color = '#10b981', height = 32 }: { data: number[]; color?: string; height?: number }) {
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const w = 120
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none">
      <polyline fill="none" stroke={color} strokeWidth={1.5} points={points} />
    </svg>
  )
}

function MiniBarChart({ data, height = 80 }: { data: { label: string; value: number }[]; height?: number }) {
  const maxVal = Math.max(...data.map(d => d.value))
  return (
    <div className="flex items-end gap-1 h-full" style={{ height }}>
      {data.map((d, i) => (
        <div key={i} className="flex flex-col items-center flex-1 gap-1">
          <div className="w-full relative group">
            <div
              className="w-full rounded-t-sm bg-gradient-to-t from-emerald-600 to-emerald-400 dark:from-emerald-500 dark:to-emerald-300 transition-all duration-300 hover:from-emerald-500 hover:to-emerald-300"
              style={{ height: Math.max(4, (d.value / maxVal) * (height - 16)) }}
            />
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-card border border-border px-1.5 py-0.5 rounded text-[9px] font-mono opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
              {d.value}
            </div>
          </div>
          <span className="text-[8px] text-muted-foreground truncate w-full text-center">{d.label}</span>
        </div>
      ))}
    </div>
  )
}

function AreaChartSVG({ data, width = 400, height = 160 }: { data: { time: string; cpu: number; memory: number; latency: number }[]; width?: number; height?: number }) {
  const pad = { t: 10, r: 10, b: 20, l: 30 }
  const cw = width - pad.l - pad.r
  const ch = height - pad.t - pad.b
  const maxVal = 100

  const toPoints = (key: 'cpu' | 'memory' | 'latency') =>
    data.map((d, i) => {
      const x = pad.l + (i / (data.length - 1)) * cw
      const y = pad.t + ch - (d[key] / maxVal) * ch
      return `${x},${y}`
    }).join(' ')

  const toArea = (key: 'cpu' | 'memory' | 'latency', color: string) => {
    const linePoints = toPoints(key)
    const firstX = pad.l
    const lastX = pad.l + cw
    const bottomY = pad.t + ch
    const areaPoints = `${linePoints} ${lastX},${bottomY} ${firstX},${bottomY}`
    return (
      <g key={key}>
        <polygon fill={color} fillOpacity={0.1} points={areaPoints} />
        <polyline fill="none" stroke={color} strokeWidth={2} points={linePoints} />
      </g>
    )
  }

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((pct) => (
        <line key={pct} x1={pad.l} y1={pad.t + ch * (1 - pct)} x2={pad.l + cw} y2={pad.t + ch * (1 - pct)} stroke="currentColor" strokeOpacity={0.08} strokeWidth={1} />
      ))}
      {/* Y-axis labels */}
      {[0, 25, 50, 75, 100].map((v) => (
        <text key={v} x={pad.l - 5} y={pad.t + ch - (v / maxVal) * ch + 3} textAnchor="end" fill="currentColor" fillOpacity={0.4} fontSize={8} fontFamily="monospace">{v}</text>
      ))}
      {/* X-axis labels */}
      {data.map((d, i) => {
        if (i % 2 !== 0) return null
        const x = pad.l + (i / (data.length - 1)) * cw
        return <text key={i} x={x} y={height - 2} textAnchor="middle" fill="currentColor" fillOpacity={0.4} fontSize={8} fontFamily="monospace">{d.time}</text>
      })}
      {/* Data areas */}
      {toArea('latency', '#f97316')}
      {toArea('memory', '#3b82f6')}
      {toArea('cpu', '#10b981')}
      {/* Legend */}
      <g transform={`translate(${pad.l}, ${pad.t})`}>
        {[{ label: 'CPU', color: '#10b981' }, { label: 'Memory', color: '#3b82f6' }, { label: 'Latency', color: '#f97316' }].map((l, i) => (
          <g key={l.label} transform={`translate(${i * 70}, 0)`}>
            <rect width={8} height={3} fill={l.color} rx={1} />
            <text x={12} y={4} fill="currentColor" fillOpacity={0.6} fontSize={8} fontFamily="monospace">{l.label}</text>
          </g>
        ))}
      </g>
    </svg>
  )
}

function DonutChart({ segments, size = 80, strokeWidth = 8 }: { segments: { value: number; color: string; label: string }[]; size?: number; strokeWidth?: number }) {
  const total = segments.reduce((s, seg) => s + seg.value, 0)
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI

  // Pre-compute offsets for each segment to avoid mutation during render
  const segmentOffsets = segments.reduce<number[]>((acc, seg, i) => {
    const prevOffset = i === 0 ? 0 : acc[i - 1]
    acc.push(prevOffset + seg.value / total)
    return acc
  }, [])

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        {segments.map((seg, i) => {
          const pct = seg.value / total
          const dashOffset = circumference * (i === 0 ? 0 : segmentOffsets[i - 1])
          return (
            <circle key={i} cx={size / 2} cy={size / 2} r={radius} fill="none"
              stroke={seg.color} strokeWidth={strokeWidth}
              strokeDasharray={`${circumference * pct} ${circumference * (1 - pct)}`}
              strokeDashoffset={-dashOffset}
              strokeLinecap="round" className="transition-all duration-700" />
          )
        })}
      </svg>
      <div className="absolute text-[10px] font-bold tabular-nums">{total}</div>
    </div>
  )
}

// ─── Network Topology SVG ──────────────────────────────────────────────────

function NetworkTopology() {
  const nodes = [
    { id: 'dash', label: 'DASH', x: 200, y: 30, color: '#10b981', r: 16 },
    { id: 'gw', label: 'GW', x: 200, y: 90, color: '#34d399', r: 14 },
    { id: 'w1', label: 'W1', x: 80, y: 155, color: '#10b981', r: 12 },
    { id: 'w2', label: 'W2', x: 160, y: 165, color: '#eab308', r: 12 },
    { id: 'w3', label: 'W3', x: 240, y: 165, color: '#10b981', r: 12 },
    { id: 'crd', label: 'CRD', x: 320, y: 155, color: '#10b981', r: 12 },
    { id: 'prem', label: 'PREM', x: 60, y: 230, color: '#10b981', r: 11 },
    { id: 'mid', label: 'MID', x: 155, y: 240, color: '#3b82f6', r: 11 },
    { id: 'fast', label: 'FAST', x: 250, y: 240, color: '#f97316', r: 11 },
    { id: 'pv', label: '14 PV', x: 340, y: 230, color: '#8b5cf6', r: 11 },
  ]
  const links = [
    ['dash', 'gw'], ['gw', 'w1'], ['gw', 'w2'], ['gw', 'w3'], ['gw', 'crd'],
    ['w1', 'prem'], ['w1', 'mid'], ['w2', 'mid'], ['w2', 'fast'], ['w3', 'fast'],
    ['w3', 'prem'], ['crd', 'pv'], ['crd', 'mid'], ['prem', 'pv'], ['mid', 'pv'], ['fast', 'pv'],
  ]
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]))
  return (
    <svg viewBox="0 0 400 270" className="w-full" style={{ maxHeight: 240 }}>
      {links.map(([from, to], i) => {
        const f = nodeMap[from], t = nodeMap[to]
        if (!f || !t) return null
        return <line key={i} x1={f.x} y1={f.y} x2={t.x} y2={t.y} stroke="#374151" strokeWidth={1} strokeOpacity={0.5} />
      })}
      {nodes.map((n) => (
        <g key={n.id}>
          <circle cx={n.x} cy={n.y} r={n.r} fill={n.color} fillOpacity={0.2} stroke={n.color} strokeWidth={1.5}>
            <animate attributeName="fill-opacity" values="0.15;0.3;0.15" dur="3s" repeatCount="indefinite" />
          </circle>
          <text x={n.x} y={n.y + 4} textAnchor="middle" fill={n.color} fontSize={8} fontWeight={600} fontFamily="monospace">{n.label}</text>
        </g>
      ))}
      <text x={15} y={35} fill="#6b7280" fontSize={7} fontFamily="monospace">UI</text>
      <text x={15} y={95} fill="#6b7280" fontSize={7} fontFamily="monospace">ROUTING</text>
      <text x={15} y={160} fill="#6b7280" fontSize={7} fontFamily="monospace">AGENTS</text>
      <text x={15} y={235} fill="#6b7280" fontSize={7} fontFamily="monospace">MODELS</text>
    </svg>
  )
}

type TrendDirection = 'up' | 'down'

interface HealthMetric {
  value: number
  trend: TrendDirection
  history: number[]
}

interface HealthMetrics {
  cpu: HealthMetric
  memory: HealthMetric
  diskIO: HealthMetric
  networkIO: HealthMetric
}

// ─── Main Dashboard Component ──────────────────────────────────────────────

export function NexusDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [mounted, setMounted] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { theme, setTheme } = useTheme()

  // Live metrics
  const [activeConnections, setActiveConnections] = useState(247)
  const [requestsPerSec, setRequestsPerSec] = useState(34)
  const [tokensPerMin, setTokensPerMin] = useState(1420)
  const [errorRate, setErrorRate] = useState(0.3)
  const [rpsHistory, setRpsHistory] = useState<number[]>([32, 35, 28, 31, 34, 30, 33, 36, 29, 34])
  const [alerts, setAlerts] = useState(() => alertFeedData.map(a => ({ ...a, time: 0 })))
  const [clock, setClock] = useState('--:--:--')
  const [uptime, setUptime] = useState('00:00:00')
  const startTimeRef = useRef(0)
  const alertListRef = useRef<HTMLDivElement>(null)

  // Notification Center state
  const [notifications, setNotifications] = useState<Array<{
    id: number; severity: 'critical' | 'warning' | 'info' | 'success';
    message: string; source: string; time: number; read: boolean;
  }>>([])
  const [notifOpen, setNotifOpen] = useState(false)

  // Command Palette state
  const [commandOpen, setCommandOpen] = useState(false)

  // Diagnostics state
  const [diagRunning, setDiagRunning] = useState(false)
  const [diagProgress, setDiagProgress] = useState(0)
  const [healthMetrics, setHealthMetrics] = useState<HealthMetrics>({
    cpu: { value: 34, trend: 'up', history: [28, 30, 32, 31, 34] },
    memory: { value: 58, trend: 'down', history: [62, 60, 59, 61, 58] },
    diskIO: { value: 42, trend: 'up', history: [35, 38, 40, 39, 42] },
    networkIO: { value: 67, trend: 'up', history: [55, 60, 63, 65, 67] },
  })

  // Mount effect - resolve timestamps client-side only
  useEffect(() => {
    setMounted(true)
    startTimeRef.current = Date.now()
    const now = Date.now()
    setAlerts(alertFeedData.map(a => ({ ...a, time: now - a.offsetMs })))
  }, [])

  // Clock
  useEffect(() => {
    const update = () => {
      setClock(new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    }
    update()
    const i = setInterval(update, 1000)
    return () => clearInterval(i)
  }, [])

  // Uptime
  useEffect(() => {
    const update = () => {
      if (!startTimeRef.current) return
      const diff = Date.now() - startTimeRef.current
      const h = Math.floor(diff / 3600000).toString().padStart(2, '0')
      const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0')
      const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0')
      setUptime(`${h}:${m}:${s}`)
    }
    update()
    const i = setInterval(update, 1000)
    return () => clearInterval(i)
  }, [])

  // Live metrics update — every 10 seconds to avoid UI flashing
  useEffect(() => {
    const i = setInterval(() => {
      setActiveConnections(p => Math.max(150, Math.min(400, p + Math.floor(Math.random() * 20) - 10)))
      setRequestsPerSec(p => Math.max(10, Math.min(80, p + Math.floor(Math.random() * 8) - 4)))
      setTokensPerMin(p => Math.max(500, Math.min(3000, p + Math.floor(Math.random() * 200) - 100)))
      setErrorRate(p => Math.max(0, Math.min(5, parseFloat((p + (Math.random() * 0.4 - 0.2)).toFixed(1)))))
      setRpsHistory(p => [...p.slice(1), Math.max(10, Math.min(80, p[p.length - 1] + Math.floor(Math.random() * 8) - 4))])
      // Only add a new alert occasionally (30% chance per tick)
      if (Math.random() < 0.3) {
        setAlerts(prev => {
          const nextId = Math.max(...prev.map(a => a.id)) + 1
          const msgs = ['Memory spike on worker-2', 'Rate limit approaching for groq', 'Token burn +12%', 'Circuit breaker for scaleway', 'Pool rebalance done']
          const sevs: Array<'critical' | 'warning' | 'info' | 'success'> = ['critical', 'warning', 'info', 'success']
          const srcs = ['System', 'Gateway', 'Tokens', 'Governor', 'ModelRelay']
          return [{ id: nextId, severity: sevs[Math.floor(Math.random() * 4)], message: msgs[Math.floor(Math.random() * msgs.length)], source: srcs[Math.floor(Math.random() * srcs.length)], time: Date.now() }, ...prev.slice(0, 7)]
        })
      }
    }, 10000)
    return () => clearInterval(i)
  }, [])

  // Auto-scroll alerts
  useEffect(() => {
    if (alertListRef.current) alertListRef.current.scrollTop = 0
  }, [alerts])

  // Initialize notifications from alert data
  useEffect(() => {
    const now = Date.now()
    setNotifications(alertFeedData.map(a => ({
      id: a.id,
      severity: a.severity,
      message: a.message,
      source: a.source,
      time: now - a.offsetMs,
      read: false,
    })))
  }, [])

  // Sync new alerts to notifications
  useEffect(() => {
    if (alerts.length === 0) return
    const latestAlert = alerts[0]
    setNotifications(prev => {
      if (prev.some(n => n.id === latestAlert.id)) return prev
      return [{ ...latestAlert, read: false }, ...prev].slice(0, 20)
    })
  }, [alerts])

  // Update health metrics periodically — every 10 seconds
  useEffect(() => {
    const i = setInterval(() => {
      const getTrend = (): TrendDirection => Math.random() > 0.5 ? 'up' : 'down'
      setHealthMetrics(prev => ({
        cpu: {
          value: Math.max(5, Math.min(95, prev.cpu.value + Math.floor(Math.random() * 10) - 5)),
          trend: getTrend(),
          history: [...prev.cpu.history.slice(1), Math.max(5, Math.min(95, prev.cpu.value + Math.floor(Math.random() * 10) - 5))],
        },
        memory: {
          value: Math.max(30, Math.min(90, prev.memory.value + Math.floor(Math.random() * 6) - 3)),
          trend: getTrend(),
          history: [...prev.memory.history.slice(1), Math.max(30, Math.min(90, prev.memory.value + Math.floor(Math.random() * 6) - 3))],
        },
        diskIO: {
          value: Math.max(10, Math.min(80, prev.diskIO.value + Math.floor(Math.random() * 8) - 4)),
          trend: getTrend(),
          history: [...prev.diskIO.history.slice(1), Math.max(10, Math.min(80, prev.diskIO.value + Math.floor(Math.random() * 8) - 4))],
        },
        networkIO: {
          value: Math.max(20, Math.min(90, prev.networkIO.value + Math.floor(Math.random() * 10) - 5)),
          trend: getTrend(),
          history: [...prev.networkIO.history.slice(1), Math.max(20, Math.min(90, prev.networkIO.value + Math.floor(Math.random() * 10) - 5))],
        },
      }))
    }, 10000)
    return () => clearInterval(i)
  }, [])

  // Keyboard shortcut for command palette (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandOpen(prev => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Notification helpers
  const unreadCount = useMemo(() => notifications.filter(n => !n.read).length, [notifications])

  const markAllRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }, [])

  const clearAllNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const markAsRead = useCallback((id: number) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  }, [])

  // Run diagnostics
  const runDiagnostics = useCallback(() => {
    if (diagRunning) return
    setDiagRunning(true)
    setDiagProgress(0)
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 15 + 5
      if (progress >= 100) {
        progress = 100
        clearInterval(interval)
        setTimeout(() => {
          setDiagRunning(false)
          setDiagProgress(0)
        }, 800)
      }
      setDiagProgress(Math.min(100, Math.round(progress)))
    }, 400)
  }, [diagRunning])

  const errorRateColor = errorRate > 2 ? 'text-red-500' : errorRate > 1 ? 'text-yellow-500' : 'text-emerald-500'
  const alertSeverityConfig = {
    critical: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/30' },
    warning: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' },
    info: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
    success: { icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab />
      case 'architecture':
        return <FullArchitectureTab />
      case 'providers':
        return <ProvidersTab />
      case 'agents':
        return <AgentsTab />
      case 'gmr':
        return <GMRTab />
      case 'governor':
        return <GovernorTab />
      case 'vault':
        return <FullVaultTab />
      case 'research':
        return <FullResearchTab />
      case 'aichat':
        return <FullAIChatTab />
      case 'swarm':
        return <FullSwarmTab />
      case 'tokens':
        return <TokensTab />
      case 'ratelimits':
        return <FullRateLimitTab />
      case 'kpi':
        return <FullKpiTab />
      case 'stresslab':
        return <FullStressLabTab />
      default:
        return <OverviewTab />
    }
  }

  // ─── Overview Tab ─────────────────────────────
  function OverviewTab() {
    return (
      <div className="space-y-5">
        {/* System Status Header */}
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
          </span>
          <span className="text-sm font-medium animate-pulse text-emerald-600 dark:text-emerald-400">System Operational</span>
          <Badge variant="outline" className="text-[9px] bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-emerald-600/30 live-badge-glow">
            <span className="relative flex h-1.5 w-1.5 mr-1"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" /></span>
            LIVE
          </Badge>
        </div>

        {/* 8-Pillar Health Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {healthPillars.map((pillar) => (
            <Card key={pillar.name} className={cn(
              'glass-card-hover hover:scale-[1.03] cursor-default',
              pillar.status === 'degraded'
                ? 'border-yellow-600/30 bg-gradient-to-br from-yellow-600/5 to-transparent'
                : 'border-border/50 bg-gradient-to-br from-emerald-600/5 to-transparent'
            )}>
              <CardContent className="p-3 text-center">
                <div className="flex items-center justify-center gap-1 mb-1">
                  <span className="text-lg">{pillar.icon}</span>
                  <Badge variant="outline" className={cn(
                    'text-[7px] h-3.5 px-1',
                    pillar.status === 'healthy' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400'
                  )}>{pillar.status === 'healthy' ? 'OK' : 'WARN'}</Badge>
                </div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{pillar.name}</div>
                <div className={cn('text-lg font-bold tabular-nums', pillar.health >= 90 ? 'text-emerald-600 dark:text-emerald-400' : pillar.health >= 70 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400')}>
                  {pillar.health}%
                </div>
                <div className="mt-1 h-1 rounded-full bg-muted overflow-hidden">
                  <div className={cn('h-full rounded-full transition-all duration-700', pillar.health >= 90 ? 'bg-emerald-500' : pillar.health >= 70 ? 'bg-yellow-500' : 'bg-red-500')} style={{ width: `${pillar.health}%` }} />
                </div>
                <div className="text-[8px] text-muted-foreground/60 mt-1">{pillar.version}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Live Metrics */}
        <Card className="glass-card-hover border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 to-transparent">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Radio className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Live System Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Active Connections', value: activeConnections, unit: '', icon: Wifi, sparkData: [200, 220, 247, 230, 260, 247] },
                { label: 'Requests/sec', value: requestsPerSec, unit: 'req/s', icon: Activity, sparkData: rpsHistory },
                { label: 'Tokens/min', value: tokensPerMin, unit: 'tok/min', icon: Zap, sparkData: [1200, 1350, 1420, 1380, 1500, 1420] },
                { label: 'Error Rate', value: errorRate, unit: '%', icon: AlertCircle, sparkData: [0.5, 0.3, 0.4, 0.2, 0.3, 0.3] },
              ].map((m) => (
                <div key={m.label} className={cn('bg-gradient-to-br p-3 rounded-lg border border-border/30', m.label === 'Error Rate' ? (errorRate > 2 ? 'from-red-600/10 to-transparent' : errorRate > 1 ? 'from-yellow-600/10 to-transparent' : 'from-emerald-600/5 to-transparent') : 'from-emerald-600/5 to-transparent')}>
                  <div className="flex items-center gap-2 mb-1">
                    <m.icon className={cn('h-3.5 w-3.5', m.label === 'Error Rate' ? errorRateColor : 'text-emerald-600 dark:text-emerald-400')} />
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</span>
                  </div>
                  <div className="flex items-end gap-2">
                    <span className={cn('text-2xl font-bold tabular-nums', m.label === 'Error Rate' ? errorRateColor : 'text-emerald-600 dark:text-emerald-400')}>
                      {m.value.toLocaleString()}
                    </span>
                    <span className="text-[10px] text-muted-foreground mb-1">{m.unit}</span>
                  </div>
                  <div className="mt-1 h-6">
                    <SparklineSVG data={m.sparkData} color={m.label === 'Error Rate' ? (errorRate > 2 ? '#ef4444' : errorRate > 1 ? '#eab308' : '#10b981') : '#10b981'} height={24} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Network Topology & Alert Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="glass-card-hover border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Wifi className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Network Topology
                <Badge variant="outline" className="text-[9px] ml-auto">4 Layers</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <NetworkTopology />
              <div className="flex flex-wrap gap-3 mt-2">
                {[{ c: 'bg-emerald-500', l: 'Healthy' }, { c: 'bg-yellow-500', l: 'Degraded' }, { c: 'bg-blue-500', l: 'Mid Pool' }, { c: 'bg-orange-500', l: 'Fast Pool' }, { c: 'bg-purple-500', l: 'Providers' }].map(g => (
                  <div key={g.l} className="flex items-center gap-1.5"><span className={cn('h-2 w-2 rounded-full', g.c)} /><span className="text-[9px] text-muted-foreground">{g.l}</span></div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card-hover border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Bell className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Alert Feed
                <Badge variant="outline" className="text-[9px] ml-auto bg-yellow-600/10 text-yellow-600 dark:text-yellow-400 border-yellow-600/30">
                  {alerts.filter(a => a.severity === 'critical' || a.severity === 'warning').length} Active
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div ref={alertListRef} className="space-y-1.5 max-h-[260px] overflow-y-auto custom-scrollbar">
                {alerts.slice(0, 5).map((alert) => {
                  const config = alertSeverityConfig[alert.severity]
                  const Icon = config.icon
                  return (
                    <div key={alert.id} className={cn('flex items-center gap-2.5 p-2 rounded-lg border transition-opacity duration-300', config.bg, config.border)}>
                      <Icon className={cn('h-3.5 w-3.5 shrink-0', config.color)} />
                      <span className="text-xs flex-1 truncate">{alert.message}</span>
                      <Badge variant="outline" className="text-[8px] shrink-0">{alert.source}</Badge>
                      <span className="text-[9px] text-muted-foreground whitespace-nowrap shrink-0" suppressHydrationWarning>{mounted ? getRelativeTime(alert.time) : '...'}</span>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* System Performance Chart */}
        <Card className="glass-card-hover border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              System Performance (24h)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <AreaChartSVG data={systemPerformanceData} width={600} height={200} />
          </CardContent>
        </Card>

        {/* Request Volume & Agent Task Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="glass-card-hover border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Request Volume
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <MiniBarChart data={requestVolumeData.map(d => ({ label: d.hour, value: d.requests }))} height={120} />
            </CardContent>
          </Card>

          <Card className="glass-card-hover border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Target className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Agent Task Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="flex items-center gap-6">
                <DonutChart segments={[
                  { value: 47, color: '#10b981', label: 'Research' },
                  { value: 31, color: '#3b82f6', label: 'Coding' },
                  { value: 38, color: '#f97316', label: 'Analysis' },
                  { value: 12, color: '#8b5cf6', label: 'Governance' },
                ]} size={100} strokeWidth={12} />
                <div className="space-y-2 flex-1">
                  {[{ label: 'Research', value: 47, color: 'bg-emerald-500' }, { label: 'Coding', value: 31, color: 'bg-blue-500' }, { label: 'Analysis', value: 38, color: 'bg-orange-500' }, { label: 'Governance', value: 12, color: 'bg-purple-500' }].map(d => (
                    <div key={d.label} className="flex items-center gap-2">
                      <span className={cn('h-2 w-2 rounded-full shrink-0', d.color)} />
                      <span className="text-xs text-muted-foreground flex-1">{d.label}</span>
                      <span className="text-xs font-bold tabular-nums">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* System Health Diagnostics */}
        <Card className="glass-card-hover border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 to-transparent">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Stethoscope className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              System Health Diagnostics
              {diagRunning && (
                <Badge className="text-[9px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 animate-pulse">
                  Scanning...
                </Badge>
              )}
              <Button
                size="sm"
                variant="outline"
                className="ml-auto h-6 text-[9px] gap-1 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
                onClick={runDiagnostics}
                disabled={diagRunning}
              >
                {diagRunning ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                {diagRunning ? `${diagProgress}%` : 'Run Diagnostics'}
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {diagRunning && (
              <div className="mb-3">
                <Progress value={diagProgress} className="h-1.5 [&>div]:bg-emerald-500" />
              </div>
            )}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { key: 'cpu', label: 'CPU Usage', icon: Cpu, unit: '%', data: healthMetrics.cpu },
                { key: 'memory', label: 'Memory', icon: HardDrive, unit: '%', data: healthMetrics.memory },
                { key: 'diskIO', label: 'Disk I/O', icon: Disc, unit: 'MB/s', data: healthMetrics.diskIO },
                { key: 'networkIO', label: 'Network I/O', icon: RadioTower, unit: 'MB/s', data: healthMetrics.networkIO },
              ].map((metric) => {
                const val = metric.data.value
                const color = val >= 80 ? 'red' : val >= 60 ? 'yellow' : 'emerald'
                const TrendIcon = metric.data.trend === 'up' ? ArrowUp : ArrowDown
                return (
                  <div key={metric.key} className={cn(
                    'p-3 rounded-lg border transition-all duration-500',
                    color === 'red' ? 'border-red-500/30 bg-red-500/5' :
                    color === 'yellow' ? 'border-yellow-500/30 bg-yellow-500/5' :
                    'border-emerald-500/30 bg-emerald-500/5'
                  )}>
                    <div className="flex items-center gap-2 mb-2">
                      <metric.icon className={cn('h-3.5 w-3.5', color === 'red' ? 'text-red-500' : color === 'yellow' ? 'text-yellow-500' : 'text-emerald-500')} />
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{metric.label}</span>
                      <TrendIcon className={cn(
                        'h-3 w-3 ml-auto',
                        metric.data.trend === 'up'
                          ? (val >= 80 ? 'text-red-500' : 'text-emerald-500')
                          : 'text-yellow-500'
                      )} />
                    </div>
                    <div className="flex items-end gap-1 mb-2">
                      <span className={cn('text-2xl font-bold tabular-nums smooth-number', color === 'red' ? 'text-red-500' : color === 'yellow' ? 'text-yellow-500' : 'text-emerald-500')}>
                        {val}
                      </span>
                      <span className="text-[9px] text-muted-foreground mb-1">{metric.unit}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className={cn('h-full rounded-full transition-all duration-700', color === 'red' ? 'bg-red-500' : color === 'yellow' ? 'bg-yellow-500' : 'bg-emerald-500')}
                        style={{ width: `${val}%` }}
                      />
                    </div>
                    <div className="mt-2 h-5">
                      <SparklineSVG
                        data={metric.data.history}
                        color={color === 'red' ? '#ef4444' : color === 'yellow' ? '#eab308' : '#10b981'}
                        height={20}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Activity Timeline & Constitutional Rules */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Activity Timeline */}
          <Card className="glass-card-hover border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Activity Timeline
                <Badge variant="outline" className="text-[9px] ml-auto">Live</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="max-h-[280px] overflow-y-auto custom-scrollbar">
                <div className="relative pl-6 space-y-0">
                  {/* Timeline line */}
                  <div className="absolute left-[9px] top-1 bottom-1 w-px bg-border" />

                  {[
                    { time: '2m ago', type: 'success', icon: CheckCircle2, desc: 'Health check passed — all pillars OK', source: 'Monitor' },
                    { time: '5m ago', type: 'info', icon: Info, desc: 'Model failover triggered for gemma-fast', source: 'ModelRelay' },
                    { time: '12m ago', type: 'warning', icon: AlertTriangle, desc: 'Memory usage approaching 80%', source: 'System' },
                    { time: '18m ago', type: 'success', icon: CheckCircle2, desc: 'Constitutional check passed for all rules', source: 'Governor' },
                    { time: '25m ago', type: 'info', icon: Info, desc: 'Token budget reset for new cycle', source: 'Tokens' },
                    { time: '32m ago', type: 'critical', icon: XCircle, desc: 'Provider dashscope rate limit exceeded', source: 'Gateway' },
                    { time: '45m ago', type: 'warning', icon: AlertTriangle, desc: 'Agent worker-2 trust score below 0.8', source: 'Governor' },
                    { time: '1h ago', type: 'success', icon: CheckCircle2, desc: 'Pool rebalance completed successfully', source: 'GMR' },
                  ].map((event, i) => {
                    const colorMap = {
                      success: { dot: 'bg-emerald-500', ring: 'ring-emerald-500/20', text: 'text-emerald-600 dark:text-emerald-400' },
                      warning: { dot: 'bg-yellow-500', ring: 'ring-yellow-500/20', text: 'text-yellow-600 dark:text-yellow-400' },
                      critical: { dot: 'bg-red-500', ring: 'ring-red-500/20', text: 'text-red-600 dark:text-red-400' },
                      info: { dot: 'bg-blue-500', ring: 'ring-blue-500/20', text: 'text-blue-600 dark:text-blue-400' },
                    }
                    const c = colorMap[event.type as keyof typeof colorMap]
                    return (
                      <div key={i} className="relative pb-3">
                        {/* Timeline dot */}
                        <div className={cn('absolute -left-6 top-0.5 h-[18px] w-[18px] rounded-full border-2 border-background ring-2 flex items-center justify-center', c.dot, c.ring)}>
                          <div className="h-1.5 w-1.5 rounded-full bg-white dark:bg-background" />
                        </div>
                        <div className="flex items-start gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <event.icon className={cn('h-3 w-3 shrink-0', c.text)} />
                              <span className="text-xs font-medium truncate">{event.desc}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-[7px] h-4">{event.source}</Badge>
                              <span className="text-[9px] text-muted-foreground" suppressHydrationWarning>{mounted ? event.time : '...'}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Constitutional Rules */}
          <Card className="glass-card-hover border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Scale className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Constitutional Rules
                <Badge variant="outline" className="text-[9px] ml-auto">{constitutionalRules.length} Active</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {constitutionalRules.map((rule) => (
                  <div key={rule.id} className="flex items-center gap-2 p-2 rounded-lg border border-border/30 bg-muted/20">
                    <Badge variant="outline" className={cn('text-[8px] shrink-0', rule.severity === 'critical' ? 'border-red-500/30 text-red-500' : rule.severity === 'warning' ? 'border-yellow-500/30 text-yellow-500' : 'border-blue-500/30 text-blue-500')}>
                      {rule.severity.toUpperCase()}
                    </Badge>
                    <span className="text-[10px] font-mono text-muted-foreground shrink-0">{rule.id}</span>
                    <span className="text-xs truncate flex-1">{rule.name}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // ─── Providers Tab ────────────────────────────
  function ProvidersTab() {
    const activeCount = providers.filter(p => p.status === 'active').length
    const degradedCount = providers.filter(p => p.status === 'degraded').length
    return (
      <div className="space-y-5">
        {/* Provider Health Summary */}
        <Card className="glass-card-hover border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 to-transparent">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {[
                { label: 'Active', value: activeCount, color: 'text-emerald-500' },
                { label: 'Degraded', value: degradedCount, color: 'text-yellow-500' },
                { label: 'Inactive', value: providers.filter(p => p.status === 'inactive').length, color: 'text-red-500' },
                { label: 'Total Models', value: providers.reduce((s, p) => s + p.models, 0), color: 'text-blue-500' },
                { label: 'Avg Latency', value: `${Math.round(providers.filter(p => p.latency > 0).reduce((s, p) => s + p.latency, 0) / providers.filter(p => p.latency > 0).length)}ms`, color: 'text-orange-500' },
              ].map(s => (
                <div key={s.label} className="text-center">
                  <div className={cn('text-2xl font-bold tabular-nums', s.color)}>{s.value}</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{s.label}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Provider Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {providers.map((p) => (
            <Card key={p.name} className={cn(
              'glass-card-hover hover:scale-[1.02] transition-all duration-200',
              p.status === 'degraded' ? 'border-yellow-600/30' : p.status === 'inactive' ? 'border-red-600/20' : p.status === 'unknown' ? 'border-gray-500/20' : 'border-border/50',
              p.status === 'degraded' ? 'bg-gradient-to-br from-yellow-600/5 to-transparent' : ''
            )}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={cn('h-2 w-2 rounded-full shrink-0', p.status === 'active' ? 'bg-emerald-500 status-pulse-green' : p.status === 'degraded' ? 'bg-yellow-500 animate-pulse' : p.status === 'inactive' ? 'bg-red-500' : 'bg-gray-400')} />
                  <span className="text-sm font-semibold truncate flex-1">{p.name}</span>
                  <Badge variant="outline" className={cn('text-[9px]', p.pool === 'PREMIUM' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : p.pool === 'FAST' ? 'border-orange-600/30 text-orange-600 dark:text-orange-400' : 'border-blue-600/30 text-blue-600 dark:text-blue-400')}>
                    {p.pool}
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-[10px] text-muted-foreground">Models</div>
                    <div className="text-sm font-bold tabular-nums">{p.models}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-muted-foreground">Latency</div>
                    <div className={cn('text-sm font-bold tabular-nums', p.latency > 200 ? 'text-red-500' : p.latency > 100 ? 'text-yellow-500' : 'text-emerald-500')}>
                      {p.latency > 0 ? `${p.latency}ms` : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-muted-foreground">Trust</div>
                    <div className={cn('text-sm font-bold tabular-nums', p.trust >= 0.9 ? 'text-emerald-500' : p.trust >= 0.7 ? 'text-yellow-500' : 'text-red-500')}>
                      {(p.trust * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
                {p.latency > 0 && (
                  <div className="mt-2 h-1 rounded-full bg-muted overflow-hidden">
                    <div className={cn('h-full rounded-full', p.latency > 200 ? 'bg-red-500' : p.latency > 100 ? 'bg-yellow-500' : 'bg-emerald-500')} style={{ width: `${Math.min(p.latency / 3, 100)}%` }} />
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  // ─── Agents Tab ───────────────────────────────
  function AgentsTab() {
    return (
      <div className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {agents.map((a) => (
            <Card key={a.name} className={cn('glass-card-hover border-border/50 hover:scale-[1.02] transition-all duration-200', a.status === 'warning' ? 'border-l-2 border-l-yellow-500' : 'border-l-2 border-l-emerald-500')}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className={cn('h-2.5 w-2.5 rounded-full', a.status === 'active' ? 'bg-emerald-500 status-pulse-green' : 'bg-yellow-500 animate-pulse')} />
                  <span className="text-sm font-bold font-mono">{a.name}</span>
                  <Badge variant="outline" className={cn('text-[9px] ml-auto', a.status === 'active' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400')}>
                    {a.status.toUpperCase()}
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><span className="text-[10px] text-muted-foreground block">Domain</span><span className="text-xs font-medium">{a.domain}</span></div>
                  <div><span className="text-[10px] text-muted-foreground block">Model</span><span className="text-xs font-mono">{a.model}</span></div>
                  <div><span className="text-[10px] text-muted-foreground block">Tasks</span><span className="text-xs font-bold tabular-nums">{a.tasks}</span></div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Trust Score</span>
                    <div className="flex items-center gap-1.5">
                      <span className={cn('text-xs font-bold tabular-nums', a.trust >= 0.9 ? 'text-emerald-500' : 'text-yellow-500')}>{(a.trust * 100).toFixed(0)}%</span>
                      <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                        <div className={cn('h-full rounded-full', a.trust >= 0.9 ? 'bg-emerald-500' : 'bg-yellow-500')} style={{ width: `${a.trust * 100}%` }} />
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Agent Activity Log */}
        <Card className="glass-card-hover border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Recent Agent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
              {[
                { agent: 'worker-1', action: 'Completed research task #47', time: '2m ago', status: 'success' },
                { agent: 'coordinator', action: 'Constitutional check passed', time: '5m ago', status: 'success' },
                { agent: 'worker-2', action: 'Trust score dropped below 0.8', time: '8m ago', status: 'warning' },
                { agent: 'worker-3', action: 'Model failover: gemma → gemma-fast', time: '12m ago', status: 'info' },
                { agent: 'worker-1', action: 'Token budget at 73.4%', time: '15m ago', status: 'info' },
                { agent: 'coordinator', action: 'Blocked CRITICAL action per CR-002', time: '20m ago', status: 'warning' },
              ].map((log, i) => (
                <div key={i} className={cn('flex items-center gap-3 p-2 rounded-lg border border-border/20', log.status === 'warning' ? 'bg-yellow-500/5' : log.status === 'success' ? 'bg-emerald-500/5' : 'bg-blue-500/5')}>
                  <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', log.status === 'success' ? 'bg-emerald-500' : log.status === 'warning' ? 'bg-yellow-500' : 'bg-blue-500')} />
                  <span className="text-[10px] font-mono text-muted-foreground w-20 shrink-0">{log.agent}</span>
                  <span className="text-xs flex-1 truncate">{log.action}</span>
                  <span className="text-[9px] text-muted-foreground whitespace-nowrap" suppressHydrationWarning>{mounted ? log.time : '...'}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ─── GMR Router Tab ───────────────────────────
  function GMRTab() {
    return (
      <div className="space-y-5">
        {/* Model Pools */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { name: 'PREMIUM', models: ['trinity-large-preview', 'minimax-m2.5'], health: 97, color: 'emerald' },
            { name: 'MID', models: ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'], health: 89, color: 'blue' },
            { name: 'FAST', models: ['gemma-fast', 'nemotron-3-super'], health: 94, color: 'orange' },
          ].map(pool => (
            <Card key={pool.name} className={cn('glass-card-hover border-border/50', pool.color === 'emerald' ? 'bg-gradient-to-br from-emerald-600/5 to-transparent' : pool.color === 'blue' ? 'bg-gradient-to-br from-blue-600/5 to-transparent' : 'bg-gradient-to-br from-orange-600/5 to-transparent')}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <Badge variant="outline" className={cn('text-[10px]', pool.color === 'emerald' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : pool.color === 'blue' ? 'border-blue-600/30 text-blue-600 dark:text-blue-400' : 'border-orange-600/30 text-orange-600 dark:text-orange-400')}>
                    {pool.name}
                  </Badge>
                  <span className={cn('text-lg font-bold tabular-nums', pool.health >= 95 ? 'text-emerald-500' : pool.health >= 80 ? 'text-yellow-500' : 'text-red-500')}>{pool.health}%</span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden mb-3">
                  <div className={cn('h-full rounded-full transition-all duration-700', pool.color === 'emerald' ? 'bg-emerald-500' : pool.color === 'blue' ? 'bg-blue-500' : 'bg-orange-500')} style={{ width: `${pool.health}%` }} />
                </div>
                <div className="space-y-1">
                  {pool.models.map(m => (
                    <div key={m} className="flex items-center gap-1.5 text-xs">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      <span className="font-mono text-[11px]">{m}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* GMR Routing Strategy */}
        <Card className="glass-card-hover border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Network className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Routing Strategy
              <Badge variant="outline" className="text-[9px] ml-auto">quota_aware</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Strategy', value: 'Quota-Aware' },
                { label: 'Failover', value: 'Enabled' },
                { label: 'Circuit Breaker', value: 'Active' },
                { label: 'Rebalance', value: 'Every 5m' },
              ].map(s => (
                <div key={s.label} className="p-2 rounded-lg border border-border/30 bg-muted/20">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{s.label}</div>
                  <div className="text-sm font-semibold mt-0.5">{s.value}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ─── Governor Tab ─────────────────────────────
  function GovernorTab() {
    return (
      <div className="space-y-5">
        {/* Governor Status */}
        <Card className="glass-card-hover border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <div className="h-14 w-14 rounded-xl bg-emerald-600/10 border border-emerald-600/30 flex items-center justify-center">
                <Shield className="h-7 w-7 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold">Constitutional Governor</span>
                  <Badge className="bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-emerald-600/30 text-[9px]">v4.0.0</Badge>
                </div>
                <div className="text-sm text-muted-foreground mt-0.5">Enforcing 6 constitutional rules across 4 agents</div>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-[10px] text-muted-foreground">Trust Score: <span className="text-emerald-500 font-bold">0.95</span></span>
                  <span className="text-[10px] text-muted-foreground">Actions Blocked: <span className="text-yellow-500 font-bold">3</span></span>
                  <span className="text-[10px] text-muted-foreground">Uptime: <span className="text-emerald-500 font-bold">4h 23m</span></span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Constitutional Rules */}
        <Card className="glass-card-hover border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Scale className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Constitutional Rules
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {constitutionalRules.map((rule) => (
                <div key={rule.id} className={cn('flex items-center gap-3 p-3 rounded-lg border', rule.severity === 'critical' ? 'border-red-500/20 bg-red-500/5' : rule.severity === 'warning' ? 'border-yellow-500/20 bg-yellow-500/5' : 'border-blue-500/20 bg-blue-500/5')}>
                  <Badge variant="outline" className={cn('text-[8px] shrink-0', rule.severity === 'critical' ? 'border-red-500/30 text-red-500' : rule.severity === 'warning' ? 'border-yellow-500/30 text-yellow-500' : 'border-blue-500/30 text-blue-500')}>
                    {rule.severity.toUpperCase()}
                  </Badge>
                  <span className="text-[10px] font-mono text-muted-foreground shrink-0">{rule.id}</span>
                  <span className="text-sm flex-1">{rule.name}</span>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Governance Log */}
        <Card className="glass-card-hover border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Governance Log
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
              {[
                { action: 'BLOCKED', target: 'worker-2 → destructive action', rule: 'CR-002', time: '5m ago' },
                { action: 'APPROVED', target: 'worker-1 → research task #47', rule: 'CR-005', time: '12m ago' },
                { action: 'ENFORCED', target: 'Token budget cap at 100k', rule: 'CR-003', time: '25m ago' },
                { action: 'AUDITED', target: 'Trust score decay cycle', rule: 'CR-004', time: '45m ago' },
                { action: 'BLOCKED', target: 'worker-3 → unattended modification', rule: 'CR-001', time: '1h ago' },
              ].map((log, i) => (
                <div key={i} className="flex items-center gap-2 p-2 rounded border border-border/20 text-xs">
                  <Badge variant="outline" className={cn('text-[8px] shrink-0', log.action === 'BLOCKED' ? 'border-red-500/30 text-red-500' : log.action === 'APPROVED' ? 'border-emerald-500/30 text-emerald-500' : 'border-blue-500/30 text-blue-500')}>
                    {log.action}
                  </Badge>
                  <span className="flex-1 truncate">{log.target}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">{log.rule}</span>
                  <span className="text-[9px] text-muted-foreground" suppressHydrationWarning>{mounted ? log.time : '...'}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ─── Research Tab: Now uses FullResearchTab via dynamic import (ssr: false) ──

  // ─── Tokens Tab ───────────────────────────────
  function TokensTab() {
    const tokenBudget = { used: 73450, total: 100000, session: 23400, sessionTotal: 50000 }
    const pct = Math.round((tokenBudget.used / tokenBudget.total) * 100)
    const sessionPct = Math.round((tokenBudget.session / tokenBudget.sessionTotal) * 100)
    return (
      <div className="space-y-5">
        {/* Token Budget Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card className={cn('glass-card-hover border-border/50', pct > 80 ? 'budget-alert-pulse border-red-600/30' : '')}>
            <CardContent className="p-4">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Global Token Budget</div>
              <div className="flex items-end gap-2 mb-2">
                <span className="text-3xl font-bold tabular-nums">{tokenBudget.used.toLocaleString()}</span>
                <span className="text-sm text-muted-foreground mb-1">/ {tokenBudget.total.toLocaleString()}</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className={cn('h-full rounded-full token-flow-bar', pct > 80 ? 'bg-red-500' : pct > 60 ? 'bg-yellow-500' : 'bg-emerald-500')} style={{ width: `${pct}%` }} />
              </div>
              <div className="flex justify-between mt-1.5 text-[10px] text-muted-foreground">
                <span>{pct}% used</span>
                <span>{(tokenBudget.total - tokenBudget.used).toLocaleString()} remaining</span>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card-hover border-border/50">
            <CardContent className="p-4">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Session Budget</div>
              <div className="flex items-end gap-2 mb-2">
                <span className="text-3xl font-bold tabular-nums">{tokenBudget.session.toLocaleString()}</span>
                <span className="text-sm text-muted-foreground mb-1">/ {tokenBudget.sessionTotal.toLocaleString()}</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className={cn('h-full rounded-full', sessionPct > 80 ? 'bg-red-500' : sessionPct > 60 ? 'bg-yellow-500' : 'bg-emerald-500')} style={{ width: `${sessionPct}%` }} />
              </div>
              <div className="flex justify-between mt-1.5 text-[10px] text-muted-foreground">
                <span>{sessionPct}% used</span>
                <span>{(tokenBudget.sessionTotal - tokenBudget.session).toLocaleString()} remaining</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Token Consumption by Model */}
        <Card className="glass-card-hover border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Zap className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Token Consumption by Model
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {[
                { model: 'trinity-large-preview', tokens: 28400, pct: 39, pool: 'PREMIUM' },
                { model: 'qwen3-coder', tokens: 18200, pct: 25, pool: 'MID' },
                { model: 'glm-4.7', tokens: 12350, pct: 17, pool: 'PREMIUM' },
                { model: 'gemma-fast', tokens: 8900, pct: 12, pool: 'FAST' },
                { model: 'nemotron-3-super', tokens: 5600, pct: 7, pool: 'FAST' },
              ].map(m => (
                <div key={m.model} className="flex items-center gap-3">
                  <span className="font-mono text-xs w-36 shrink-0 truncate">{m.model}</span>
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div className={cn('h-full rounded-full', m.pool === 'PREMIUM' ? 'bg-emerald-500' : m.pool === 'FAST' ? 'bg-orange-500' : 'bg-blue-500')} style={{ width: `${m.pct}%` }} />
                  </div>
                  <span className="text-xs font-bold tabular-nums w-12 text-right">{m.tokens.toLocaleString()}</span>
                  <Badge variant="outline" className={cn('text-[8px] shrink-0', m.pool === 'PREMIUM' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : m.pool === 'FAST' ? 'border-orange-600/30 text-orange-600 dark:text-orange-400' : 'border-blue-600/30 text-blue-600 dark:text-blue-400')}>
                    {m.pool}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ─── StressLab Tab: Now uses FullStressLabTab via dynamic import (ssr: false) ──

  // ─── Render ───────────────────────────────────
  // Mount gate: prevent hydration mismatch by waiting for client mount
  if (!mounted) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-emerald-600/10 border border-emerald-600/30 flex items-center justify-center">
            <Shield className="h-6 w-6 text-emerald-600" />
          </div>
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
            <span className="text-sm text-muted-foreground">Initializing NEXUS-OS...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-56 flex-col border-r border-border/60 bg-card/80 backdrop-blur-md">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border/40">
          <div className="h-8 w-8 rounded-lg bg-emerald-600/10 border border-emerald-600/30 flex items-center justify-center">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <div className="text-sm font-bold gradient-text">NEXUS OS</div>
            <div className="text-[9px] text-muted-foreground">v3.1 Command Center</div>
          </div>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-0.5">
          {['Core', 'Routing', 'Governance', 'Intelligence', 'Operations', 'Metrics', 'Testing'].map(group => {
            const groupTabs = TABS.filter(t => t.group === group)
            if (groupTabs.length === 0) return null
            return (
              <div key={group} className="sidebar-group-bg mb-2">
                <div className="text-[9px] font-semibold text-muted-foreground/60 uppercase tracking-widest px-2 py-1.5">{group}</div>
                {groupTabs.map(tab => {
                  const Icon = tab.icon
                  return (
                    <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        'sidebar-item-hover w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs transition-all duration-200',
                        activeTab === tab.id
                          ? 'sidebar-active-item bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-600/20'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                      )}>
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      {tab.label}
                      {tab.id === 'stresslab' && <Badge variant="outline" className="text-[7px] ml-auto border-yellow-500/30 text-yellow-500">1 RUN</Badge>}
                    </button>
                  )
                })}
              </div>
            )
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-border/40">
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 pulse-dot" />
            <span>Session: <span className="font-mono tabular-nums" suppressHydrationWarning>{uptime}</span></span>
          </div>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSidebarOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-card border-r border-border flex flex-col animate-slide-up">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/40">
              <div className="text-sm font-bold gradient-text">NEXUS OS v3.1</div>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSidebarOpen(false)}><X className="h-4 w-4" /></Button>
            </div>
            <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
              {TABS.map(tab => {
                const Icon = tab.icon
                return (
                  <button key={tab.id} onClick={() => { setActiveTab(tab.id); setSidebarOpen(false) }}
                    className={cn('w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-all', activeTab === tab.id ? 'bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50')}>
                    <Icon className="h-4 w-4 shrink-0" />
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </aside>
        </div>
      )}

      {/* Main Area */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <header className="header-gradient-border relative flex h-12 items-center gap-3 border-b border-border/60 bg-card/80 backdrop-blur-md px-4">

          <Button variant="ghost" size="icon" className="h-8 w-8 md:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-4 w-4" />
          </Button>

          <div className="hidden sm:flex items-center gap-1.5">
            <span className="relative flex h-2 w-2 online-status-glow"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" /></span>
            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">Online</span>
          </div>

          <div className="hidden md:flex items-center gap-1 text-[10px] text-muted-foreground">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">NEXUS OS</span>
            <ChevronRight className="h-3 w-3 text-muted-foreground/40" />
            <span>{TABS.find(t => t.id === activeTab)?.group}</span>
            <ChevronRight className="h-3 w-3 text-muted-foreground/40" />
            <span className="font-medium text-foreground">{TABS.find(t => t.id === activeTab)?.label}</span>
          </div>

          <div className="flex-1 md:hidden text-sm font-semibold truncate gradient-text">
            {TABS.find(t => t.id === activeTab)?.label}
          </div>

          {/* Token Budget Indicator */}
          <div className="hidden sm:flex items-center gap-2 rounded-lg border border-emerald-600/10 px-2.5 py-1">
            <div className="h-5 w-5 rounded-full border-2 border-emerald-500 flex items-center justify-center text-[7px] font-bold text-emerald-500">73</div>
            <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 tabular-nums">73,450</span>
            <span className="text-[9px] text-muted-foreground">/ 100k</span>
          </div>

          {/* RPS Badge */}
          <Badge variant="outline" className="gap-1 text-[10px] font-mono hidden sm:flex">
            <Activity className="h-3 w-3 text-emerald-500" />
            {requestsPerSec} req/s
          </Badge>

          {/* Clock */}
          <span className="hidden md:inline text-[10px] font-mono tabular-nums text-muted-foreground clock-digit" suppressHydrationWarning>{clock}</span>

          {/* Notification Center */}
          <Popover open={notifOpen} onOpenChange={setNotifOpen}>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7 relative">
                <Bell className="h-3.5 w-3.5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-red-500 text-[7px] font-bold text-white">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-0" align="end" sideOffset={8}>
              <div className="flex items-center justify-between border-b px-3 py-2">
                <div className="flex items-center gap-2">
                  <Bell className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                  <span className="text-xs font-semibold">Notifications</span>
                  {unreadCount > 0 && (
                    <Badge className="text-[8px] bg-red-500/15 text-red-600 dark:text-red-400 border-0 px-1.5">{unreadCount} new</Badge>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {unreadCount > 0 && (
                    <Button variant="ghost" size="sm" className="h-6 text-[9px] px-1.5 gap-0.5" onClick={markAllRead}>
                      <CheckCheck className="h-3 w-3" /> Read all
                    </Button>
                  )}
                  {notifications.length > 0 && (
                    <Button variant="ghost" size="sm" className="h-6 text-[9px] px-1.5 gap-0.5 text-red-500 hover:text-red-400" onClick={clearAllNotifications}>
                      <Trash2 className="h-3 w-3" /> Clear
                    </Button>
                  )}
                </div>
              </div>
              <ScrollArea className="max-h-[300px]">
                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 gap-2">
                    <Bell className="h-6 w-6 text-muted-foreground/30" />
                    <span className="text-xs text-muted-foreground">No notifications</span>
                  </div>
                ) : (
                  <div className="divide-y divide-border/50">
                    {notifications.slice(0, 10).map((notif) => {
                      const config = alertSeverityConfig[notif.severity]
                      const Icon = config.icon
                      return (
                        <button
                          key={notif.id}
                          className={cn(
                            'w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-accent/30 transition-colors',
                            !notif.read && 'bg-emerald-500/5'
                          )}
                          onClick={() => markAsRead(notif.id)}
                        >
                          <Icon className={cn('h-3.5 w-3.5 shrink-0 mt-0.5', config.color)} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className={cn('text-xs', !notif.read && 'font-semibold')}>{notif.message}</span>
                              {!notif.read && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              <Badge variant="outline" className="text-[7px] h-3.5 px-1">{notif.source}</Badge>
                              <span className="text-[9px] text-muted-foreground" suppressHydrationWarning>{mounted ? getRelativeTime(notif.time) : '...'}</span>
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </ScrollArea>
            </PopoverContent>
          </Popover>

          {/* Search / Command Palette Trigger */}
          <Button variant="ghost" size="sm" className="h-7 gap-1.5 text-[10px] text-muted-foreground hidden sm:flex" onClick={() => setCommandOpen(true)}>
            <Search className="h-3 w-3" />
            <span className="hidden lg:inline">Search...</span>
            <kbd className="hidden lg:inline-flex h-4 items-center gap-0.5 rounded border border-border/50 bg-muted px-1 text-[8px] font-mono">⌘K</kbd>
          </Button>

          {/* Theme Toggle */}
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            <Sun className="h-3.5 w-3.5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-3.5 w-3.5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
        </header>

        {/* Content */}
        <main className="relative flex-1 overflow-y-auto overflow-x-hidden bg-background">
          <div className="pointer-events-none absolute inset-0 grid-pattern-animated opacity-40" />
          <div className="relative z-10 p-4 md:p-6 tab-content-transition min-h-[50vh]" key={activeTab}>
            {renderTabContent()}
          </div>
        </main>

        {/* Footer */}
        <footer className="footer-gradient-top footer-bg-gradient relative shrink-0 flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-2">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">NEXUS OS v3.1</span>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400"><Heart className="h-3 w-3 fill-emerald-500/80 animate-pulse" />Operational</span>
            <span className="text-border hidden sm:inline">|</span>
            <span className="hidden sm:inline">5 agents/hr · 20 API/session · 2 concurrent</span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="hidden md:flex items-center gap-1.5">
              <Cpu className="h-3 w-3" /><span className="text-[9px] tabular-nums font-bold text-emerald-600 dark:text-emerald-400">34%</span>
              <span className="text-border mx-1">|</span>
              <HardDrive className="h-3 w-3" /><span className="text-[9px] tabular-nums font-bold text-yellow-600 dark:text-yellow-400">58%</span>
              <span className="text-border mx-1">|</span>
              <Zap className="h-3 w-3" /><span className="text-[9px] tabular-nums font-bold text-emerald-600 dark:text-emerald-400">42ms</span>
            </span>
            <span className="text-border">|</span>
            <span className="font-mono text-[10px] tabular-nums" suppressHydrationWarning>Session: {uptime}</span>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500 live-pulse-indicator" />Live</span>
          </div>
        </footer>
      </div>

      {/* AI Assistant FAB */}
      {activeTab !== 'aichat' && (
        <button
          onClick={() => setActiveTab('aichat')}
          className="interactive-hover fixed bottom-6 right-6 z-50 h-12 w-12 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/25 flex items-center justify-center transition-all duration-200 hover:scale-110 group"
          aria-label="Open AI Assistant"
        >
          <Brain className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-300" />
          </span>
        </button>
      )}

      {/* Quick Stats Floating Widget */}
      <QuickStatsWidget />

      {/* Command Palette (Cmd+K / Ctrl+K) */}
      <CommandDialog open={commandOpen} onOpenChange={setCommandOpen} title="NEXUS OS Command Palette" description="Search tabs, settings, and documentation">
        <CommandInput placeholder="Search tabs, settings, actions..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Navigation">
            {TABS.map(tab => {
              const Icon = tab.icon
              return (
                <CommandItem
                  key={tab.id}
                  value={`${tab.label} ${tab.group}`}
                  onSelect={() => { setActiveTab(tab.id); setCommandOpen(false) }}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                  <Badge variant="outline" className="text-[8px] ml-1">{tab.group}</Badge>
                </CommandItem>
              )
            })}
          </CommandGroup>
          <CommandGroup heading="Quick Actions">
            <CommandItem value="Run Diagnostics" onSelect={() => { runDiagnostics(); setCommandOpen(false) }}>
              <Stethoscope className="h-4 w-4" />
              <span>Run System Diagnostics</span>
            </CommandItem>
            <CommandItem value="Toggle Theme" onSelect={() => { setTheme(theme === 'dark' ? 'light' : 'dark'); setCommandOpen(false) }}>
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              <span>Toggle Theme</span>
              <CommandShortcut>⌘D</CommandShortcut>
            </CommandItem>
            <CommandItem value="Mark All Notifications Read" onSelect={() => { markAllRead(); setCommandOpen(false) }}>
              <CheckCheck className="h-4 w-4" />
              <span>Mark All Notifications Read</span>
            </CommandItem>
            <CommandItem value="Clear Notifications" onSelect={() => { clearAllNotifications(); setCommandOpen(false) }}>
              <Trash2 className="h-4 w-4" />
              <span>Clear All Notifications</span>
            </CommandItem>
          </CommandGroup>
          <CommandGroup heading="Documentation">
            <CommandItem value="Architecture Overview" onSelect={() => { setActiveTab('architecture'); setCommandOpen(false) }}>
              <LayoutGrid className="h-4 w-4" />
              <span>Architecture Overview</span>
              <CommandShortcut>Docs</CommandShortcut>
            </CommandItem>
            <CommandItem value="API Reference" onSelect={() => { setActiveTab('providers'); setCommandOpen(false) }}>
              <Server className="h-4 w-4" />
              <span>API & Provider Reference</span>
              <CommandShortcut>Docs</CommandShortcut>
            </CommandItem>
            <CommandItem value="Constitutional Rules" onSelect={() => { setActiveTab('governor'); setCommandOpen(false) }}>
              <Shield className="h-4 w-4" />
              <span>Constitutional Rules & Governance</span>
              <CommandShortcut>Docs</CommandShortcut>
            </CommandItem>
            <CommandItem value="Token Guard" onSelect={() => { setActiveTab('tokens'); setCommandOpen(false) }}>
              <Zap className="h-4 w-4" />
              <span>Token Budget & Guard</span>
              <CommandShortcut>Docs</CommandShortcut>
            </CommandItem>
          </CommandGroup>
          <CommandGroup heading="Settings">
            <CommandItem value="Settings API Keys" onSelect={() => { setActiveTab('aichat'); setCommandOpen(false) }}>
              <Key className="h-4 w-4" />
              <span>Manage API Keys</span>
            </CommandItem>
            <CommandItem value="Settings Rate Limits" onSelect={() => { setActiveTab('ratelimits'); setCommandOpen(false) }}>
              <Gauge className="h-4 w-4" />
              <span>Configure Rate Limits</span>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </div>
  )
}
