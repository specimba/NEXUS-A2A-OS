'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  Users,
  Shield,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  PieChart as PieChartIcon,
  Wifi,
  AlertCircle,
  Radio,
  Bell,
  XCircle,
  Info,
  Scale,
  BookOpen,
  Rocket,
  ListTodo,
  CheckCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useApiData } from '@/hooks/use-api-data'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

const healthCards = [
  { label: 'CPU Load', value: 34, unit: '%', icon: Cpu, trend: 'down', color: 'emerald', gradient: 'from-emerald-600/10 via-emerald-600/5 to-transparent', sparkData: [42, 38, 45, 35, 30, 37, 34, 28, 32, 36, 33, 34] },
  { label: 'Memory', value: 62, unit: '%', icon: HardDrive, trend: 'up', color: 'yellow', gradient: 'from-yellow-600/10 via-yellow-600/5 to-transparent', sparkData: [55, 58, 52, 60, 57, 63, 65, 62, 59, 61, 64, 62] },
  { label: 'API Latency', value: 142, unit: 'ms', icon: Zap, trend: 'down', color: 'emerald', gradient: 'from-emerald-600/10 via-emerald-600/5 to-transparent', sparkData: [180, 165, 172, 155, 148, 160, 152, 145, 142, 148, 139, 142] },
  { label: 'Uptime', value: 99.7, unit: '%', icon: Activity, trend: 'up', color: 'emerald', gradient: 'from-emerald-600/10 via-emerald-600/5 to-transparent', sparkData: [99.5, 99.6, 99.7, 99.8, 99.7, 99.6, 99.7, 99.8, 99.9, 99.7, 99.6, 99.7] },
]

// System Load Average data (1m/5m/15m)
const loadAverages = {
  '1m': { value: 1.24, sparkData: [1.8, 1.5, 1.3, 1.6, 1.2, 1.1, 1.4, 1.3, 1.2, 1.1, 1.3, 1.24] },
  '5m': { value: 1.58, sparkData: [2.1, 1.9, 1.7, 1.8, 1.6, 1.5, 1.7, 1.6, 1.5, 1.6, 1.5, 1.58] },
  '15m': { value: 2.01, sparkData: [2.4, 2.3, 2.2, 2.1, 2.0, 2.1, 2.0, 2.1, 2.0, 1.9, 2.0, 2.01] },
}

// Constitutional Rules data
const constitutionalRules = [
  { id: 'CR-001', name: 'No Unattended Self-Modification', status: 'active', severity: 'critical' },
  { id: 'CR-002', name: 'Human Approval for Destructive Actions', status: 'active', severity: 'critical' },
  { id: 'CR-003', name: 'Token Budget Hard Limit', status: 'active', severity: 'warning' },
  { id: 'CR-004', name: 'Trust Score Decay Enforcement', status: 'active', severity: 'info' },
  { id: 'CR-005', name: 'Agent Autonomy Boundary', status: 'active', severity: 'critical' },
  { id: 'CR-006', name: 'Rate Limit Circuit Breaker', status: 'active', severity: 'warning' },
]

const agents = [
  { name: 'worker-1', status: 'active', trust: 0.92, tasks: 47, domain: 'Research', model: 'trinity-large' },
  { name: 'worker-2', status: 'warning', trust: 0.78, tasks: 31, domain: 'Coding', model: 'qwen3-coder' },
  { name: 'worker-3', status: 'active', trust: 0.85, tasks: 38, domain: 'Analysis', model: 'gemma-fast' },
  { name: 'coordinator', status: 'active', trust: 0.95, tasks: 12, domain: 'Governance', model: 'glm-4.7' },
]

const recentModelUsage = [
  { model: 'trinity-large', agent: 'worker-1', type: 'completion', tokens: 2450, time: '1m ago' },
  { model: 'qwen3-coder', agent: 'worker-2', type: 'prompt', tokens: 1820, time: '3m ago' },
  { model: 'gemma-fast', agent: 'worker-3', type: 'completion', tokens: 980, time: '5m ago' },
  { model: 'glm-4.7', agent: 'coordinator', type: 'prompt', tokens: 3200, time: '8m ago' },
  { model: 'trinity-large', agent: 'worker-1', type: 'prompt', tokens: 1560, time: '12m ago' },
  { model: 'gemma-fast', agent: 'worker-3', type: 'completion', tokens: 720, time: '15m ago' },
]

