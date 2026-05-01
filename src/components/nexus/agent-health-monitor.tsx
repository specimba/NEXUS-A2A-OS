'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { MiniAreaChart, COLORS } from '@/components/nexus/charts'
import { useApiData } from '@/hooks/use-api-data'
import {
  Heart,
  Activity,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Users,
  Clock,
  Shield,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import { toast } from 'sonner'

// ── Interfaces ───────────────────────────────────────────────────

interface AgentData {
  id: string
  name: string
  type: string
  status: string
  domain: string | null
  trustScore: number
  totalTokens: number
  tasksDone: number
  tasksFailed: number
  lastActive: string
  createdAt: string
  updatedAt: string
}

// ── Helper: get health color class based on trust score ──────────

function getHealthColor(trustScore: number): string {
  if (trustScore > 0.8) return 'text-emerald-500'
  if (trustScore >= 0.6) return 'text-yellow-500'
  return 'text-red-500'
}

function getHealthBgClass(trustScore: number): string {
  if (trustScore > 0.8) return 'bg-emerald-500'
  if (trustScore >= 0.6) return 'bg-yellow-500'
  return 'bg-red-500'
}

function getHealthStroke(trustScore: number): string {
  if (trustScore > 0.8) return COLORS.emerald
  if (trustScore >= 0.6) return COLORS.yellow
  return COLORS.red
}

function getStatusDotColor(status: string): string {
  if (status === 'busy') return 'bg-emerald-400'
  if (status === 'idle') return 'bg-yellow-400'
  return 'bg-red-400'
}

function getStatusLabel(status: string): string {
  if (status === 'busy') return 'online'
  if (status === 'idle') return 'idle'
  return 'error'
}

function getRoleBadgeClass(type: string): string {
  if (type === 'coordinator') return 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0'
  if (type === 'specialist') return 'bg-purple-600/15 text-purple-600 dark:text-purple-400 border-0'
  return 'bg-blue-600/15 text-blue-600 dark:text-blue-400 border-0'
}

// ── SVG Circular Health Ring ─────────────────────────────────────

function CircularHealthRing({ percentage }: { percentage: number }) {
  const [animatedPercentage, setAnimatedPercentage] = useState(0)
  const prevPercentageRef = useRef(0)

  useEffect(() => {
    const start = prevPercentageRef.current
    const end = percentage
    const duration = 800
    const startTime = performance.now()

    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setAnimatedPercentage(start + (end - start) * eased)
      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        prevPercentageRef.current = percentage
      }
    }

    requestAnimationFrame(animate)
  }, [percentage])

  const radius = 54
  const stroke = 8
  const normalizedRadius = radius - stroke / 2
  const circumference = normalizedRadius * 2 * Math.PI
  const strokeDashoffset = circumference - (animatedPercentage / 100) * circumference
  const strokeColor = getHealthStroke(percentage / 100)
  const textColor = getHealthColor(percentage / 100)

  return (
    <div className="relative flex items-center justify-center">
      <svg
        height={radius * 2}
        width={radius * 2}
        className="transform -rotate-90"
      >
        {/* Background ring */}
        <circle
          stroke="var(--muted)"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        {/* Foreground ring */}
        <circle
          stroke={strokeColor}
          fill="transparent"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          style={{ transition: 'stroke 0.3s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold tabular-nums ${textColor}`}>
          {Math.round(animatedPercentage)}%
        </span>
        <span className="text-[10px] text-muted-foreground">Fleet Health</span>
      </div>
    </div>
  )
}

// ── Metric Card ──────────────────────────────────────────────────

function MetricCard({
  icon: Icon,
  label,
  value,
  subValue,
  colorClass,
  bgClass,
  pulse,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  subValue?: string
  colorClass: string
  bgClass: string
  pulse?: boolean
}) {
  return (
    <div className="rounded-lg border bg-card/50 p-3 transition-colors hover:bg-accent/30">
      <div className="flex items-center gap-2 mb-1.5">
        <div className={`flex h-7 w-7 items-center justify-center rounded-md ${bgClass}`}>
          <Icon className={`h-3.5 w-3.5 ${colorClass}`} />
        </div>
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
        {pulse && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-lg font-bold tabular-nums ${colorClass}`}>{value}</span>
        {subValue && <span className="text-[10px] text-muted-foreground">{subValue}</span>}
      </div>
    </div>
  )
}

// ── Agent Health Bar ─────────────────────────────────────────────

function AgentHealthBar({ agent, sparklineData }: { agent: AgentData; sparklineData: { name: string; value: number }[] }) {
  const trustPercent = Math.round(agent.trustScore * 100)
  const errorRate = agent.tasksDone + agent.tasksFailed > 0
    ? ((agent.tasksFailed / (agent.tasksDone + agent.tasksFailed)) * 100).toFixed(1)
    : '0.0'

  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card/30 px-3 py-2.5 transition-colors hover:bg-accent/20">
      {/* Status dot */}
      <div className="flex flex-col items-center gap-1">
        <span className={`h-2 w-2 rounded-full ${getStatusDotColor(agent.status)} ${agent.status === 'error' ? 'animate-pulse' : ''}`} />
        <span className="text-[8px] text-muted-foreground capitalize">{getStatusLabel(agent.status)}</span>
      </div>

      {/* Agent info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium truncate">{agent.name}</span>
          <Badge className={`text-[9px] px-1.5 py-0 ${getRoleBadgeClass(agent.type)}`}>
            {agent.type}
          </Badge>
        </div>

        {/* Health bar */}
        <div className="flex items-center gap-2">
          <Progress
            value={trustPercent}
            className={`h-1.5 flex-1 ${
              agent.trustScore > 0.8 ? '[&>div]:bg-emerald-500' :
              agent.trustScore >= 0.6 ? '[&>div]:bg-yellow-500' :
              '[&>div]:bg-red-500'
            }`}
          />
          <span className={`text-xs font-medium tabular-nums w-10 text-right ${
            agent.trustScore > 0.8 ? 'text-emerald-600 dark:text-emerald-400' :
            agent.trustScore >= 0.6 ? 'text-yellow-600 dark:text-yellow-400' :
            'text-red-600 dark:text-red-400'
          }`}>
            {trustPercent}%
          </span>
        </div>

        {/* Bottom row: sparkline + error rate */}
        <div className="flex items-center justify-between mt-1.5 gap-2">
          <div className="flex-1 min-w-0 h-8">
            <MiniAreaChart
              data={sparklineData}
              dataKey="value"
              color={getHealthStroke(agent.trustScore)}
              height={32}
            />
          </div>
          <div className="flex items-center gap-1">
            {Number(errorRate) > 10 ? (
              <TrendingDown className="h-3 w-3 text-red-600 dark:text-red-400" />
            ) : (
              <TrendingUp className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            )}
            <span className="text-[10px] text-muted-foreground tabular-nums">{errorRate}% err</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Degradation Alert ────────────────────────────────────────────

function DegradationAlert({
  agent,
  healthPercent,
  onInvestigate,
}: {
  agent: AgentData
  healthPercent: number
  onInvestigate: (name: string) => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className="rounded-lg border border-red-600/30 bg-gradient-to-r from-red-600/8 via-red-600/3 to-transparent p-3"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-600/15">
          <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-red-600 dark:text-red-400">{agent.name}</span>
            <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">
              {healthPercent}% health
            </Badge>
          </div>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Agent health below 70% threshold — trust score degraded to {agent.trustScore.toFixed(2)}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0 h-7 text-[10px] border-red-600/30 text-red-600 dark:text-red-400 hover:bg-red-600/10 hover:border-red-600/40 px-2.5"
          onClick={() => onInvestigate(agent.name)}
        >
          Investigate
        </Button>
      </div>
    </motion.div>
  )
}

// ── Generate sparkline data per agent (deterministic based on agent id) ──

function generateSparkline(agent: AgentData): { name: string; value: number }[] {
  const base = Math.round(agent.trustScore * 100)
  // Deterministic pseudo-random based on agent name
  const seed = agent.name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)
  const points: { name: string; value: number }[] = []
  for (let i = 0; i < 5; i++) {
    const variation = Math.sin(seed * (i + 1) * 0.7) * 8
    points.push({ name: String(i + 1), value: Math.max(0, Math.min(100, base + variation)) })
  }
  return points
}

// ── Main Component ───────────────────────────────────────────────

export function AgentHealthMonitor() {
  const { data: agents, loading, error } = useApiData<AgentData[]>('/api/agents', 15000)

  // Deduplicate agents by name (API may return duplicates from multiple seeds)
  const uniqueAgents = useMemo(() => {
    if (!agents) return []
    const seen = new Set<string>()
    return agents.filter((agent) => {
      if (seen.has(agent.name)) return false
      seen.add(agent.name)
      return true
    })
  }, [agents])

  // Compute fleet health metrics
  const metrics = useMemo(() => {
    if (uniqueAgents.length === 0) {
      return {
        fleetHealth: 0,
        activeAgents: 0,
        avgTrust: 0,
        errorRate: 0,
        uptime: '0d 0h',
      }
    }

    const fleetHealth = Math.round(
      uniqueAgents.reduce((sum, a) => sum + a.trustScore * 100, 0) / uniqueAgents.length
    )
    const activeAgents = uniqueAgents.filter((a) => a.status === 'busy').length
    const avgTrust =
      uniqueAgents.reduce((sum, a) => sum + a.trustScore, 0) / uniqueAgents.length
    const totalTasks = uniqueAgents.reduce((sum, a) => sum + a.tasksDone + a.tasksFailed, 0)
    const totalFailed = uniqueAgents.reduce((sum, a) => sum + a.tasksFailed, 0)
    const errorRate = totalTasks > 0 ? ((totalFailed / totalTasks) * 100) : 0

    // Compute uptime from earliest agent creation
    const earliest = uniqueAgents.reduce((min, a) => {
      const d = new Date(a.createdAt).getTime()
      return d < min ? d : min
    }, Date.now())
    const uptimeMs = Date.now() - earliest
    const uptimeDays = Math.floor(uptimeMs / (1000 * 60 * 60 * 24))
    const uptimeHours = Math.floor((uptimeMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const uptime = `${uptimeDays}d ${uptimeHours}h`

    return { fleetHealth, activeAgents, avgTrust, errorRate, uptime }
  }, [uniqueAgents])

  // Degraded agents (trust score < 0.7)
  const degradedAgents = useMemo(
    () => uniqueAgents.filter((a) => a.trustScore < 0.7),
    [uniqueAgents]
  )

  // Sparkline data map
  const sparklineMap = useMemo(() => {
    const map = new Map<string, { name: string; value: number }[]>()
    uniqueAgents.forEach((agent) => {
      map.set(agent.id, generateSparkline(agent))
    })
    return map
  }, [uniqueAgents])

  const handleInvestigate = useCallback((agentName: string) => {
    toast.warning(`Investigating ${agentName}`, {
      description: `Opening diagnostic panel for degraded agent. Check trust history and recent errors.`,
      duration: 4000,
    })
  }, [])

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Heart className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Agent Health Monitor
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[9px]">
              {uniqueAgents.length} agents
            </Badge>
            {loading && (
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        {error ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground text-xs">
            <AlertTriangle className="h-4 w-4 mr-2 text-red-500" />
            Failed to load agent data
          </div>
        ) : (
          <div className="space-y-4">
            {/* Top section: Ring + Metrics */}
            <div className="flex flex-col sm:flex-row items-center gap-4">
              {/* Circular Health Ring */}
              <div className="shrink-0">
                <CircularHealthRing percentage={metrics.fleetHealth} />
              </div>

              {/* 2x2 Metric Grid */}
              <div className="grid grid-cols-2 gap-2 flex-1 w-full">
                <MetricCard
                  icon={Users}
                  label="Active"
                  value={String(metrics.activeAgents)}
                  subValue={`/ ${uniqueAgents.length}`}
                  colorClass="text-emerald-600 dark:text-emerald-400"
                  bgClass="bg-emerald-600/15"
                  pulse
                />
                <MetricCard
                  icon={Shield}
                  label="Avg Trust"
                  value={metrics.avgTrust.toFixed(2)}
                  subValue="Bayesian"
                  colorClass={
                    metrics.avgTrust > 0.8 ? 'text-emerald-600 dark:text-emerald-400' :
                    metrics.avgTrust >= 0.6 ? 'text-yellow-600 dark:text-yellow-400' :
                    'text-red-600 dark:text-red-400'
                  }
                  bgClass={
                    metrics.avgTrust > 0.8 ? 'bg-emerald-600/15' :
                    metrics.avgTrust >= 0.6 ? 'bg-yellow-600/15' :
                    'bg-red-600/15'
                  }
                />
                <MetricCard
                  icon={Activity}
                  label="Error Rate"
                  value={`${metrics.errorRate.toFixed(1)}%`}
                  subValue=""
                  colorClass={
                    metrics.errorRate < 5 ? 'text-emerald-600 dark:text-emerald-400' :
                    metrics.errorRate < 15 ? 'text-yellow-600 dark:text-yellow-400' :
                    'text-red-600 dark:text-red-400'
                  }
                  bgClass={
                    metrics.errorRate < 5 ? 'bg-emerald-600/15' :
                    metrics.errorRate < 15 ? 'bg-yellow-600/15' :
                    'bg-red-600/15'
                  }
                />
                <MetricCard
                  icon={Clock}
                  label="Uptime"
                  value={metrics.uptime}
                  subValue="continuous"
                  colorClass="text-blue-600 dark:text-blue-400"
                  bgClass="bg-blue-600/15"
                />
              </div>
            </div>

            {/* Degradation Alerts */}
            <AnimatePresence>
              {degradedAgents.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-2 overflow-hidden"
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <AlertTriangle className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
                    <span className="text-xs font-medium text-red-600 dark:text-red-400">
                      Degradation Alerts
                    </span>
                    <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">
                      {degradedAgents.length}
                    </Badge>
                  </div>
                  {degradedAgents.map((agent) => (
                    <DegradationAlert
                      key={agent.id}
                      agent={agent}
                      healthPercent={Math.round(agent.trustScore * 100)}
                      onInvestigate={handleInvestigate}
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Per-Agent Health Bars */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Activity className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-medium">Per-Agent Health</span>
              </div>
              <div className="max-h-72 space-y-2 overflow-y-auto custom-scrollbar pr-1">
                {uniqueAgents.length === 0 && !loading ? (
                  <div className="flex items-center justify-center py-6 text-muted-foreground text-xs">
                    No agents found
                  </div>
                ) : (
                  uniqueAgents.map((agent) => (
                    <AgentHealthBar
                      key={agent.id}
                      agent={agent}
                      sparklineData={sparklineMap.get(agent.id) ?? []}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
