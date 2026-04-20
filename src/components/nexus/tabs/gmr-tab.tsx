'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'
import { useApiData } from '@/hooks/use-api-data'
import { Activity, Zap, Wifi, WifiOff, RefreshCw, Gauge, RotateCcw, ArrowRightLeft, AlertTriangle, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { useState, useEffect, useMemo, useCallback } from 'react'
import { toast } from 'sonner'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

const latencyHistory = [
  { name: '10m', qwen: 1200, trinity: 1350, gemma: 340 },
  { name: '8m', qwen: 1180, trinity: 1290, gemma: 350 },
  { name: '6m', qwen: 1240, trinity: 1410, gemma: 330 },
  { name: '4m', qwen: 1190, trinity: 1320, gemma: 360 },
  { name: '2m', qwen: 1210, trinity: 1380, gemma: 345 },
  { name: 'now', qwen: 1200, trinity: 1350, gemma: 340 },
]

// Model performance comparison data for grouped bar chart
const modelPerformanceData = [
  { name: 'qwen3', health: 96, successRate: 97, latency: 88 },
  { name: 'trinity', health: 99, successRate: 99, latency: 82 },
  { name: 'gemma', health: 100, successRate: 95, latency: 95 },
  { name: 'nemotron', health: 92, successRate: 94, latency: 90 },
  { name: 'kimi', health: 91, successRate: 93, latency: 85 },
  { name: 'minimax', health: 94, successRate: 96, latency: 87 },
]

// Failover log data
const failoverLog = [
  { time: '14:22:45', from: 'gemma-fast', to: 'qwen3-coder', reason: 'Health fallback: 88%', severity: 'warning' },
  { time: '14:20:55', from: 'gemma-fast', to: 'kimi-k2.5', reason: 'Health fallback: 88%', severity: 'warning' },
  { time: '14:20:12', from: 'nemotron-3-super', to: 'gpt-oss-120b', reason: 'Rate limit backoff', severity: 'info' },
  { time: '13:58:30', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Latency spike: 2400ms', severity: 'warning' },
  { time: '13:45:12', from: 'dolphin-mistral-venice', to: 'trinity-large-preview', reason: 'Model disabled by admin', severity: 'critical' },
]

// Rotation analytics data
const rotationAnalytics = {
  mostRotatedTo: [
    { model: 'trinity-large-preview', count: 23 },
    { model: 'qwen3-coder', count: 18 },
    { model: 'kimi-k2.5', count: 12 },
  ],
  mostRotatedFrom: [
    { model: 'gemma-fast', count: 19 },
    { model: 'dolphin-mistral-venice', count: 15 },
    { model: 'nemotron-3-super', count: 11 },
  ],
}

// Per-model sparkline data for pool cards
const modelSparklines: Record<string, { name: string; value: number }[]> = {
  'trinity-large-preview': [
    { name: '1', value: 95 }, { name: '2', value: 97 }, { name: '3', value: 99 },
    { name: '4', value: 96 }, { name: '5', value: 98 }, { name: '6', value: 99 },
  ],
  'minimax-m2.5': [
    { name: '1', value: 90 }, { name: '2', value: 93 }, { name: '3', value: 91 },
    { name: '4', value: 94 }, { name: '5', value: 92 }, { name: '6', value: 94 },
  ],
  'qwen3-coder': [
    { name: '1', value: 96 }, { name: '2', value: 94 }, { name: '3', value: 97 },
    { name: '4', value: 95 }, { name: '5', value: 96 }, { name: '6', value: 96 },
  ],
  'kimi-k2.5': [
    { name: '1', value: 88 }, { name: '2', value: 91 }, { name: '3', value: 90 },
    { name: '4', value: 92 }, { name: '5', value: 91 }, { name: '6', value: 91 },
  ],
  'gpt-oss-120b': [
    { name: '1', value: 82 }, { name: '2', value: 85 }, { name: '3', value: 83 },
    { name: '4', value: 86 }, { name: '5', value: 84 }, { name: '6', value: 85 },
  ],
  'gemma-fast': [
    { name: '1', value: 100 }, { name: '2', value: 98 }, { name: '3', value: 100 },
    { name: '4', value: 99 }, { name: '5', value: 100 }, { name: '6', value: 100 },
  ],
  'nemotron-3-super': [
    { name: '1', value: 92 }, { name: '2', value: 90 }, { name: '3', value: 93 },
    { name: '4', value: 91 }, { name: '5', value: 92 }, { name: '6', value: 92 },
  ],
  'dolphin-mistral-venice': [
    { name: '1', value: 85 }, { name: '2', value: 82 }, { name: '3', value: 88 },
    { name: '4', value: 80 }, { name: '5', value: 84 }, { name: '6', value: 83 },
  ],
}

const poolDefinitions = [
  {
    name: 'PREMIUM',
    desc: 'Tier 90+ · Complex reasoning & security',
    modelNames: ['trinity-large-preview', 'minimax-m2.5'],
    tierRange: '90+',
    color: COLORS.emerald,
    gradient: 'from-emerald-600/10',
  },
  {
    name: 'MID',
    desc: 'Tier 60-89 · Code & research',
    modelNames: ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'],
    tierRange: '60-89',
    color: COLORS.blue,
    gradient: 'from-blue-600/10',
  },
  {
    name: 'FAST',
    desc: 'Tier <60 · Quick responses',
    modelNames: ['gemma-fast', 'nemotron-3-super'],
    tierRange: '<60',
    color: COLORS.orange,
    gradient: 'from-orange-600/10',
  },
  {
    name: 'FREE_RESEARCH',
    desc: 'StressLab + heretic control group',
    modelNames: ['dolphin-mistral-venice', 'qwen3-coder', 'trinity-large-preview'],
    tierRange: 'any',
    color: COLORS.purple,
    gradient: 'from-purple-600/10',
  },
]

const rotationLog = [
  { time: '14:23:01', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Domain: reason', tokens: 0 },
  { time: '14:22:45', from: 'gemma-fast', to: 'qwen3-coder', reason: 'Domain: code', tokens: 340 },
  { time: '14:22:12', from: '-', to: 'gemma-fast', reason: 'New request: fast', tokens: 340 },
  { time: '14:21:58', from: 'trinity-large-preview', to: 'nemotron-3-super', reason: 'Domain: research', tokens: 1280 },
  { time: '14:21:30', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Escalation: sec domain', tokens: 890 },
  { time: '14:20:55', from: 'gemma-fast', to: 'kimi-k2.5', reason: 'Health fallback: 88%', tokens: 450 },
  { time: '14:20:12', from: 'nemotron-3-super', to: 'gpt-oss-120b', reason: 'Rate limit backoff', tokens: 220 },
  { time: '14:19:45', from: 'trinity-large-preview', to: 'minimax-m2.5', reason: 'Domain: general', tokens: 560 },
]

interface ModelData {
  id: string
  name: string
  provider: string
  tier: number
  domain: string
  health: number
  latencyMs: number
  isFree: boolean
  isActive: boolean
  totalCalls: number
  successRate: number
}

// Pool Health Overview Component - compact horizontal stacked bar
function PoolHealthOverview({ models }: { models: ModelData[] }) {
  const poolHealthData = useMemo(() => {
    return poolDefinitions.map(pool => {
      const poolModels = models.filter(m => pool.modelNames.includes(m.name))
      const activeCount = poolModels.filter(m => m.isActive).length
      const totalHealth = poolModels.reduce((s, m) => s + m.health, 0)
      const avgHealth = poolModels.length ? Math.round(totalHealth / poolModels.length) : 0
      return {
        name: pool.name,
        color: pool.color,
        total: poolModels.length,
        active: activeCount,
        avgHealth,
        segments: poolModels.map(m => ({
          name: m.name.split('-')[0].substring(0, 8),
          health: m.health,
          active: m.isActive,
        })),
      }
    })
  }, [models])

  return (
    <Card className="relative overflow-hidden border-emerald-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Activity className="h-4 w-4 text-emerald-400" />
          Pool Health Overview
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-3">
        {poolHealthData.map((pool) => (
          <div key={pool.name}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: pool.color }} />
                <span className="text-xs font-medium">{pool.name}</span>
                <span className="text-[10px] text-muted-foreground">{pool.active}/{pool.total} active</span>
              </div>
              <span className={`text-[10px] font-bold tabular-nums ${
                pool.avgHealth >= 95 ? 'text-emerald-400' :
                pool.avgHealth >= 85 ? 'text-yellow-400' :
                'text-red-400'
              }`}>{pool.avgHealth}% avg</span>
            </div>
            {/* Horizontal stacked bar */}
            <div className="flex h-4 rounded-full overflow-hidden bg-muted/30">
              {pool.segments.map((seg, i) => (
                <div
                  key={`${pool.name}-${seg.name}-${i}`}
                  className={`h-full flex items-center justify-center text-[8px] font-bold transition-all duration-300 ${
                    !seg.active ? 'opacity-30' : ''
                  } ${i === 0 ? 'rounded-l-full' : ''} ${i === pool.segments.length - 1 ? 'rounded-r-full' : ''}`}
                  style={{
                    width: `${100 / pool.segments.length}%`,
                    backgroundColor: seg.active
                      ? (seg.health >= 95 ? '#34d399' : seg.health >= 85 ? '#facc15' : '#f87171')
                      : '#6b7280',
                    opacity: seg.active ? 0.7 : 0.2,
                  }}
                >
                  {seg.health}%
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// Rotation Analytics Component
function RotationAnalyticsCard() {
  return (
    <Card className="relative overflow-hidden border-blue-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <ArrowRightLeft className="h-4 w-4 text-blue-400" />
          Rotation Analytics
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="grid grid-cols-2 gap-4">
          {/* Most Rotated To */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp className="h-3 w-3 text-emerald-400" />
              <span className="text-[10px] font-medium uppercase tracking-wider text-emerald-400">Most Rotated To</span>
            </div>
            <div className="space-y-1.5">
              {rotationAnalytics.mostRotatedTo.map((item, i) => (
                <div key={item.model} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-600/10 text-[9px] font-bold text-emerald-400">
                    {i + 1}
                  </span>
                  <span className="text-xs truncate flex-1">{item.model.split('-')[0]}</span>
                  <span className="text-[10px] font-bold text-emerald-400 tabular-nums">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Most Rotated From */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingDown className="h-3 w-3 text-red-400" />
              <span className="text-[10px] font-medium uppercase tracking-wider text-red-400">Most Rotated From</span>
            </div>
            <div className="space-y-1.5">
              {rotationAnalytics.mostRotatedFrom.map((item, i) => (
                <div key={item.model} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-600/10 text-[9px] font-bold text-red-400">
                    {i + 1}
                  </span>
                  <span className="text-xs truncate flex-1">{item.model.split('-')[0]}</span>
                  <span className="text-[10px] font-bold text-red-400 tabular-nums">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Failover Log Component
function FailoverLogCard() {
  return (
    <Card className="relative overflow-hidden border-red-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-red-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            Failover Log
          </CardTitle>
          <Badge variant="outline" className="text-[9px]">{failoverLog.length} events</Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-3 pt-0">
        <div className="max-h-48 space-y-1.5 overflow-y-auto custom-scrollbar">
          {failoverLog.map((entry, i) => (
            <div
              key={`failover-${i}`}
              className="flex items-center gap-2 rounded-md bg-accent/20 px-2.5 py-2 text-xs hover:bg-accent/40 transition-colors"
            >
              <span className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">{entry.time}</span>
              <Badge className={`shrink-0 border-0 text-[8px] px-1.5 py-0 ${
                entry.severity === 'critical' ? 'bg-red-600/15 text-red-400' :
                entry.severity === 'warning' ? 'bg-yellow-600/15 text-yellow-400' :
                'bg-blue-600/15 text-blue-400'
              }`}>
                {entry.severity === 'critical' ? 'CRIT' : entry.severity === 'warning' ? 'WARN' : 'INFO'}
              </Badge>
              <span className="text-muted-foreground shrink-0">{entry.from.split('-')[0]}</span>
              <span className="text-emerald-400">→</span>
              <span className="truncate">{entry.to.split('-')[0]}</span>
              <span className="ml-auto text-[10px] text-muted-foreground/60 shrink-0 truncate max-w-[120px]">{entry.reason}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Model Performance Comparison Card with grouped bar chart
function ModelPerformanceComparison() {
  return (
    <Card className="relative overflow-hidden border-purple-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-purple-400" />
          Model Performance Comparison
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="h-[180px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={modelPerformanceData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} domain={[70, 100]} />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '11px',
                }}
                formatter={(value: number, name: string) => [`${value}%`, name]}
              />
              <Legend wrapperStyle={{ fontSize: '10px' }} iconType="circle" iconSize={8} />
              <Bar dataKey="health" name="Health" fill={COLORS.emerald} fillOpacity={0.7} radius={[2, 2, 0, 0]} />
              <Bar dataKey="successRate" name="Success" fill={COLORS.blue} fillOpacity={0.7} radius={[2, 2, 0, 0]} />
              <Bar dataKey="latency" name="Latency Score" fill={COLORS.orange} fillOpacity={0.7} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

export function GmrTab() {
  const { data: modelsData, loading, refetch } = useApiData<{ models: ModelData[] }>('/api/models', 15000)
  const baseModels = useMemo(() => modelsData?.models ?? [], [modelsData])
  const [healthPulse, setHealthPulse] = useState(0)

  // Track user overrides for active/inactive state per model ID (optimistic updates)
  // Empty = use base data; populated = user has toggled that model
  const [overrides, setOverrides] = useState<Record<string, boolean>>({})

  // Simulate health fluctuations on top of base data
  const models = useMemo(() => {
    return baseModels.map(m => {
      const isActive = m.id in overrides ? overrides[m.id] : m.isActive
      return {
        ...m,
        isActive,
        health: isActive
          ? Math.min(100, Math.max(80, m.health + (healthPulse % 5 === 0 ? 0 : (healthPulse % 2 === 0 ? 1 : -1))))
          : m.health,
      }
    })
  }, [baseModels, healthPulse, overrides])

  // Find which pool(s) a model belongs to
  const getModelPools = useCallback((modelName: string) => {
    return poolDefinitions.filter(pool => pool.modelNames.includes(modelName))
  }, [])

  // Check if a model is the last active one in any of its pools
  const isLastActiveInPool = useCallback((modelId: string) => {
    const model = models.find(m => m.id === modelId)
    if (!model) return false
    const pools = getModelPools(model.name)
    return pools.some(pool => {
      const poolModels = models.filter(m => pool.modelNames.includes(m.name))
      const activeInPool = poolModels.filter(m => m.isActive)
      return activeInPool.length === 1 && activeInPool[0].id === modelId
    })
  }, [models, getModelPools])

  // Handle model toggle
  const handleToggle = useCallback((modelId: string) => {
    const model = models.find(m => m.id === modelId)
    if (!model) return

    const newState = !model.isActive

    // If deactivating, check if it's the last active model in any pool
    if (!newState && isLastActiveInPool(modelId)) {
      toast.warning(`Cannot deactivate ${model.name} — it's the last active model in its pool`)
      return
    }

    // Optimistic update via override
    setOverrides(prev => ({ ...prev, [modelId]: newState }))
    toast.success(`Model ${model.name} ${newState ? 'activated' : 'deactivated'}`)
  }, [models, isLastActiveInPool])

  // Reset all models to their original isActive state (clear overrides)
  const handleReset = useCallback(() => {
    setOverrides({})
    toast.info('All models reset to default state')
  }, [])

  // Timer for health simulation pulse
  useEffect(() => {
    const interval = setInterval(() => {
      setHealthPulse(p => p + 1)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const activeModels = models.filter(m => m.isActive)
  const avgHealth = activeModels.length ? Math.round(activeModels.reduce((s, m) => s + m.health, 0) / activeModels.length) : 0
  const totalCalls = models.reduce((s, m) => s + m.totalCalls, 0)
  const freeActiveCount = models.filter(m => m.isActive && m.isFree).length

  return (
    <div className="space-y-6 p-6 grid-pattern">
      {/* Stats Row */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="relative overflow-hidden border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Models Online</p>
                <p className="mt-1 text-3xl font-bold text-emerald-400 tabular-nums">{activeModels.length}</p>
                <p className="text-[10px] text-muted-foreground">of {models.length} total</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Wifi className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Avg Health</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{avgHealth}%</p>
                <p className="text-[10px] text-muted-foreground">across active models</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Activity className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total API Calls</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{totalCalls.toLocaleString()}</p>
                <p className="text-[10px] text-muted-foreground">this session</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                <Zap className="h-5 w-5 text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">FREE_RESEARCH Pool</p>
                <p className="mt-1 text-3xl font-bold text-purple-400 tabular-nums">{freeActiveCount}</p>
                <p className="text-[10px] text-muted-foreground">free-tier models active</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-600/15 shadow-lg shadow-purple-600/10">
                <Gauge className="h-5 w-5 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Latency Chart + Model Performance Comparison */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Gauge className="h-4 w-4" /> Model Latency Over Time
              </CardTitle>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-400" /> qwen3-coder</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-blue-400" /> trinity</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-orange-400" /> gemma-fast</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <NexusBarChart
              data={latencyHistory}
              dataKey="qwen"
              nameKey="name"
              color={COLORS.emerald}
              height={100}
            />
          </CardContent>
        </Card>
        <ModelPerformanceComparison />
      </div>

      {/* Pool Health Overview + Rotation Analytics + Failover Log */}
      <div className="grid gap-4 lg:grid-cols-3">
        <PoolHealthOverview models={models} />
        <RotationAnalyticsCard />
        <FailoverLogCard />
      </div>

      <Tabs defaultValue="models" className="space-y-4">
        <TabsList>
          <TabsTrigger value="models">Model Registry</TabsTrigger>
          <TabsTrigger value="pools">Pool Status</TabsTrigger>
          <TabsTrigger value="rotation">Rotation Log</TabsTrigger>
        </TabsList>

        {/* Model Registry */}
        <TabsContent value="models">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-muted-foreground">{models.length} models registered</span>
            <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1.5" onClick={handleReset}>
              <RotateCcw className="h-3 w-3" /> Reset to Default
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {models.map((m) => (
              <Card key={m.id} className={`group relative overflow-hidden transition-all duration-300 ${m.isActive ? 'hover:border-emerald-600/20 hover:shadow-md hover:shadow-emerald-600/5' : 'opacity-50'}`}>
                {m.isActive && <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />}
                <CardContent className="relative p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">{m.name}</p>
                        {m.isFree && (
                          <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px] px-1">FREE</Badge>
                        )}
                        {!m.isActive && (
                          <Badge className="bg-red-600/15 text-red-400 border-0 text-[9px] px-1 animate-in fade-in duration-200">Disabled</Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground">{m.provider} · {m.domain}</p>
                    </div>
                    <div className="shrink-0">
                      {m.isActive ? (
                        <span className="relative flex h-4 w-4">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-30" />
                          <Wifi className="relative h-4 w-4 text-emerald-400" />
                        </span>
                      ) : (
                        <WifiOff className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-md bg-accent/30 py-1">
                      <p className="text-[9px] text-muted-foreground">Tier</p>
                      <p className="text-sm font-bold">{m.tier}</p>
                    </div>
                    <div className="rounded-md bg-accent/30 py-1">
                      <p className="text-[9px] text-muted-foreground">Health</p>
                      <p className={`text-sm font-bold ${m.health >= 95 ? 'text-emerald-400' : m.health >= 85 ? 'text-yellow-400' : 'text-red-400'}`}>{m.health}%</p>
                    </div>
                    <div className="rounded-md bg-accent/30 py-1">
                      <p className="text-[9px] text-muted-foreground">Latency</p>
                      <p className="text-sm font-bold">{m.latencyMs}ms</p>
                    </div>
                  </div>

                  <div className="mt-3">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>Success Rate</span>
                      <span className={m.successRate >= 98 ? 'text-emerald-400' : m.successRate >= 90 ? 'text-yellow-400' : 'text-red-400'}>{m.successRate}%</span>
                    </div>
                    <Progress value={m.successRate} className="mt-1 h-1.5" />
                  </div>

                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{m.totalCalls.toLocaleString()} calls</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-muted-foreground">Active</span>
                      <Switch
                        checked={m.isActive}
                        onCheckedChange={() => handleToggle(m.id)}
                        className="scale-75"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Pool Status - Enhanced with per-model mini sparklines */}
        <TabsContent value="pools">
          <div className="grid gap-4 md:grid-cols-2">
            {poolDefinitions.map((pool) => {
              const poolModels = models.filter(m => pool.modelNames.includes(m.name))
              const poolCalls = poolModels.reduce((s, m) => s + m.totalCalls, 0)
              const poolHealth = poolModels.length ? Math.round(poolModels.reduce((s, m) => s + m.health, 0) / poolModels.length) : 0
              return (
                <Card key={pool.name} className="relative overflow-hidden">
                  <div className={`absolute inset-0 bg-gradient-to-br ${pool.gradient} via-transparent to-transparent`} />
                  <CardHeader className="relative pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: pool.color }} />
                        {pool.name} Pool
                      </CardTitle>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="text-[10px]">Tier {pool.tierRange}</Badge>
                        <Badge className="text-[10px] border-0 bg-emerald-600/15 text-emerald-400">{poolHealth}% health</Badge>
                      </div>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{pool.desc}</p>
                  </CardHeader>
                  <CardContent className="relative p-4 pt-0">
                    <div className="space-y-2">
                      {poolModels.map((m) => (
                        <div key={m.id} className="flex items-center gap-2 rounded-md bg-accent/20 px-2.5 py-1.5">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${m.isActive ? 'bg-emerald-500' : 'bg-muted-foreground'}`} />
                            <span className="font-medium text-xs truncate">{m.name}</span>
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-muted-foreground shrink-0">
                            <span>{m.health}%</span>
                            <span>{m.latencyMs}ms</span>
                            <span className="text-emerald-400">{m.totalCalls}</span>
                          </div>
                          {/* Per-model mini sparkline */}
                          {modelSparklines[m.name] && (
                            <div className="w-16 shrink-0">
                              <MiniAreaChart
                                data={modelSparklines[m.name]}
                                dataKey="value"
                                color={m.health >= 95 ? COLORS.emerald : m.health >= 85 ? COLORS.yellow : COLORS.red}
                                height={20}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground">{poolCalls.toLocaleString()} total calls</span>
                      <NexusBarChart
                        data={poolModels.map(m => ({ name: m.name.split('-')[0].substring(0, 6), value: m.totalCalls }))}
                        height={40}
                      />
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </TabsContent>

        {/* Rotation Log */}
        <TabsContent value="rotation">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Hermes Router — Rotation Log</CardTitle>
                <Button variant="ghost" size="sm" className="h-7 text-[11px]" onClick={() => refetch()}>
                  <RefreshCw className="mr-1 h-3 w-3" /> Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="max-h-96 space-y-1.5 overflow-y-auto custom-scrollbar">
                {rotationLog.map((r, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg bg-accent/30 px-3 py-2 text-xs hover:bg-accent/50 transition-colors">
                    <span className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">{r.time}</span>
                    <span className="text-muted-foreground">{r.from === '-' ? '—' : r.from}</span>
                    <span className="text-emerald-400 font-medium">→</span>
                    <span className="font-medium">{r.to}</span>
                    <span className="ml-auto text-[10px] text-muted-foreground shrink-0">{r.reason}</span>
                    {r.tokens > 0 && <Badge variant="outline" className="text-[9px] shrink-0">{r.tokens}tok</Badge>}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