const modelPools = [
  { name: 'PREMIUM', models: ['trinity-large-preview', 'minimax-m2.5'], health: 97, color: 'emerald' },
  { name: 'MID', models: ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'], health: 89, color: 'blue' },
  { name: 'FAST', models: ['gemma-fast', 'nemotron-3-super'], health: 94, color: 'orange' },
]

// Static recent activity data (no Date.now() to avoid hydration mismatch)
const recentActivityStatic = [
  { offsetMs: 2 * 60 * 1000, event: 'Governor blocked CRITICAL action', type: 'warning' as const, source: 'Governor' },
  { offsetMs: 5 * 60 * 1000, event: 'StressLab test ISC-001 completed', type: 'success' as const, source: 'StressLab' },
  { offsetMs: 10 * 60 * 1000, event: 'Token budget at 73.4%', type: 'info' as const, source: 'Tokens' },
  { offsetMs: 15 * 60 * 1000, event: 'New research paper vetted: OR-Bench', type: 'success' as const, source: 'Research' },
  { offsetMs: 20 * 60 * 1000, event: 'GMR pool FAST: all models healthy', type: 'success' as const, source: 'GMR' },
  { offsetMs: 25 * 60 * 1000, event: 'Agent worker-3 trust score increased', type: 'info' as const, source: 'Governor' },
  { offsetMs: 30 * 60 * 1000, event: 'Constitution check passed', type: 'success' as const, source: 'Vault' },
]

const typeStyles = {
  success: 'text-emerald-600 dark:text-emerald-400',
  warning: 'text-yellow-600 dark:text-yellow-400',
  info: 'text-blue-600 dark:text-blue-400',
}

const statusStyles = {
  active: 'bg-emerald-500',
  warning: 'bg-yellow-500',
  inactive: 'bg-red-500',
}

const agentBorderStyles = {
  active: 'border-l-2 border-l-emerald-500',
  warning: 'border-l-2 border-l-yellow-500',
  inactive: 'border-l-2 border-l-red-500',
}

// Static alert feed data (offsets only, resolved client-side to avoid hydration mismatch)
const alertFeedDataStatic = [
  { id: 1, severity: 'warning' as const, message: 'Memory usage approaching 80% threshold', source: 'System', offsetMs: 30 * 1000 },
  { id: 2, severity: 'info' as const, message: 'Model failover triggered for gemma-fast', source: 'ModelRelay', offsetMs: 90 * 1000 },
  { id: 3, severity: 'critical' as const, message: 'Provider dashscope rate limit exceeded', source: 'Gateway', offsetMs: 180 * 1000 },
  { id: 4, severity: 'success' as const, message: 'Constitutional check passed for all rules', source: 'Governor', offsetMs: 240 * 1000 },
  { id: 5, severity: 'info' as const, message: 'Token budget reset for new cycle', source: 'Tokens', offsetMs: 360 * 1000 },
  { id: 6, severity: 'warning' as const, message: 'Agent worker-2 trust score below 0.8', source: 'Governor', offsetMs: 480 * 1000 },
  { id: 7, severity: 'success' as const, message: 'StressLab test completed successfully', source: 'StressLab', offsetMs: 600 * 1000 },
  { id: 8, severity: 'info' as const, message: 'New provider sambanova added to pool', source: 'ModelRelay', offsetMs: 900 * 1000 },
]

// Mock data for System Performance AreaChart
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

// Fallback data for Request Volume BarChart (used when API data is unavailable)
const requestVolumeDataFallback = [
  { hour: '12h ago', requests: 245 },
  { hour: '11h ago', requests: 312 },
  { hour: '10h ago', requests: 289 },
  { hour: '9h ago', requests: 378 },
  { hour: '8h ago', requests: 425 },
  { hour: '7h ago', requests: 356 },
  { hour: '6h ago', requests: 298 },
  { hour: '5h ago', requests: 410 },
  { hour: '4h ago', requests: 467 },
  { hour: '3h ago', requests: 389 },
  { hour: '2h ago', requests: 342 },
  { hour: '1h ago', requests: 315 },
]

// Fallback data for Agent Task Distribution PieChart (used when API data is unavailable)
const agentTaskDistributionFallback = [
  { name: 'Research', value: 47, color: '#10b981' },
  { name: 'Coding', value: 31, color: '#3b82f6' },
  { name: 'Analysis', value: 38, color: '#f97316' },
  { name: 'Governance', value: 12, color: '#8b5cf6' },
]

// Sparkline component using recharts LineChart
function MiniSparkline({ data, color, dataKey = 'value' }: { data: number[]; color: string; dataKey?: string }) {
  const chartData = data.map((v, i) => ({ [dataKey]: v, index: i }))

  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// Animated number component with framer-motion
function AnimatedNumber({ value, duration = 0.8 }: { value: number; duration?: number }) {
  return (
    <motion.span
      key={value}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration, ease: 'easeOut' }}
      className="tabular-nums"
    >
      {value.toLocaleString()}
    </motion.span>
  )
}

