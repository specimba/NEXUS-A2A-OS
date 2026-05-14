'use client'

import { useState, useEffect, useMemo } from 'react'
import { useTheme } from 'next-themes'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Cpu, HardDrive, Zap, Users, Shield, Activity,
  TrendingUp, AlertTriangle, CheckCircle2, Clock, ArrowUpRight,
  ArrowDownRight, Wifi, AlertCircle, Radio, Bell,
  XCircle, Info, Moon, Sun, Menu, ChevronRight,
  ChevronLeft, FlaskConical, Router, Server,
  BookOpen, Bug, Coins, Network,
  RefreshCw, Heart, Globe, Layers, ShieldCheck, Sparkles
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

// ─── Types ───────────────────────────────────────────────────────────────────
type TabId = 'overview' | 'providers' | 'agents' | 'gmr' | 'governor' | 'research' | 'stresslab' | 'tokens'

interface NavItem {
  id: TabId
  label: string
  icon: React.ReactNode
  badge?: string
  shortcut: string
  desc: string
}

// ─── Navigation Config ───────────────────────────────────────────────────────
const navGroups: { label: string; items: NavItem[] }[] = [
  {
    label: 'Core',
    items: [
      { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" />, shortcut: '1', desc: 'System overview & health' },
      { id: 'providers', label: 'Providers', icon: <Server className="h-4 w-4" />, shortcut: '2', desc: 'AI provider management' },
      { id: 'agents', label: 'Agents', icon: <Bug className="h-4 w-4" />, shortcut: '3', desc: 'Agent swarm monitoring' },
    ],
  },
  {
    label: 'Routing & Governance',
    items: [
      { id: 'gmr', label: 'GMR Router', icon: <Router className="h-4 w-4" />, shortcut: '4', desc: 'Global Model Router' },
      { id: 'governor', label: 'Governor', icon: <Shield className="h-4 w-4" />, shortcut: '5', desc: 'Constitutional governance' },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { id: 'research', label: 'Research', icon: <BookOpen className="h-4 w-4" />, badge: '20', shortcut: '6', desc: 'Research pipeline' },
      { id: 'stresslab', label: 'StressLab', icon: <FlaskConical className="h-4 w-4" />, badge: 'ISC', shortcut: '7', desc: 'Model stress testing' },
    ],
  },
  {
    label: 'Metrics',
    items: [
      { id: 'tokens', label: 'Token Budget', icon: <Coins className="h-4 w-4" />, shortcut: '8', desc: 'Token usage tracking' },
    ],
  },
]

const tabTitles: Record<TabId, string> = {
  overview: 'System Overview',
  providers: 'Provider Management',
  agents: 'Agent Swarm',
  gmr: 'GMR Router Panel',
  governor: 'Governor Dashboard',
  research: 'Research Pipeline',
  stresslab: 'StressLab Arena',
  tokens: 'Token Budget',
}

// ─── Mock Data ────────────────────────────────────────────────────────────────
const healthCards = [
  { label: 'CPU Load', value: 34, unit: '%', icon: Cpu, trend: 'down', color: '#10b981', sparkData: [42, 38, 45, 35, 30, 37, 34, 28, 32, 36, 33, 34] },
  { label: 'Memory', value: 62, unit: '%', icon: HardDrive, trend: 'up', color: '#eab308', sparkData: [55, 58, 52, 60, 57, 63, 65, 62, 59, 61, 64, 62] },
  { label: 'API Latency', value: 142, unit: 'ms', icon: Zap, trend: 'down', color: '#10b981', sparkData: [180, 165, 172, 155, 148, 160, 152, 145, 142, 148, 139, 142] },
  { label: 'Uptime', value: 99.7, unit: '%', icon: Activity, trend: 'up', color: '#10b981', sparkData: [99.5, 99.6, 99.7, 99.8, 99.7, 99.6, 99.7, 99.8, 99.9, 99.7, 99.6, 99.7] },
]

const agents = [
  { name: 'worker-1', status: 'active', trust: 0.92, tasks: 47, domain: 'Research', model: 'trinity-large', uptime: '4h 23m' },
  { name: 'worker-2', status: 'warning', trust: 0.78, tasks: 31, domain: 'Coding', model: 'qwen3-coder', uptime: '3h 15m' },
  { name: 'worker-3', status: 'active', trust: 0.85, tasks: 38, domain: 'Analysis', model: 'gemma-fast', uptime: '4h 10m' },
  { name: 'coordinator', status: 'active', trust: 0.95, tasks: 12, domain: 'Governance', model: 'glm-4.7', uptime: '4h 23m' },
]

const providers = [
  { name: 'z-ai SDK', model: 'GLM-4.7', status: 'online', latency: 45, quota: 85, color: '#10b981' },
  { name: 'OpenRouter', model: 'trinity-large', status: 'online', latency: 120, quota: 62, color: '#3b82f6' },
  { name: 'Cerebras', model: 'llama-4-scout', status: 'degraded', latency: 280, quota: 30, color: '#f97316' },
  { name: 'Groq', model: 'gemma-fast', status: 'online', latency: 35, quota: 78, color: '#10b981' },
  { name: 'Mistral', model: 'codestral', status: 'online', latency: 95, quota: 55, color: '#3b82f6' },
  { name: 'Fireworks', model: 'qwen3-coder', status: 'degraded', latency: 210, quota: 25, color: '#f97316' },
  { name: 'Scaleway', model: 'mistral-nemo', status: 'unknown', latency: 0, quota: 0, color: '#6b7280' },
  { name: 'DashScope', model: 'qwen-max', status: 'online', latency: 110, quota: 70, color: '#10b981' },
  { name: 'NVIDIA NIM', model: 'nemotron-3', status: 'online', latency: 65, quota: 88, color: '#10b981' },
  { name: 'SambaNova', model: 'samba-1', status: 'online', latency: 78, quota: 72, color: '#10b981' },
  { name: 'BitDeer', model: 'deepseek-v3', status: 'unknown', latency: 0, quota: 0, color: '#6b7280' },
  { name: 'DeepSeek', model: 'deepseek-r1', status: 'online', latency: 88, quota: 60, color: '#3b82f6' },
  { name: 'Google', model: 'gemma-3', status: 'online', latency: 55, quota: 82, color: '#10b981' },
  { name: 'Meta', model: 'llama-4', status: 'online', latency: 72, quota: 75, color: '#10b981' },
]

const modelPools = [
  { name: 'PREMIUM', models: ['trinity-large-preview', 'minimax-m2.5'], health: 97, color: '#10b981' },
  { name: 'MID', models: ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'], health: 89, color: '#3b82f6' },
  { name: 'FAST', models: ['gemma-fast', 'nemotron-3-super'], health: 94, color: '#f97316' },
]

const BASE_TIME = 1747200000000 // Fixed base time to avoid hydration mismatch
const alertFeedData = [
  { id: 1, severity: 'warning' as const, message: 'Memory usage approaching 80% threshold', source: 'System', time: BASE_TIME - 30000 },
  { id: 2, severity: 'info' as const, message: 'Model failover triggered for gemma-fast', source: 'ModelRelay', time: BASE_TIME - 90000 },
  { id: 3, severity: 'critical' as const, message: 'Provider scaleway rate limit exceeded', source: 'Gateway', time: BASE_TIME - 180000 },
  { id: 4, severity: 'success' as const, message: 'Constitutional check passed for all rules', source: 'Governor', time: BASE_TIME - 240000 },
  { id: 5, severity: 'info' as const, message: 'Token budget reset for new cycle', source: 'Tokens', time: BASE_TIME - 360000 },
]

const recentActivity = [
  { time: BASE_TIME - 2 * 60000, event: 'Governor blocked CRITICAL action', type: 'warning' as const, source: 'Governor' },
  { time: BASE_TIME - 5 * 60000, event: 'StressLab test ISC-001 completed', type: 'success' as const, source: 'StressLab' },
  { time: BASE_TIME - 10 * 60000, event: 'Token budget at 73.4%', type: 'info' as const, source: 'Tokens' },
  { time: BASE_TIME - 15 * 60000, event: 'New research paper vetted: OR-Bench', type: 'success' as const, source: 'Research' },
  { time: BASE_TIME - 20 * 60000, event: 'GMR pool FAST: all models healthy', type: 'success' as const, source: 'GMR' },
  { time: BASE_TIME - 30 * 60000, event: 'Constitution check passed', type: 'success' as const, source: 'Vault' },
]

const gmrRouteHistory = [
  { time: '14:23:01', model: 'trinity-large', pool: 'PREMIUM', agent: 'worker-1', latency: 124, tokens: 2450, status: 'success' },
  { time: '14:22:58', model: 'gemma-fast', pool: 'FAST', agent: 'worker-3', latency: 38, tokens: 980, status: 'success' },
  { time: '14:22:55', model: 'qwen3-coder', pool: 'MID', agent: 'worker-2', latency: 156, tokens: 1820, status: 'success' },
  { time: '14:22:50', model: 'glm-4.7', pool: 'PREMIUM', agent: 'coordinator', latency: 45, tokens: 3200, status: 'success' },
  { time: '14:22:45', model: 'trinity-large', pool: 'PREMIUM', agent: 'worker-1', latency: 132, tokens: 1560, status: 'success' },
  { time: '14:22:40', model: 'gemma-fast', pool: 'FAST', agent: 'worker-3', latency: 35, tokens: 720, status: 'failover' },
]

const governorRules = [
  { id: 'R-001', name: 'Agent Rate Limit', rule: '5 agents/hr', status: 'active', violations: 0 },
  { id: 'R-002', name: 'API Call Limit', rule: '20 API/session', status: 'active', violations: 0 },
  { id: 'R-003', name: 'Concurrent Agents', rule: '2 concurrent', status: 'active', violations: 1 },
  { id: 'R-004', name: 'Write Limit', rule: '30 writes', status: 'active', violations: 0 },
  { id: 'R-005', name: 'CRITICAL Block', rule: 'Block delete_all, override_constitution', status: 'active', violations: 3 },
]

const researchPapers = [
  { title: 'OR-Bench: Over-Refusal Benchmark', relevance: 95, status: 'vetted', queue: 'P1', assignedTo: 'worker-1' },
  { title: 'AgentTrust: Multi-Agent Delegation', relevance: 88, status: 'vetted', queue: 'P1', assignedTo: 'worker-2' },
  { title: 'Constitutional AI Self-Improvement', relevance: 82, status: 'pending', queue: 'P2', assignedTo: '—' },
  { title: 'Model Collapse in Recursive Training', relevance: 79, status: 'pending', queue: 'P2', assignedTo: '—' },
  { title: 'Stress Testing LLM Guardrails', relevance: 91, status: 'vetted', queue: 'P1', assignedTo: 'worker-3' },
]

const stressTests = [
  { id: 'ISC-001', model: 'qwen3-coder', type: 'Agentic Mode', result: 'COLLAPSE', rate: 95.3, status: 'completed' },
  { id: 'ISC-002', model: 'trinity-large', type: 'Prompt Injection', result: 'RESISTANT', rate: 2.1, status: 'completed' },
  { id: 'ISC-003', model: 'gemma-fast', type: 'Agentic Mode', result: 'DEGRADED', rate: 34.7, status: 'completed' },
  { id: 'ISC-004', model: 'glm-4.7', type: 'Constitutional Bypass', result: 'RESISTANT', rate: 0.8, status: 'running' },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getRelativeTime(timestamp: number): string {
  const diff = Date.now() - timestamp
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}

const alertSeverityConfig = {
  critical: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  warning: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' },
  info: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  success: { icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
}

// ─── SVG Mini Sparkline (no recharts dependency) ─────────────────────────────
function MiniSparkline({ data, color, height = 32 }: { data: number[]; color: string; height?: number }) {
  if (!data.length) return null
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const w = 100
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" style={{ height }} preserveAspectRatio="none">
      <polyline fill="none" stroke={color} strokeWidth={2} points={points} strokeLinejoin="round" strokeLinecap="round" />
      <polyline fill={`${color}20`} stroke="none" points={`0,${height} ${points} ${w},${height}`} />
    </svg>
  )
}

// ─── SVG Mini Bar Chart ──────────────────────────────────────────────────────
function MiniBarChart({ data, color, height = 120 }: { data: { label: string; value: number }[]; color: string; height?: number }) {
  if (!data.length) return null
  const max = Math.max(...data.map(d => d.value))
  const barW = 100 / data.length
  return (
    <svg viewBox={`0 0 100 ${height}`} className="w-full" style={{ height }} preserveAspectRatio="none">
      {data.map((d, i) => {
        const barH = (d.value / max) * (height - 20)
        return (
          <g key={i}>
            <rect x={i * barW + 1} y={height - 14 - barH} width={barW - 2} height={barH} fill={color} rx={1.5} opacity={0.7} />
            <text x={i * barW + barW / 2} y={height - 2} textAnchor="middle" fill="currentColor" fontSize={4} fontFamily="monospace">{d.label}</text>
          </g>
        )
      })}
    </svg>
  )
}

// ─── SVG Mini Donut Chart ────────────────────────────────────────────────────
function MiniDonut({ segments, size = 120 }: { segments: { value: number; color: string; label: string }[]; size?: number }) {
  const total = segments.reduce((s, d) => s + d.value, 0)
  let cumulative = 0
  const r = 35; const cx = 50; const cy = 50; const sw = 10
  return (
    <svg viewBox="0 0 100 100" className="w-full" style={{ maxWidth: size }}>
      {segments.map((seg, i) => {
        const pct = seg.value / total
        const circumference = 2 * Math.PI * r
        const dashLen = pct * circumference
        const gap = circumference - dashLen
        const rotation = (cumulative / total) * 360 - 90
        cumulative += seg.value
        return (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={seg.color} strokeWidth={sw}
            strokeDasharray={`${dashLen} ${gap}`} transform={`rotate(${rotation} ${cx} ${cy})`} strokeLinecap="round" />
        )
      })}
      <text x={cx} y={cy - 2} textAnchor="middle" fill="currentColor" fontSize={10} fontWeight="bold">{total}</text>
      <text x={cx} y={cy + 8} textAnchor="middle" fill="currentColor" fontSize={5} opacity={0.6}>TASKS</text>
    </svg>
  )
}

// ─── Mini Components ──────────────────────────────────────────────────────────
function AnimatedNumber({ value }: { value: number }) {
  return (
    <motion.span key={value} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: 'easeOut' }} className="tabular-nums">
      {value.toLocaleString()}
    </motion.span>
  )
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'active' || status === 'online' ? 'bg-emerald-500' : status === 'warning' || status === 'degraded' ? 'bg-yellow-500' : status === 'unknown' ? 'bg-gray-500' : 'bg-red-500'
  return (
    <span className="relative flex h-2.5 w-2.5">
      {(status === 'active' || status === 'online') && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />}
      <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', color)} />
    </span>
  )
}

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
    { from: 'dashboard', to: 'gateway' }, { from: 'gateway', to: 'worker1' }, { from: 'gateway', to: 'worker2' },
    { from: 'gateway', to: 'worker3' }, { from: 'gateway', to: 'coord' }, { from: 'worker1', to: 'premium' },
    { from: 'worker1', to: 'mid' }, { from: 'worker2', to: 'mid' }, { from: 'worker2', to: 'fast' },
    { from: 'worker3', to: 'fast' }, { from: 'worker3', to: 'premium' }, { from: 'coord', to: 'providers' },
    { from: 'coord', to: 'mid' }, { from: 'premium', to: 'providers' }, { from: 'mid', to: 'providers' }, { from: 'fast', to: 'providers' },
  ]
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]))
  return (
    <svg viewBox="0 0 400 270" className="w-full h-full" style={{ maxHeight: 260 }}>
      {links.map((link, i) => {
        const from = nodeMap[link.from]; const to = nodeMap[link.to]
        if (!from || !to) return null
        return <line key={i} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#374151" strokeWidth={1} strokeOpacity={0.5} />
      })}
      {nodes.map((node) => (
        <g key={node.id}>
          <motion.circle cx={node.x} cy={node.y} r={node.r} fill={node.color} fillOpacity={0.2} stroke={node.color} strokeWidth={1.5}
            animate={{ fillOpacity: [0.15, 0.3, 0.15] }} transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }} />
          <text x={node.x} y={node.y + 4} textAnchor="middle" fill={node.color} fontSize={8} fontWeight={600} fontFamily="monospace">{node.label}</text>
        </g>
      ))}
      <text x={15} y={35} fill="#6b7280" fontSize={7} fontFamily="monospace">UI</text>
      <text x={15} y={95} fill="#6b7280" fontSize={7} fontFamily="monospace">ROUTING</text>
      <text x={15} y={160} fill="#6b7280" fontSize={7} fontFamily="monospace">AGENTS</text>
      <text x={15} y={235} fill="#6b7280" fontSize={7} fontFamily="monospace">MODELS</text>
    </svg>
  )
}