// Relative time helper
function getRelativeTime(timestamp: number): string {
  const diff = Date.now() - timestamp
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

// Alert severity config
const alertSeverityConfig = {
  critical: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  warning: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' },
  info: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  success: { icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
}

// Network Topology SVG Component
function NetworkTopology() {
  const nodes = [
    { id: 'dashboard', label: 'Dashboard', x: 200, y: 30, color: '#10b981', r: 16 },
    { id: 'gateway', label: 'Gateway', x: 200, y: 90, color: '#34d399', r: 14 },
    { id: 'worker1', label: 'W1', x: 80, y: 155, color: '#10b981', r: 12 },
    { id: 'worker2', label: 'W2', x: 160, y: 165, color: '#eab308', r: 12 },
    { id: 'worker3', label: 'W3', x: 240, y: 165, color: '#10b981', r: 12 },
    { id: 'coord', label: 'CRD', x: 320, y: 155, color: '#10b981', r: 12 },
    { id: 'premium', label: 'PREM', x: 60, y: 230, color: '#10b981', r: 11 },
    { id: 'mid', label: 'MID', x: 155, y: 240, color: '#3b82f6', r: 11 },
    { id: 'fast', label: 'FAST', x: 250, y: 240, color: '#f97316', r: 11 },
    { id: 'providers', label: '14 PV', x: 340, y: 230, color: '#8b5cf6', r: 11 },
  ]

  const links = [
    { from: 'dashboard', to: 'gateway' },
    { from: 'gateway', to: 'worker1' },
    { from: 'gateway', to: 'worker2' },
    { from: 'gateway', to: 'worker3' },
    { from: 'gateway', to: 'coord' },
    { from: 'worker1', to: 'premium' },
    { from: 'worker1', to: 'mid' },
    { from: 'worker2', to: 'mid' },
    { from: 'worker2', to: 'fast' },
    { from: 'worker3', to: 'fast' },
    { from: 'worker3', to: 'premium' },
    { from: 'coord', to: 'providers' },
    { from: 'coord', to: 'mid' },
    { from: 'premium', to: 'providers' },
    { from: 'mid', to: 'providers' },
    { from: 'fast', to: 'providers' },
  ]

  const nodeDescriptions: Record<string, string> = {
    dashboard: 'NEXUS-OS Dashboard UI',
    gateway: 'API Gateway & Router',
    worker1: 'Research Agent (trust: 0.92)',
    worker2: 'Coding Agent (trust: 0.78)',
    worker3: 'Analysis Agent (trust: 0.85)',
    coord: 'Governance Coordinator',
    premium: 'Premium Model Pool (97%)',
    mid: 'Mid Model Pool (89%)',
    fast: 'Fast Model Pool (94%)',
    providers: '14 Active Providers',
  }

  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]))

  return (
    <svg viewBox="0 0 400 270" className="w-full h-full" style={{ maxHeight: 260 }}>
      {/* Connection lines */}
      {links.map((link, i) => {
        const from = nodeMap[link.from]
        const to = nodeMap[link.to]
        if (!from || !to) return null
        return (
          <line
            key={i}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            stroke="#374151"
            strokeWidth={1}
            strokeOpacity={0.5}
          />
        )
      })}
      {/* Nodes with hover tooltips via <title> */}
      {nodes.map((node) => (
        <g key={node.id}>
          <title>{node.label} — {nodeDescriptions[node.id] || ''}</title>
          <motion.circle
            cx={node.x}
            cy={node.y}
            r={node.r}
            fill={node.color}
            fillOpacity={0.2}
            stroke={node.color}
            strokeWidth={1.5}
            animate={{ fillOpacity: [0.15, 0.3, 0.15] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            style={{ cursor: 'pointer' }}
          />
          <text
            x={node.x}
            y={node.y + 4}
            textAnchor="middle"
            fill={node.color}
            fontSize={8}
            fontWeight={600}
            fontFamily="monospace"
            style={{ pointerEvents: 'none' }}
          >
            {node.label}
          </text>
        </g>
      ))}
      {/* Layer labels */}
      <text x={15} y={35} fill="#6b7280" fontSize={7} fontFamily="monospace">UI</text>
      <text x={15} y={95} fill="#6b7280" fontSize={7} fontFamily="monospace">ROUTING</text>
      <text x={15} y={160} fill="#6b7280" fontSize={7} fontFamily="monospace">AGENTS</text>
      <text x={15} y={235} fill="#6b7280" fontSize={7} fontFamily="monospace">MODELS</text>
    </svg>
  )
}

export function OverviewTab() {
  // Hydration-safe mount detection
  const [mounted, setMounted] = useState(false)

  // ── Dynamic data from APIs ──────────────────────────────────────
  // NOTE: /api/system is disabled to prevent OOM (20+ DB queries)
  // Fetch tasks data for Agent Task Distribution donut chart
  const { data: tasksData } = useApiData<{ tasks: Array<{ category: string; status: string; priority: string }> }>('/api/tasks', 120000)

  // Fetch rate-limit logs for Request Volume chart
  const { data: rateLimitData } = useApiData<{ hourlyData: Array<{ hour: string; total: number }> }>('/api/rate-limit/logs?hours=24&limit=100', 300000)

  // System data disabled - too heavy for sandbox environment
  // const { data: systemData } = useApiData<{ overview?: { recentActivity?: Array<{ event: string; type: string; time: string; source?: string }> } }>('/api/system', 300000)
  const systemData = null as { overview?: { recentActivity?: Array<{ event: string; type: string; time: string; source?: string }> } } | null

  // Derive Agent Task Distribution from tasks API
  const agentTaskDistribution = useMemo(() => {
    const tasks = tasksData?.tasks
    if (!tasks || tasks.length === 0) return agentTaskDistributionFallback

    // Group tasks by category and count
    const categoryCount: Record<string, number> = {}
    for (const t of tasks) {
      const cat = t.category || 'general'
      categoryCount[cat] = (categoryCount[cat] || 0) + 1
    }

    // Map categories to colors
    const categoryColors: Record<string, string> = {
      evaluation: '#10b981',
      safety_review: '#ef4444',
      implementation: '#f97316',
      research: '#8b5cf6',
      governance: '#6366f1',
      security: '#ec4899',
      general: '#6b7280',
      context_processing: '#94a3b8',
      memory_research: '#14b8a6',
      harness_testing: '#84cc16',
      compression: '#0ea5e9',
      benchmark: '#a855f7',
      survey_analysis: '#d946ef',
      infra_build: '#78716c',
      ics_testing: '#06b6d4',
      fleet: '#f59e0b',
      dashboard: '#ec4899',
    }

    const categoryLabels: Record<string, string> = {
      evaluation: 'Evaluation',
      safety_review: 'Safety',
      implementation: 'Implementation',
      research: 'Research',
      governance: 'Governance',
      security: 'Security',
      general: 'General',
      context_processing: 'Context',
      memory_research: 'Memory',
      harness_testing: 'Harness',
      compression: 'Compression',
      benchmark: 'Benchmark',
      survey_analysis: 'Survey',
      infra_build: 'Infra',
      ics_testing: 'ICS Testing',
      fleet: 'Fleet',
      dashboard: 'Dashboard',
    }

    return Object.entries(categoryCount)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 6)
      .map(([cat, count]) => ({
        name: categoryLabels[cat] || cat,
        value: count,
        color: categoryColors[cat] || '#6b7280',
      }))
  }, [tasksData])

  // Derive Request Volume from rate-limit API
  const requestVolumeData = useMemo(() => {
    const hourly = rateLimitData?.hourlyData
    if (!hourly || hourly.length === 0) return requestVolumeDataFallback

    // Take the last 12 hours and format
    return hourly
      .slice(-12)
      .map((h) => ({
        hour: h.hour.slice(11, 16), // Extract HH:MM
        requests: h.total,
      }))
  }, [rateLimitData])

  // Derive recent task completions from system API
  const recentTaskActivity = useMemo(() => {
    const activity = systemData?.overview?.recentActivity
    if (!activity || activity.length === 0) return []
    // Filter to task-related activity
    return activity.slice(0, 6)
  }, [systemData])

  // Track last data refresh time for "Last updated" display
  const [lastDataRefresh, setLastDataRefresh] = useState<Date | null>(null)
  useEffect(() => {
    if (tasksData || rateLimitData || systemData) {
      setLastDataRefresh(new Date())
    }
  }, [tasksData, rateLimitData, systemData])

  // Live system metrics state
  const [activeConnections, setActiveConnections] = useState(247)
  const [requestsPerSec, setRequestsPerSec] = useState(34)
  const [tokensPerMin, setTokensPerMin] = useState(1420)
  const [errorRate, setErrorRate] = useState(0.3)
  const [rpsHistory, setRpsHistory] = useState<number[]>([32, 35, 28, 31, 34, 30, 33, 36, 29, 34])

  // Initialize alerts with 0 timestamps (hydration-safe), will be updated on mount
  const [alerts, setAlerts] = useState(() =>
    alertFeedDataStatic.map(a => ({ ...a, time: 0 }))
  )

  // Resolve timestamps client-side after mount
  useEffect(() => {
    setMounted(true)
    const now = Date.now()
    setAlerts(alertFeedDataStatic.map(a => ({ ...a, time: now - a.offsetMs })))
  }, [])

  const alertListRef = useRef<HTMLDivElement>(null)

  // Simulated live metric updates every 2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveConnections(prev => {
        const delta = Math.floor(Math.random() * 20) - 10
        return Math.max(150, Math.min(400, prev + delta))
      })
      setRequestsPerSec(prev => {
        const delta = Math.floor(Math.random() * 8) - 4
        return Math.max(10, Math.min(80, prev + delta))
      })
      setTokensPerMin(prev => {
        const delta = Math.floor(Math.random() * 200) - 100
        return Math.max(500, Math.min(3000, prev + delta))
      })
      setErrorRate(prev => {
        const delta = (Math.random() * 0.4) - 0.2
        return Math.max(0, Math.min(5, parseFloat((prev + delta).toFixed(1))))
      })
      setRpsHistory(prev => {
        const newVal = Math.max(10, Math.min(80, prev[prev.length - 1] + Math.floor(Math.random() * 8) - 4))
        return [...prev.slice(1), newVal]
      })
      // Rotate alerts - shift and add new one at top
      setAlerts(prev => {
        const nextId = Math.max(...prev.map(a => a.id)) + 1
        const severities: Array<'critical' | 'warning' | 'info' | 'success'> = ['critical', 'warning', 'info', 'success']
        const messages = [
          'Memory usage spike detected on worker-2',
          'Provider rate limit approaching for groq',
          'Token burn rate increased by 12%',
          'Circuit breaker triggered for scaleway',
          'Model pool rebalance completed',
          'New constitutional rule validated',
          'Agent coordinator heartbeat received',
          'Cache hit ratio improved to 94%',
        ]
        const sources = ['System', 'Gateway', 'Tokens', 'Governor', 'ModelRelay', 'Vault', 'StressLab']
        const newAlert = {
          id: nextId,
          severity: severities[Math.floor(Math.random() * severities.length)],
          message: messages[Math.floor(Math.random() * messages.length)],
          source: sources[Math.floor(Math.random() * sources.length)],
          time: Date.now(),
        }
        return [newAlert, ...prev.slice(0, 7)]
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  // Auto-scroll alert feed to top when new alerts arrive
  useEffect(() => {
    if (alertListRef.current) {
      alertListRef.current.scrollTop = 0
    }
  }, [alerts])

  const errorRateColor = errorRate > 2 ? 'text-red-500' : errorRate > 1 ? 'text-yellow-500' : 'text-emerald-500'
  const errorRateBg = errorRate > 2 ? 'from-red-600/10 to-transparent' : errorRate > 1 ? 'from-yellow-600/10 to-transparent' : 'from-emerald-600/10 to-transparent'

  return (
    <div className="space-y-6">
      {/* System Status Header */}
      <div className="flex items-center gap-3">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
        </span>
        <span className="text-sm font-medium animate-pulse text-emerald-600 dark:text-emerald-400">System Operational</span>
        <span className="ml-auto text-[10px] text-muted-foreground flex items-center gap-1" suppressHydrationWarning>
          <Clock className="h-3 w-3" />
          {mounted && lastDataRefresh ? `Last updated: ${lastDataRefresh.toLocaleTimeString()}` : '...'}
        </span>
      </div>

      {/* 8-Pillar Health Grid — larger cards with status badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {[
          { name: 'Bridge', health: 98, status: 'healthy', icon: '🔗', uptime: '4h 23m', version: 'v3.1.2' },
          { name: 'Engine', health: 95, status: 'healthy', icon: '⚙️', uptime: '4h 23m', version: 'v2.8.1' },
          { name: 'Governor', health: 100, status: 'healthy', icon: '🛡️', uptime: '4h 23m', version: 'v4.0.0' },
          { name: 'Vault', health: 97, status: 'healthy', icon: '🔐', uptime: '4h 23m', version: 'v2.5.3' },
          { name: 'GMR', health: 91, status: 'healthy', icon: '🚦', uptime: '4h 23m', version: 'v1.9.7' },
          { name: 'Swarm', health: 82, status: 'degraded', icon: '🐝', uptime: '3h 15m', version: 'v1.3.2' },
          { name: 'Monitor', health: 94, status: 'healthy', icon: '📊', uptime: '4h 23m', version: 'v2.1.0' },
          { name: 'Config', health: 100, status: 'healthy', icon: '🔧', uptime: '4h 23m', version: 'v1.0.5' },
        ].map((pillar) => (
          <Tooltip key={pillar.name}>
            <TooltipTrigger asChild>
              <Card className={cn(
                'bg-card/50 hover:scale-[1.03] transition-all duration-200 cursor-default',
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
                    )}>
                      {pillar.status === 'healthy' ? 'OK' : 'WARN'}
                    </Badge>
                  </div>
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{pillar.name}</div>
                  <div className={cn(
                    'text-lg font-bold tabular-nums',
                    pillar.health >= 90 ? 'text-emerald-600 dark:text-emerald-400' :
                    pillar.health >= 70 ? 'text-yellow-600 dark:text-yellow-400' :
                    'text-red-600 dark:text-red-400'
                  )}>
                    {pillar.health}%
                  </div>
                  <div className="mt-1 h-1 rounded-full bg-muted overflow-hidden">
                    <motion.div
                      className={cn(
                        'h-full rounded-full',
                        pillar.health >= 90 ? 'bg-emerald-500' :
                        pillar.health >= 70 ? 'bg-yellow-500' :
                        'bg-red-500'
                      )}
                      initial={{ width: 0 }}
                      animate={{ width: `${pillar.health}%` }}
                      transition={{ duration: 1, ease: 'easeOut', delay: 0.1 }}
                    />
                  </div>
                  <div className="text-[8px] text-muted-foreground/60 mt-1">{pillar.uptime} • {pillar.version}</div>
                </CardContent>
              </Card>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <div className="text-xs">
                <p className="font-semibold">{pillar.name} Pillar</p>
                <p className="text-muted-foreground">Health: {pillar.health}% • Status: {pillar.status}</p>
                <p className="text-muted-foreground">Uptime: {pillar.uptime} • Version: {pillar.version}</p>
              </div>
            </TooltipContent>
          </Tooltip>
        ))}
      </div>

      {/* System Load Average Mini Card */}
      <Card className="bg-card/50 border-border/50 bg-gradient-to-r from-emerald-600/5 via-transparent to-transparent">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Scale className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            System Load Average
            <Badge variant="outline" className="text-[9px] ml-auto">1m / 5m / 15m</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-3 gap-4">
            {(['1m', '5m', '15m'] as const).map((period) => (
              <div key={period} className="bg-gradient-to-br from-emerald-600/5 to-transparent p-3 rounded-lg border border-border/30">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{period}</span>
                  <Badge variant="outline" className={cn(
                    'text-[8px] h-3.5',
                    loadAverages[period].value > 2 ? 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400' :
                    loadAverages[period].value > 1.5 ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' :
                    'border-emerald-600/30 text-emerald-600 dark:text-emerald-400'
                  )}>
                    {loadAverages[period].value > 2 ? 'HIGH' : loadAverages[period].value > 1.5 ? 'MED' : 'LOW'}
                  </Badge>
                </div>
                <div className={cn(
                  'text-xl font-bold tabular-nums',
                  loadAverages[period].value > 2 ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'
                )}>
                  {loadAverages[period].value.toFixed(2)}
                </div>
                <div className="mt-1 h-6">
                  <MiniSparkline data={loadAverages[period].sparkData} color={loadAverages[period].value > 2 ? '#eab308' : '#10b981'} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Live System Metrics */}
      <Card className="bg-card/50 border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 to-transparent">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Radio className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Live System Metrics
            <Badge variant="outline" className="text-[9px] bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-emerald-600/30">
              <span className="relative flex h-1.5 w-1.5 mr-1">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              LIVE
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Active Connections */}
            <div className="bg-gradient-to-br from-emerald-600/5 to-transparent p-3 rounded-lg border border-border/30">
              <div className="flex items-center gap-2 mb-1">
                <Wifi className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Active Connections</span>
              </div>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                <AnimatedNumber value={activeConnections} duration={0.6} />
              </div>
            </div>

            {/* Requests/sec with sparkline */}
            <div className="bg-gradient-to-br from-emerald-600/5 to-transparent p-3 rounded-lg border border-border/30">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Requests/sec</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                  <AnimatedNumber value={requestsPerSec} duration={0.6} />
                </span>
                <span className="text-[10px] text-muted-foreground mb-1">req/s</span>
              </div>
              <div className="mt-1 h-8">
                <MiniSparkline data={rpsHistory} color="#10b981" />
              </div>
            </div>

            {/* Tokens/min */}
            <div className="bg-gradient-to-br from-emerald-600/5 to-transparent p-3 rounded-lg border border-border/30">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Tokens/min</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                  <AnimatedNumber value={tokensPerMin} duration={0.6} />
                </span>
                <span className="text-[10px] text-muted-foreground mb-1">tok/min</span>
              </div>
            </div>

            {/* Error Rate with color coding */}
            <div className={cn('bg-gradient-to-br p-3 rounded-lg border border-border/30', errorRateBg)}>
              <div className="flex items-center gap-2 mb-1">
                <AlertCircle className={cn('h-3.5 w-3.5', errorRateColor)} />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Error Rate</span>
              </div>
              <div className="flex items-end gap-2">
                <span className={cn('text-2xl font-bold', errorRateColor)}>
                  <AnimatedNumber value={errorRate} duration={0.6} />
                </span>
                <span className="text-[10px] text-muted-foreground mb-1">%</span>
              </div>
              <motion.div
                className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden"
              >
                <motion.div
                  className={cn('h-full rounded-full', errorRate > 2 ? 'bg-red-500' : errorRate > 1 ? 'bg-yellow-500' : 'bg-emerald-500')}
                  initial={false}
                  animate={{ width: `${Math.min(errorRate * 20, 100)}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                />
              </motion.div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Network Topology & Alert Feed - side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Network Topology Mini-Map */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Wifi className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Network Topology
              <Badge variant="outline" className="text-[9px] ml-auto">4 Layers</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <NetworkTopology />
            {/* Legend */}
            <div className="flex flex-wrap gap-3 mt-2">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-[9px] text-muted-foreground">Healthy</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-yellow-500" />
                <span className="text-[9px] text-muted-foreground">Degraded</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-blue-500" />
                <span className="text-[9px] text-muted-foreground">Mid Pool</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-orange-500" />
                <span className="text-[9px] text-muted-foreground">Fast Pool</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-purple-500" />
                <span className="text-[9px] text-muted-foreground">Providers</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Alert Feed */}
        <Card className="bg-card/50 border-border/50">
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
            <div ref={alertListRef} className="space-y-1.5 max-h-[260px] overflow-y-auto scrollbar-thin">
              <AnimatePresence mode="popLayout">
                {alerts.slice(0, 5).map((alert) => {
                  const config = alertSeverityConfig[alert.severity]
                  const Icon = config.icon
                  return (
                    <motion.div
                      key={alert.id}
                      initial={{ opacity: 0, x: -20, height: 0 }}
                      animate={{ opacity: 1, x: 0, height: 'auto' }}
                      exit={{ opacity: 0, x: 20, height: 0 }}
                      transition={{ duration: 0.3, ease: 'easeOut' }}
                      className={cn('flex items-center gap-2.5 p-2 rounded-lg border', config.bg, config.border)}
                    >
                      <Icon className={cn('h-3.5 w-3.5 shrink-0', config.color)} />
                      <span className="text-xs flex-1 truncate">{alert.message}</span>
                      <Badge variant="outline" className="text-[8px] shrink-0">{alert.source}</Badge>
                      <span className="text-[9px] text-muted-foreground whitespace-nowrap shrink-0" suppressHydrationWarning>{mounted ? getRelativeTime(alert.time) : '...'}</span>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Health Cards with Animated Progress Bars & Sparklines */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {healthCards.map((card) => (
          <Card key={card.label} className={cn('bg-card/50 border-border/50 bg-gradient-to-br hover:scale-[1.02] transition-transform duration-200 cursor-default group', card.gradient)}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <card.icon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">{card.label}</span>
                </div>
                <Badge variant="outline" className={`text-[10px] ${card.trend === 'down' ? 'text-emerald-600 dark:text-emerald-400' : 'text-yellow-600 dark:text-yellow-400'}`}>
                  {card.trend === 'down' ? <ArrowDownRight className="h-3 w-3 mr-0.5" /> : <ArrowUpRight className="h-3 w-3 mr-0.5" />}
                  {card.trend === 'down' ? 'Good' : 'Watch'}
                </Badge>
              </div>
              <div className="mt-2">
                <span className="text-2xl font-bold">{card.value}</span>
                <span className="text-sm text-muted-foreground ml-1">{card.unit}</span>
              </div>
              {card.label !== 'Uptime' && (
                <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                  <motion.div
                    className={cn(
                      'h-full rounded-full',
                      card.color === 'emerald' ? 'bg-emerald-500' : 'bg-yellow-500'
                    )}
                    initial={{ width: 0 }}
                    animate={{ width: `${card.label === 'API Latency' ? Math.min(card.value / 3, 100) : card.value}%` }}
                    transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
                  />
                </div>
              )}
              {/* Sparkline */}
              <div className="mt-2 opacity-60 group-hover:opacity-100 transition-opacity duration-200">
                <MiniSparkline
                  data={card.sparkData}
                  color={card.color === 'emerald' ? '#10b981' : card.color === 'yellow' ? '#eab308' : '#3b82f6'}
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* System Performance Area Chart */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            System Performance
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={systemPerformanceData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="memoryGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#6b7280" tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10 }} stroke="#6b7280" tickLine={false} axisLine={false} />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
              <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#10b981" strokeWidth={2} fill="url(#cpuGradient)" />
              <Area type="monotone" dataKey="memory" name="Memory %" stroke="#3b82f6" strokeWidth={2} fill="url(#memoryGradient)" />
              <Area type="monotone" dataKey="latency" name="Latency (ms)" stroke="#f97316" strokeWidth={2} fill="url(#latencyGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Request Volume & Agent Task Distribution - side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Request Volume Bar Chart */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Request Volume
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={requestVolumeData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.9} />
                    <stop offset="95%" stopColor="#34d399" stopOpacity={0.6} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" tick={{ fontSize: 9 }} stroke="#6b7280" tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} stroke="#6b7280" tickLine={false} axisLine={false} />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="requests" name="API Requests" fill="url(#barGradient)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Agent Task Distribution Pie Chart */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <PieChartIcon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Agent Task Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={agentTaskDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                  stroke="none"
                >
                  {agentTaskDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Agent Status */}
        <Card className="bg-card/50 border-border/50 lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Users className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Agent Status
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {agents.map((agent) => (
                <div key={agent.name} className={cn('flex items-center gap-3 p-2 rounded-lg bg-muted/30', agentBorderStyles[agent.status as keyof typeof agentBorderStyles])}>
                  <span className={`h-2 w-2 rounded-full ${statusStyles[agent.status as keyof typeof statusStyles]}`} />
                  <span className="text-sm font-medium">{agent.name}</span>
                  <span className="text-[10px] font-mono text-muted-foreground">{agent.model}</span>
                  <span className="flex-1" />
                  <Badge variant="outline" className="text-[10px]">{agent.domain}</Badge>
                  <div className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-muted-foreground" />
                    <span className="text-xs font-mono">{agent.trust.toFixed(2)}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{agent.tasks} tasks</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Model Pool Status */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Model Pools
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {modelPools.map((pool) => (
                <div key={pool.name} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{pool.name}</span>
                    <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400">{pool.health}%</span>
                  </div>
                  <Progress value={pool.health} className="h-1.5" />
                  <div className="flex flex-wrap gap-1">
                    {pool.models.map((model) => (
                      <Badge key={model} variant="secondary" className="text-[9px] h-4">{model}</Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Model Usage */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Usage
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {recentModelUsage.map((entry, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                <Zap className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="text-sm font-mono">{entry.model}</span>
                <Badge variant="outline" className="text-[9px] h-4">{entry.agent}</Badge>
                <Badge variant="secondary" className="text-[9px] h-4">{entry.type}</Badge>
                <span className="flex-1" />
                <span className="text-xs font-mono text-muted-foreground">{entry.tokens.toLocaleString()} tok</span>
                <span className="text-[10px] text-muted-foreground">{entry.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity with relative timestamps */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {recentActivityStatic.map((item, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                {item.type === 'success' ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                ) : item.type === 'warning' ? (
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 shrink-0" />
                ) : (
                  <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" />
                )}
                <span className="text-sm flex-1">{item.event}</span>
                <Badge variant="outline" className="text-[10px] shrink-0">{item.source}</Badge>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap" suppressHydrationWarning>{mounted ? getRelativeTime(Date.now() - item.offsetMs) : '...'}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Constitutional Rules */}
      <Card className="bg-card/50 border-border/50 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Constitutional Rules
            <Badge variant="outline" className="text-[9px] ml-auto bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-emerald-600/30">
              {constitutionalRules.length} Active
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {constitutionalRules.map((rule) => (
              <div key={rule.id} className="flex items-center gap-2 p-2 rounded-lg bg-muted/30 border border-border/20 hover:border-emerald-600/20 transition-colors">
                <Badge variant="outline" className="text-[8px] h-4 font-mono shrink-0">{rule.id}</Badge>
                <span className="text-xs flex-1 truncate">{rule.name}</span>
                <Badge className={cn('text-[8px] h-4 border-0 shrink-0', {
                  'bg-red-600/20 text-red-600 dark:text-red-400': rule.severity === 'critical',
                  'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400': rule.severity === 'warning',
                  'bg-blue-600/20 text-blue-600 dark:text-blue-400': rule.severity === 'info',
                })}>
                  {rule.severity.toUpperCase()}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Task Activity — from /api/system */}
      {recentTaskActivity.length > 0 && (
        <Card className="bg-card/50 border-border/50 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ListTodo className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Recent Task Activity
              <Badge variant="outline" className="text-[9px] ml-auto bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-emerald-600/30">
                {recentTaskActivity.length} Events
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
              {recentTaskActivity.map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                  {item.type === 'success' ? (
                    <CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  ) : item.type === 'warning' ? (
                    <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 shrink-0" />
                  ) : (
                    <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" />
                  )}
                  <span className="text-sm flex-1">{item.event}</span>
                  {item.source && <Badge variant="outline" className="text-[10px] shrink-0">{item.source}</Badge>}
                  <span className="text-[10px] text-muted-foreground whitespace-nowrap shrink-0" suppressHydrationWarning>{mounted ? item.time : '...'}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Deployments */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Rocket className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Deployments
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {[
              { id: 'DEP-012', service: 'Governor v4.0.0', status: 'success', env: 'prod', time: '25m ago' },
              { id: 'DEP-011', service: 'GMR Router v1.9.7', status: 'success', env: 'prod', time: '1h ago' },
              { id: 'DEP-010', service: 'StressLab v2.1.0', status: 'success', env: 'staging', time: '2h ago' },
              { id: 'DEP-009', service: 'Vault v2.5.3', status: 'rolled-back', env: 'prod', time: '3h ago' },
              { id: 'DEP-008', service: 'Bridge v3.1.2', status: 'success', env: 'prod', time: '5h ago' },
            ].map((dep) => (
              <div key={dep.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                {dep.status === 'success' ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 shrink-0" />
                )}
                <span className="text-xs font-mono text-muted-foreground shrink-0">{dep.id}</span>
                <span className="text-sm flex-1">{dep.service}</span>
                <Badge variant="outline" className={cn('text-[9px] h-4 shrink-0', dep.env === 'prod' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400')}>
                  {dep.env}
                </Badge>
                <Badge className={cn('text-[8px] h-4 border-0 shrink-0', dep.status === 'success' ? 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400' : 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400')}>
                  {dep.status.toUpperCase()}
                </Badge>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap shrink-0">{dep.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