// ─── Tab Panels ───────────────────────────────────────────────────────────────
function OverviewTab() {
  const [activeConnections, setActiveConnections] = useState(247)
  const [requestsPerSec, setRequestsPerSec] = useState(34)
  const [tokensPerMin, setTokensPerMin] = useState(1420)
  const [errorRate, setErrorRate] = useState(0.3)
  const [rpsHistory, setRpsHistory] = useState<number[]>([32, 35, 28, 31, 34, 30, 33, 36, 29, 34])
  const [alerts, setAlerts] = useState(alertFeedData)

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveConnections(p => Math.max(150, Math.min(400, p + Math.floor(Math.random() * 20) - 10)))
      setRequestsPerSec(p => Math.max(10, Math.min(80, p + Math.floor(Math.random() * 8) - 4)))
      setTokensPerMin(p => Math.max(500, Math.min(3000, p + Math.floor(Math.random() * 200) - 100)))
      setErrorRate(p => Math.max(0, Math.min(5, parseFloat((p + (Math.random() * 0.4) - 0.2).toFixed(1)))))
      setRpsHistory(p => [...p.slice(1), Math.max(10, Math.min(80, p[p.length - 1] + Math.floor(Math.random() * 8) - 4))])
      setAlerts(prev => {
        const severities: Array<'critical' | 'warning' | 'info' | 'success'> = ['critical', 'warning', 'info', 'success']
        const messages = ['Memory usage spike on worker-2', 'Provider rate limit approaching for groq', 'Token burn rate increased 12%', 'Cache hit ratio improved to 94%', 'New constitutional rule validated']
        const sources = ['System', 'Gateway', 'Tokens', 'Governor', 'ModelRelay']
        return [{ id: Math.max(...prev.map(a => a.id)) + 1, severity: severities[Math.floor(Math.random() * severities.length)], message: messages[Math.floor(Math.random() * messages.length)], source: sources[Math.floor(Math.random() * sources.length)], time: Date.now() }, ...prev.slice(0, 4)]
      })
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const errorRateColor = errorRate > 2 ? 'text-red-500' : errorRate > 1 ? 'text-yellow-500' : 'text-emerald-500'

  // Bar chart data
  const hourlyRequests = useMemo(() => Array.from({ length: 12 }, (_, i) => ({ label: `${i + 10}`, value: [312, 289, 378, 425, 356, 298, 410, 467, 389, 342, 315, 245][i] })), [])

  return (
    <div className="space-y-6">
      {/* Live System Metrics */}
      <Card className="bg-card/50 border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 to-transparent">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Radio className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Live System Metrics
            <Badge variant="outline" className="text-[9px] bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-emerald-600/30">
              <span className="relative flex h-1.5 w-1.5 mr-1"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" /></span>
              LIVE
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Active Connections', value: activeConnections, unit: '', icon: Wifi },
              { label: 'Requests/sec', value: requestsPerSec, unit: 'req/s', icon: Activity, spark: rpsHistory },
              { label: 'Tokens/min', value: tokensPerMin, unit: 'tok/min', icon: Zap },
              { label: 'Error Rate', value: errorRate, unit: '%', icon: AlertCircle, color: errorRateColor },
            ].map((metric) => (
              <div key={metric.label} className="bg-gradient-to-br from-emerald-600/5 to-transparent p-3 rounded-lg border border-border/30">
                <div className="flex items-center gap-2 mb-1">
                  <metric.icon className={cn('h-3.5 w-3.5', metric.color || 'text-emerald-600 dark:text-emerald-400')} />
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{metric.label}</span>
                </div>
                <div className="flex items-end gap-2">
                  <span className={cn('text-2xl font-bold', metric.color || 'text-emerald-600 dark:text-emerald-400')}>
                    <AnimatedNumber value={metric.value} />
                  </span>
                  {metric.unit && <span className="text-[10px] text-muted-foreground mb-1">{metric.unit}</span>}
                </div>
                {metric.spark && <div className="mt-1"><MiniSparkline data={metric.spark} color="#10b981" /></div>}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Network Topology & Alert Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
            <div className="flex flex-wrap gap-3 mt-2">
              {[{ c: 'bg-emerald-500', l: 'Healthy' }, { c: 'bg-yellow-500', l: 'Degraded' }, { c: 'bg-blue-500', l: 'Mid Pool' }, { c: 'bg-orange-500', l: 'Fast Pool' }, { c: 'bg-purple-500', l: 'Providers' }].map(item => (
                <div key={item.l} className="flex items-center gap-1.5"><span className={cn('h-2 w-2 rounded-full', item.c)} /><span className="text-[9px] text-muted-foreground">{item.l}</span></div>
              ))}
            </div>
          </CardContent>
        </Card>

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
            <div className="space-y-1.5 max-h-[260px] overflow-y-auto">
              <AnimatePresence mode="popLayout">
                {alerts.map((alert) => {
                  const config = alertSeverityConfig[alert.severity]
                  const Icon = config.icon
                  return (
                    <motion.div key={alert.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.3 }}
                      className={cn('flex items-center gap-2.5 p-2 rounded-lg border', config.bg, config.border)}>
                      <Icon className={cn('h-3.5 w-3.5 shrink-0', config.color)} />
                      <span className="text-xs flex-1 truncate">{alert.message}</span>
                      <Badge variant="outline" className="text-[8px] shrink-0">{alert.source}</Badge>
                      <span className="text-[9px] text-muted-foreground whitespace-nowrap shrink-0">{getRelativeTime(alert.time)}</span>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Health Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {healthCards.map((card) => (
          <Card key={card.label} className="bg-card/50 border-border/50 hover:scale-[1.02] transition-transform duration-200 cursor-default group">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2"><card.icon className="h-4 w-4 text-muted-foreground" /><span className="text-xs text-muted-foreground">{card.label}</span></div>
                <Badge variant="outline" className={cn('text-[10px]', card.trend === 'down' ? 'text-emerald-600 dark:text-emerald-400' : 'text-yellow-600 dark:text-yellow-400')}>
                  {card.trend === 'down' ? <ArrowDownRight className="h-3 w-3 mr-0.5" /> : <ArrowUpRight className="h-3 w-3 mr-0.5" />}{card.trend === 'down' ? 'Good' : 'Watch'}
                </Badge>
              </div>
              <div className="mt-2"><span className="text-2xl font-bold">{card.value}</span><span className="text-sm text-muted-foreground ml-1">{card.unit}</span></div>
              {card.label !== 'Uptime' && (
                <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                  <motion.div className="h-full rounded-full" style={{ backgroundColor: card.color }}
                    initial={{ width: 0 }} animate={{ width: `${card.label === 'API Latency' ? Math.min(card.value / 3, 100) : card.value}%` }}
                    transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }} />
                </div>
              )}
              <div className="mt-2 opacity-60 group-hover:opacity-100 transition-opacity"><MiniSparkline data={card.sparkData} color={card.color} /></div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Request Volume & Task Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Request Volume (12h)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <MiniBarChart data={hourlyRequests} color="#10b981" height={140} />
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Task Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="flex items-center gap-4">
              <MiniDonut segments={[
                { value: 47, color: '#10b981', label: 'Research' },
                { value: 31, color: '#3b82f6', label: 'Coding' },
                { value: 38, color: '#f97316', label: 'Analysis' },
                { value: 12, color: '#8b5cf6', label: 'Governance' },
              ]} />
              <div className="space-y-2">
                {[{ l: 'Research', v: 47, c: 'bg-emerald-500' }, { l: 'Coding', v: 31, c: 'bg-blue-500' }, { l: 'Analysis', v: 38, c: 'bg-orange-500' }, { l: 'Governance', v: 12, c: 'bg-purple-500' }].map(s => (
                  <div key={s.l} className="flex items-center gap-2"><span className={cn('h-2 w-2 rounded-full', s.c)} /><span className="text-xs text-muted-foreground">{s.l}</span><span className="text-xs font-bold ml-auto">{s.v}</span></div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Agent Status & Model Pools */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="bg-card/50 border-border/50 lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2"><Users className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Agent Status</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {agents.map((agent) => (
                <div key={agent.name} className={cn('flex items-center gap-3 p-2 rounded-lg bg-muted/30 border-l-2', agent.status === 'active' ? 'border-l-emerald-500' : 'border-l-yellow-500')}>
                  <StatusDot status={agent.status} /><span className="text-sm font-medium">{agent.name}</span>
                  <span className="text-[10px] font-mono text-muted-foreground">{agent.model}</span><span className="flex-1" />
                  <Badge variant="outline" className="text-[10px]">{agent.domain}</Badge>
                  <div className="flex items-center gap-1"><Shield className="h-3 w-3 text-muted-foreground" /><span className="text-xs font-mono">{agent.trust.toFixed(2)}</span></div>
                  <span className="text-xs text-muted-foreground">{agent.tasks} tasks</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Model Pools</CardTitle></CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {modelPools.map((pool) => (
                <div key={pool.name} className="space-y-1.5">
                  <div className="flex items-center justify-between"><span className="text-xs font-semibold">{pool.name}</span><span className="text-xs font-mono text-emerald-600 dark:text-emerald-400">{pool.health}%</span></div>
                  <Progress value={pool.health} className="h-1.5" />
                  <div className="flex flex-wrap gap-1">{pool.models.map((model) => <Badge key={model} variant="secondary" className="text-[9px] h-4">{model}</Badge>)}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Recent Activity</CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {recentActivity.map((item, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                {item.type === 'success' ? <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  : item.type === 'warning' ? <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 shrink-0" />
                  : <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" />}
                <span className="text-sm flex-1">{item.event}</span>
                <Badge variant="outline" className="text-[10px] shrink-0">{item.source}</Badge>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">{getRelativeTime(item.time)}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ProvidersTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Online', count: providers.filter(p => p.status === 'online').length, color: 'text-emerald-500' },
          { label: 'Degraded', count: providers.filter(p => p.status === 'degraded').length, color: 'text-yellow-500' },
          { label: 'Unknown', count: providers.filter(p => p.status === 'unknown').length, color: 'text-gray-500' },
          { label: 'Total', count: providers.length, color: 'text-emerald-600 dark:text-emerald-400' },
        ].map(s => (
          <Card key={s.label} className="bg-card/50 border-border/50">
            <CardContent className="p-4 text-center"><span className={cn('text-3xl font-bold', s.color)}>{s.count}</span><p className="text-xs text-muted-foreground mt-1">{s.label}</p></CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><Server className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Provider Registry<Badge variant="outline" className="text-[9px] ml-auto">{providers.length} Providers</Badge></CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {providers.map((p) => (
              <div key={p.name} className={cn('flex items-center gap-3 p-3 rounded-lg border border-border/30 hover:border-emerald-600/20 transition-colors', p.status === 'unknown' && 'opacity-60')}>
                <StatusDot status={p.status} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2"><span className="text-sm font-medium truncate">{p.name}</span><Badge variant="secondary" className="text-[9px] h-4">{p.model}</Badge></div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-[10px] text-muted-foreground">Latency: <span className="font-mono">{p.latency}ms</span></span>
                    <span className="text-[10px] text-muted-foreground">Quota: <span className="font-mono">{p.quota}%</span></span>
                  </div>
                  <div className="mt-1.5 h-1 rounded-full bg-muted overflow-hidden"><div className="h-full rounded-full" style={{ width: `${p.quota}%`, backgroundColor: p.color }} /></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function AgentsTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map(agent => (
          <Card key={agent.name} className={cn('bg-card/50 border-border/50', agent.status === 'warning' && 'border-yellow-600/30')}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-3"><StatusDot status={agent.status} /><span className="font-semibold">{agent.name}</span><Badge variant="outline" className="text-[9px] ml-auto">{agent.domain}</Badge></div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs"><span className="text-muted-foreground">Model</span><span className="font-mono">{agent.model}</span></div>
                <div className="flex justify-between text-xs"><span className="text-muted-foreground">Trust</span><span className={cn('font-mono font-semibold', agent.trust >= 0.9 ? 'text-emerald-500' : agent.trust >= 0.8 ? 'text-yellow-500' : 'text-red-500')}>{agent.trust.toFixed(2)}</span></div>
                <div className="flex justify-between text-xs"><span className="text-muted-foreground">Tasks</span><span className="font-mono">{agent.tasks}</span></div>
                <div className="flex justify-between text-xs"><span className="text-muted-foreground">Uptime</span><span className="font-mono">{agent.uptime}</span></div>
                <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                  <motion.div className={cn('h-full rounded-full', agent.trust >= 0.9 ? 'bg-emerald-500' : agent.trust >= 0.8 ? 'bg-yellow-500' : 'bg-red-500')}
                    initial={{ width: 0 }} animate={{ width: `${agent.trust * 100}%` }} transition={{ duration: 0.8 }} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function GmrTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {modelPools.map(pool => (
          <Card key={pool.name} className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2"><span className="text-sm font-semibold">{pool.name} Pool</span><span className="text-lg font-bold" style={{ color: pool.color }}>{pool.health}%</span></div>
              <Progress value={pool.health} className="h-2 mb-2" />
              <div className="flex flex-wrap gap-1">{pool.models.map(m => <Badge key={m} variant="secondary" className="text-[9px] h-4">{m}</Badge>)}</div>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><Network className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Route History</CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {gmrRouteHistory.map((entry, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                <span className="text-[10px] font-mono text-muted-foreground w-16">{entry.time}</span>
                <Badge variant="outline" className="text-[9px]">{entry.model}</Badge>
                <Badge variant="secondary" className="text-[9px] h-4">{entry.pool}</Badge>
                <Badge variant="outline" className="text-[9px] h-4">{entry.agent}</Badge>
                <span className="text-xs font-mono text-muted-foreground">{entry.latency}ms</span>
                <span className="text-xs font-mono text-muted-foreground">{entry.tokens} tok</span>
                <Badge className={cn('text-[9px] h-4', entry.status === 'success' ? 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400' : 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400')}>{entry.status}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function GovernorTab() {
  return (
    <div className="space-y-6">
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Constitutional Rules<Badge variant="outline" className="text-[9px] ml-auto bg-emerald-600/10 text-emerald-600 dark:text-emerald-400">{governorRules.filter(r => r.status === 'active').length} Active</Badge></CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-3">
            {governorRules.map(rule => (
              <div key={rule.id} className="flex items-center gap-3 p-3 rounded-lg border border-border/30 hover:border-emerald-600/20 transition-colors">
                <Badge variant="outline" className="text-[9px] font-mono">{rule.id}</Badge>
                <div className="flex-1"><span className="text-sm font-medium">{rule.name}</span><span className="text-xs text-muted-foreground ml-2">— {rule.rule}</span></div>
                <Badge className={cn('text-[9px]', rule.violations > 0 ? 'bg-red-600/20 text-red-600 dark:text-red-400' : 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400')}>{rule.violations > 0 ? `${rule.violations} violations` : 'Clean'}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card className="bg-card/50 border-emerald-600/10">
        <CardContent className="p-4">
          <div className="flex items-center gap-3"><ShieldCheck className="h-8 w-8 text-emerald-600 dark:text-emerald-400" /><div><h3 className="font-semibold text-emerald-600 dark:text-emerald-400">Constitution Active</h3><p className="text-xs text-muted-foreground">All limits within bounds: 3/5 agents, 12/20 API calls, 8/30 writes. Last check: 2m ago.</p></div></div>
        </CardContent>
      </Card>
    </div>
  )
}

function ResearchTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Vetted', count: researchPapers.filter(p => p.status === 'vetted').length, color: 'text-emerald-500' },
          { label: 'Pending', count: researchPapers.filter(p => p.status === 'pending').length, color: 'text-yellow-500' },
          { label: 'P1 Queue', count: researchPapers.filter(p => p.queue === 'P1').length, color: 'text-red-500' },
          { label: 'Total', count: researchPapers.length, color: 'text-emerald-600 dark:text-emerald-400' },
        ].map(s => (
          <Card key={s.label} className="bg-card/50 border-border/50"><CardContent className="p-4 text-center"><span className={cn('text-3xl font-bold', s.color)}>{s.count}</span><p className="text-xs text-muted-foreground mt-1">{s.label}</p></CardContent></Card>
        ))}
      </div>
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><BookOpen className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Research Papers</CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2">
            {researchPapers.map((paper, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg border border-border/30 hover:border-emerald-600/20 transition-colors">
                <Sparkles className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium truncate block">{paper.title}</span>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className="text-[9px]">Relevance: {paper.relevance}%</Badge>
                    <Badge className={cn('text-[9px]', paper.queue === 'P1' ? 'bg-red-600/20 text-red-600 dark:text-red-400' : 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400')}>{paper.queue}</Badge>
                  </div>
                </div>
                <Badge className={cn('text-[9px]', paper.status === 'vetted' ? 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400' : 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400')}>{paper.status}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function StressLabTab() {
  return (
    <div className="space-y-6">
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><FlaskConical className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />ISC Test Results</CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-3">
            {stressTests.map(test => (
              <div key={test.id} className={cn('p-4 rounded-lg border', test.result === 'COLLAPSE' ? 'border-red-500/30 bg-red-500/5' : test.result === 'DEGRADED' ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-emerald-500/30 bg-emerald-500/5')}>
                <div className="flex items-center gap-3 mb-2">
                  <Badge variant="outline" className="text-[9px] font-mono">{test.id}</Badge>
                  <span className="text-sm font-medium">{test.model}</span>
                  <Badge variant="outline" className="text-[9px]">{test.type}</Badge>
                  <Badge className={cn('text-[9px] ml-auto', test.result === 'COLLAPSE' ? 'bg-red-600/20 text-red-600 dark:text-red-400' : test.result === 'DEGRADED' ? 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400' : 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400')}>{test.result}</Badge>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-muted-foreground">Rate: <span className={cn('font-mono font-bold', test.rate > 50 ? 'text-red-500' : test.rate > 10 ? 'text-yellow-500' : 'text-emerald-500')}>{test.rate}%</span></span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden"><div className={cn('h-full rounded-full', test.rate > 50 ? 'bg-red-500' : test.rate > 10 ? 'bg-yellow-500' : 'bg-emerald-500')} style={{ width: `${test.rate}%` }} /></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function TokensTab() {
  const used = 73450; const budget = 100000; const pct = (used / budget * 100).toFixed(1)
  const tokenHistory = Array.from({ length: 8 }, (_, i) => ({ label: `${i + 10}h`, value: Math.floor((i + 1) * used / 8) }))
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-card/50 border-border/50"><CardContent className="p-4 text-center"><span className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{used.toLocaleString()}</span><p className="text-xs text-muted-foreground mt-1">Tokens Used</p></CardContent></Card>
        <Card className="bg-card/50 border-border/50"><CardContent className="p-4 text-center"><span className="text-3xl font-bold">{budget.toLocaleString()}</span><p className="text-xs text-muted-foreground mt-1">Session Budget</p></CardContent></Card>
        <Card className={cn('bg-card/50 border-border/50', parseFloat(pct) > 80 ? 'border-red-600/30' : 'border-yellow-600/30')}>
          <CardContent className="p-4 text-center"><span className={cn('text-3xl font-bold', parseFloat(pct) > 80 ? 'text-red-500' : 'text-yellow-500')}>{pct}%</span><p className="text-xs text-muted-foreground mt-1">Budget Used</p></CardContent>
        </Card>
      </div>
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3"><CardTitle className="text-sm font-semibold flex items-center gap-2"><Coins className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />Token Consumption</CardTitle></CardHeader>
        <CardContent className="p-4 pt-0">
          <MiniSparkline data={tokenHistory.map(t => t.value)} color="#10b981" height={80} />
        </CardContent>
      </Card>
    </div>
  )
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
const tabComponents: Record<TabId, React.ComponentType> = {
  overview: OverviewTab, providers: ProvidersTab, agents: AgentsTab, gmr: GmrTab,
  governor: GovernorTab, research: ResearchTab, stresslab: StressLabTab, tokens: TokensTab,
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [time, setTime] = useState('--:--:--')
  const { setTheme, theme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])
  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    update(); const interval = setInterval(update, 1000); return () => clearInterval(interval)
  }, [])

  const ActiveTabComponent = tabComponents[activeTab] || OverviewTab

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* ─── Sidebar ─── */}
      <aside className={cn('hidden md:flex flex-col bg-card/80 backdrop-blur-sm border-r border-border/60 transition-all duration-300', sidebarOpen ? 'w-56' : 'w-16')}>
        <div className="flex h-14 items-center gap-2 px-3 border-b border-border/50">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-md shadow-emerald-600/20"><Zap className="h-4 w-4 text-white" /></div>
          <AnimatePresence>
            {sidebarOpen && (
              <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }} transition={{ duration: 0.2 }} className="flex flex-col overflow-hidden">
                <span className="text-sm font-bold tracking-tight text-foreground">NEXUS OS</span><span className="text-[10px] text-muted-foreground">v3.1 — Intelligence Dashboard</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="px-3 pt-1 pb-2">
              <div className="grid grid-cols-3 gap-1 rounded-lg border border-border/40 bg-muted/30 p-1.5">
                {[
                  { icon: <Activity className="h-3 w-3 text-emerald-500" />, val: '99.7%', label: 'Uptime' },
                  { icon: <Users className="h-3 w-3 text-emerald-500" />, val: '4', label: 'Agents' },
                  { icon: <Globe className="h-3 w-3 text-emerald-500" />, val: '14', label: 'Provs' },
                ].map((s, i) => (
                  <div key={i} className={cn('flex flex-col items-center gap-0.5 py-1', i === 1 && 'border-x border-border/30')}>
                    {s.icon}<span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{s.val}</span>
                    <span className="text-[8px] text-muted-foreground/60 uppercase tracking-wider">{s.label}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <nav className="flex-1 space-y-0.5 p-2 overflow-y-auto">
          {navGroups.map((group, gi) => (
            <div key={group.label}>
              {gi > 0 && <div className="mx-2 my-1.5 border-t border-border/40" />}
              {sidebarOpen && <div className="px-2.5 py-1 text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/50">{group.label}</div>}
              {group.items.map(item => (
                <button key={item.id} onClick={() => setActiveTab(item.id)}
                  className={cn('relative flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-200',
                    activeTab === item.id ? 'bg-gradient-to-r from-emerald-600/20 to-emerald-600/5 text-emerald-600 dark:text-emerald-400 shadow-sm shadow-emerald-600/10'
                      : 'text-muted-foreground hover:bg-emerald-600/10 hover:text-accent-foreground')}>
                  {activeTab === item.id && <motion.span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r bg-emerald-500" animate={{ boxShadow: ['0 0 6px rgba(52,211,153,0.4)', '0 0 14px rgba(52,211,153,0.7)', '0 0 6px rgba(52,211,153,0.4)'] }} transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }} />}
                  <span className={cn('shrink-0 transition-transform duration-200', activeTab === item.id && 'scale-110')}>{item.icon}</span>
                  {sidebarOpen && <><span className="flex-1 text-left truncate">{item.label}</span><kbd className="pointer-events-none inline-flex h-4 select-none items-center rounded border border-border/50 bg-muted/50 px-1 font-mono text-[9px] font-medium text-muted-foreground/50">{item.shortcut}</kbd>{item.badge && <Badge variant="secondary" className="h-4 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">{item.badge}</Badge>}</>}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="border-t border-border p-3">
          {sidebarOpen ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="relative flex h-2.5 w-2.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" /></span>System Operational
            </div>
          ) : (
            <span className="relative mx-auto flex h-2.5 w-2.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" /></span>
          )}
        </div>
        <div className="border-t border-border p-2">
          <Button variant="ghost" size="icon" className="h-7 w-full text-muted-foreground hover:text-foreground" onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? <ChevronLeft className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </aside>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 md:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setMobileMenuOpen(false)} />
            <motion.div initial={{ x: -256 }} animate={{ x: 0 }} exit={{ x: -256 }} transition={{ duration: 0.2 }} className="relative w-64 h-full bg-card border-r border-border overflow-y-auto">
              <div className="flex h-14 items-center gap-2 px-3 border-b border-border/50">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700"><Zap className="h-4 w-4 text-white" /></div>
                <div><span className="text-sm font-bold">NEXUS OS</span><br /><span className="text-[10px] text-muted-foreground">v3.1</span></div>
              </div>
              <nav className="p-2">
                {navGroups.map((group, gi) => (
                  <div key={group.label}>
                    {gi > 0 && <div className="mx-2 my-1.5 border-t border-border/40" />}
                    <div className="px-2.5 py-1 text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/50">{group.label}</div>
                    {group.items.map(item => (
                      <button key={item.id} onClick={() => { setActiveTab(item.id); setMobileMenuOpen(false) }}
                        className={cn('flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-all', activeTab === item.id ? 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground hover:bg-muted/50')}>
                        {item.icon}<span>{item.label}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </nav>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main */}
      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex flex-col">
          <div className="h-1 w-full overflow-hidden bg-muted/20">
            <motion.div className="h-full bg-gradient-to-r from-emerald-500 via-emerald-400 to-emerald-500" initial={{ width: '0%' }} animate={{ width: '94%' }} transition={{ duration: 1, ease: 'easeOut' }} />
          </div>
          <div className="flex h-14 items-center gap-3 border-b border-border/60 bg-card/80 backdrop-blur-md px-4 relative">
            <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-600/30 to-transparent" />
            <Button variant="ghost" size="icon" className="h-8 w-8 md:hidden" onClick={() => setMobileMenuOpen(true)}><Menu className="h-4 w-4" /></Button>
            <div className="hidden sm:flex items-center gap-1.5"><span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" /></span><span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">Online</span></div>
            <div className="hidden md:flex items-center gap-1 text-[10px] text-muted-foreground"><span className="font-semibold text-emerald-600 dark:text-emerald-400">NEXUS OS</span><ChevronRight className="h-3 w-3 text-muted-foreground/40" /><span className="font-medium text-foreground">{tabTitles[activeTab]}</span></div>
            <div className="flex-1 min-w-0 md:hidden"><h1 className="text-sm font-semibold truncate gradient-text">{tabTitles[activeTab]}</h1></div>
            <div className="hidden sm:flex items-center gap-2 ml-auto">
              <Badge variant="outline" className="gap-1.5 text-[10px]"><span className="relative flex h-1.5 w-1.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" /></span>4 agents</Badge>
              <Badge variant="outline" className="gap-1 text-[10px] font-mono"><Activity className="h-3 w-3 text-emerald-500" />34 req/s</Badge>
            </div>
            {mounted && <span className="hidden md:flex font-mono text-xs text-muted-foreground tabular-nums">{time}</span>}
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" /><Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            </Button>
          </div>
        </header>

        <main className="relative flex-1 overflow-auto bg-background">
          <div className="pointer-events-none absolute inset-0 grid-pattern-animated opacity-40" />
          <AnimatePresence mode="wait">
            <motion.div key={activeTab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.2, ease: 'easeOut' }} className="relative z-10 p-4 md:p-6">
              <ActiveTabComponent />
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className="relative flex flex-wrap items-center justify-between gap-2 border-t border-border bg-card px-4 py-2">
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">NEXUS OS v3.1</span>
            <span className="hidden sm:inline">— Cloud Intelligence Dashboard</span>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400"><Heart className="h-3 w-3 fill-emerald-500/80 animate-pulse" />Operational</span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="hidden md:inline">Constitution: 5 agents/hr · 20 API/session · 2 concurrent · 30 writes</span>
            <span className="text-border">|</span>
            <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500 pulse-dot" />Live</span>
            <span className="text-border">|</span>
            <span className="text-[10px] text-muted-foreground/60">z-ai SDK</span>
          </div>
        </footer>
      </div>
    </div>
  )
}
