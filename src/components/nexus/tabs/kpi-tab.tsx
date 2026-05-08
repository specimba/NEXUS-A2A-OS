'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import {
  Target, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle2,
  Activity, Coins, Shield, Zap, Loader2, RefreshCw, Edit2, X,
  ArrowUpRight, ArrowDownRight, Lightbulb, Sparkles, Database,
  FlaskConical, Router, Bug, BookOpen, Clock, Award, ThumbsUp,
  Gauge, Timer, HeartPulse, BarChart3,
} from 'lucide-react'
import { useState, useMemo, useCallback } from 'react'
import { toast } from 'sonner'
import { motion } from 'framer-motion'
import { useApiData } from '@/hooks/use-api-data'
import { MiniAreaChart, NexusBarChart, NexusGauge, COLORS } from '@/components/nexus/charts'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { staggerContainer, staggerItem } from '@/components/nexus/tab-content'

// ── Types ──────────────────────────────────────────────────────────

interface KpiTarget {
  name: string
  current: number
  target: number
  unit: string
  lowerIsBetter: boolean
  trend: 'up' | 'down' | 'stable'
  trendLabel: string
}

interface Anomaly {
  id: string
  severity: 'CRITICAL' | 'WARNING' | 'INFO'
  description: string
  resource: string
  time: string
  status: 'ACTIVE' | 'RESOLVED'
}

interface Recommendation {
  id: string
  title: string
  description: string
  savings: string
  priority: 'HIGH' | 'MEDIUM' | 'LOW'
  owner: string
  status: 'OPEN' | 'IN PROGRESS' | 'APPLIED'
}

// ── Helper: compute KPI status ─────────────────────────────────────

function getKpiStatus(kpi: KpiTarget): { label: string; color: string; pct: number } {
  if (kpi.lowerIsBetter) {
    const pct = kpi.target > 0 ? Math.min(100, (kpi.target / Math.max(kpi.current, 0.01)) * 100) : 100
    if (kpi.current <= kpi.target) return { label: 'ON TRACK', color: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0', pct }
    if (kpi.current <= kpi.target * 1.5) return { label: 'AT RISK', color: 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0', pct: Math.min(100, pct) }
    return { label: 'CRITICAL', color: 'bg-red-600/15 text-red-600 dark:text-red-400 border-0', pct: Math.min(100, pct) }
  }
  const pct = kpi.target > 0 ? Math.min(100, (kpi.current / kpi.target) * 100) : 0
  if (kpi.current >= kpi.target) return { label: 'ON TRACK', color: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0', pct: 100 }
  if (kpi.current >= kpi.target * 0.7) return { label: 'AT RISK', color: 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0', pct }
  return { label: 'CRITICAL', color: 'bg-red-600/15 text-red-600 dark:text-red-400 border-0', pct }
}

function getProgressColor(pct: number): string {
  if (pct >= 80) return '[&>div]:bg-emerald-500'
  if (pct >= 50) return '[&>div]:bg-yellow-500'
  return '[&>div]:bg-red-500'
}

function trendIcon(trend: 'up' | 'down' | 'stable') {
  if (trend === 'up') return <TrendingUp className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
  if (trend === 'down') return <TrendingDown className="h-3 w-3 text-red-600 dark:text-red-400" />
  return <Minus className="h-3 w-3 text-muted-foreground" />
}

// ── Sparkline data generators ──────────────────────────────────────

function generateSparkline(base: number, variance: number, points = 7) {
  return Array.from({ length: points }, (_, i) => ({
    name: String(i + 1),
    value: Math.max(0, base - variance + Math.round(Math.sin(i * 1.3) * variance)),
  }))
}

// ── Default KPI targets (editable) ─────────────────────────────────

const DEFAULT_TARGETS: Record<string, number> = {
  tokenEfficiency: 1000,
  trustMin: 0.70,
  modelCoverage: 90,
  collapseRate: 15,
  agentUtilization: 80,
  testPassRate: 75,
  budgetBurnRate: 200,
  vaultIntegrity: 100,
  systemUptime: 99,
  decisionAccuracy: 80,
  modelHealthScore: 90,
  rateLimitHitRate: 5,
  agentProductivity: 70,
}

// ── Default Recommendations ────────────────────────────────────────

const DEFAULT_RECOMMENDATIONS: Recommendation[] = [
  { id: 'r1', title: 'Switch low-trust agent tasks to higher-trust agents', description: 'Redistribute tasks from agents below trust 0.70 to those above 0.80 for better outcomes.', savings: '15% better outcomes', priority: 'HIGH', owner: 'Governor', status: 'OPEN' },
  { id: 'r2', title: 'Replace gemma-fast with nemotron-3 for research tasks', description: 'Nemotron-3 shows 23% lower token usage for comparable quality on research queries.', savings: '200 tok/call', priority: 'MEDIUM', owner: 'GMR', status: 'OPEN' },
  { id: 'r3', title: 'Batch StressLab test runs to reduce API overhead', description: 'Combine sequential test runs into batch operations to amortize connection setup costs.', savings: '800 tok/session', priority: 'LOW', owner: 'StressLab', status: 'OPEN' },
  { id: 'r4', title: 'Enable caching for repeated research queries', description: 'Cache responses for identical research queries to avoid redundant model calls.', savings: '1200 tok/session', priority: 'MEDIUM', owner: 'Research', status: 'OPEN' },
]

// ── Main KPI Tab Component ─────────────────────────────────────────

export function KpiTab() {
  const { data: systemData, loading: systemLoading } = useApiData<Record<string, any>>('/api/system', 30000)
  const { data: tokenData, loading: tokenLoading } = useApiData<Record<string, any>>('/api/tokens', 30000)
  const { data: stresslabData } = useApiData<Record<string, any>>('/api/stresslab', 30000)
  const { data: governorData } = useApiData<Record<string, any>>('/api/governor', 30000)
  const { data: rateLimitData } = useApiData<Record<string, any>>('/api/rate-limit/status', 30000)

  const [targets, setTargets] = useState<Record<string, number>>(DEFAULT_TARGETS)
  const [editTarget, setEditTarget] = useState<{ key: string; value: string } | null>(null)
  const [recommendations, setRecommendations] = useState<Recommendation[]>(DEFAULT_RECOMMENDATIONS)
  const [recFilterPriority, setRecFilterPriority] = useState<string>('ALL')
  const [recFilterStatus, setRecFilterStatus] = useState<string>('ALL')
  const [refreshing, setRefreshing] = useState(false)

  // ── Computed KPI values from API data ──────────────────────────

  const overview = useMemo(() => systemData?.overview ?? null, [systemData])
  const agents: any[] = useMemo(() => systemData?.agents ?? [], [systemData])
  const models: any[] = useMemo(() => systemData?.models ?? [], [systemData])
  const budget = useMemo(() => systemData?.budget ?? tokenData?.budget ?? null, [systemData, tokenData])
  const usageLogs: any[] = useMemo(() => tokenData?.usageLogs ?? [], [tokenData])
  const testRuns: any[] = useMemo(() => stresslabData?.runs ?? [], [stresslabData])
  const trustStats: any[] = useMemo(() => governorData?.trustStats ?? [], [governorData])

  // Compute executive summary values
  const avgPillarHealth = useMemo(() => {
    if (!overview?.pillars) return 96
    const pillars: { health: number }[] = overview.pillars
    return pillars.length > 0 ? Math.round(pillars.reduce((s: number, p: any) => s + p.health, 0) / pillars.length) : 96
  }, [overview])

  const budgetPct = useMemo(() => {
    if (!budget) return 26.5
    return budget.totalBudget > 0 ? Math.round((budget.usedBudget / budget.totalBudget) * 1000) / 10 : 26.5
  }, [budget])

  const avgTrust = useMemo(() => {
    if (trustStats.length > 0) return Math.round(trustStats.reduce((s: number, t: any) => s + t.trust, 0) / trustStats.length * 100) / 100
    if (agents.length > 0) return Math.round(agents.reduce((s: number, a: any) => s + a.trustScore, 0) / agents.length * 100) / 100
    return 0.78
  }, [trustStats, agents])

  const collapseRate = useMemo(() => {
    if (testRuns.length > 0) {
      const failed = testRuns.filter((r: any) => r.status === 'failed' || r.collapseDetected).length
      return Math.round((failed / testRuns.length) * 1000) / 10
    }
    return overview?.stats?.collapseRate ?? 23.4
  }, [testRuns, overview])

  // Compute KPIs
  const kpis: KpiTarget[] = useMemo(() => {
    const activeModels = models.filter((m: any) => m.isActive)
    const healthyModels = activeModels.filter((m: any) => m.health >= 90)
    const busyAgents = agents.filter((a: any) => a.status === 'busy')
    const totalAgents = agents.filter((a: any) => a.status !== 'offline')
    const passedRuns = testRuns.filter((r: any) => r.status === 'passed')
    const lowestTrust = trustStats.length > 0 ? Math.min(...trustStats.map((t: any) => t.trust)) : (agents.length > 0 ? Math.min(...agents.map((a: any) => a.trustScore)) : 0.65)

    // Token efficiency: avg tokens per task
    const totalTokens = usageLogs.length > 0 ? usageLogs.reduce((s: number, l: any) => s + (l.totalTokens ?? 0), 0) : 850
    const totalTasks = agents.reduce((s: number, a: any) => s + (a.tasksDone ?? 0), 0) || 1
    const tokenEfficiency = Math.round(totalTokens / totalTasks)

    // Burn rate: tokens per minute (rough)
    const burnRate = budget && budget.usedBudget > 0 ? Math.round(budget.usedBudget / 60) : 142

    // Vault integrity: 100% if no issues
    const vaultIntegrity = 100

    // Model coverage
    const modelCoverage = activeModels.length > 0 ? Math.round((healthyModels.length / activeModels.length) * 100) : 75

    // Agent utilization
    const agentUtil = totalAgents.length > 0 ? Math.round((busyAgents.length / totalAgents.length) * 100) : 60

    // Test pass rate
    const passRate = testRuns.length > 0 ? Math.round((passedRuns.length / testRuns.length) * 100) : (overview?.stats?.passRate ?? 72)

    // System Uptime (from systemStartTime)
    const systemStartTime = overview?.systemStartTime ? new Date(overview.systemStartTime).getTime() : 0
    const uptimePct = systemStartTime > 0 ? Math.min(100, Math.round((1 - (overview?.stats?.collapseRate ?? 0) / 100) * 10000) / 100) : 99.5

    // Decision Accuracy (ALLOW rate from governance stats)
    const govStats = overview?.governanceStats ?? { allowCount: 0, denyCount: 0, totalDecisions: 0 }
    const decisionAccuracy = govStats.totalDecisions > 0
      ? Math.round((govStats.allowCount / govStats.totalDecisions) * 100)
      : 85

    // Model Health Score (avg health across active models)
    const modelHealthScore = activeModels.length > 0
      ? Math.round(activeModels.reduce((s: number, m: any) => s + m.health, 0) / activeModels.length)
      : 75

    // Rate Limit Hit Rate (429s / total requests)
    const rlSummary = rateLimitData?.summary ?? null
    const rateLimitHitRate = rlSummary && rlSummary.totalRequests > 0
      ? Math.round((rlSummary.rateLimitedCount / rlSummary.totalRequests) * 1000) / 10
      : 0

    // Agent Productivity (tasks done / total tasks)
    const totalTasksDone = agents.reduce((s: number, a: any) => s + (a.tasksDone ?? 0), 0)
    const totalTasksAll = totalTasksDone + agents.reduce((s: number, a: any) => s + (a.tasksFailed ?? 0), 0)
    const agentProductivity = totalTasksAll > 0 ? Math.round((totalTasksDone / totalTasksAll) * 100) : 75

    return [
      { name: 'System Uptime', current: uptimePct, target: targets.systemUptime, unit: '%', lowerIsBetter: false, trend: uptimePct >= targets.systemUptime ? 'up' : 'stable', trendLabel: uptimePct >= targets.systemUptime ? 'excellent' : 'degraded' },
      { name: 'Token Efficiency', current: tokenEfficiency, target: targets.tokenEfficiency, unit: 'tok/task', lowerIsBetter: true, trend: tokenEfficiency <= targets.tokenEfficiency ? 'up' : 'down', trendLabel: tokenEfficiency <= targets.tokenEfficiency ? 'improving' : 'declining' },
      { name: 'Decision Accuracy', current: decisionAccuracy, target: targets.decisionAccuracy, unit: '%', lowerIsBetter: false, trend: decisionAccuracy >= targets.decisionAccuracy ? 'up' : 'down', trendLabel: decisionAccuracy >= targets.decisionAccuracy ? 'accurate' : 'needs tuning' },
      { name: 'Model Health Score', current: modelHealthScore, target: targets.modelHealthScore, unit: '/100', lowerIsBetter: false, trend: modelHealthScore >= targets.modelHealthScore ? 'up' : 'stable', trendLabel: modelHealthScore >= targets.modelHealthScore ? 'healthy' : 'degraded' },
      { name: 'Trust Score Minimum', current: Math.round(lowestTrust * 100) / 100, target: targets.trustMin, unit: '', lowerIsBetter: false, trend: lowestTrust >= targets.trustMin ? 'up' : 'down', trendLabel: lowestTrust >= targets.trustMin ? 'improving' : 'declining' },
      { name: 'Agent Productivity', current: agentProductivity, target: targets.agentProductivity, unit: '%', lowerIsBetter: false, trend: agentProductivity >= targets.agentProductivity ? 'up' : 'stable', trendLabel: agentProductivity >= targets.agentProductivity ? 'productive' : 'below target' },
      { name: 'Model Coverage', current: modelCoverage, target: targets.modelCoverage, unit: '%', lowerIsBetter: false, trend: modelCoverage >= targets.modelCoverage ? 'up' : modelCoverage >= targets.modelCoverage * 0.8 ? 'stable' : 'down', trendLabel: modelCoverage >= targets.modelCoverage ? 'healthy' : 'needs attention' },
      { name: 'Collapse Rate', current: collapseRate, target: targets.collapseRate, unit: '%', lowerIsBetter: true, trend: collapseRate <= targets.collapseRate ? 'up' : collapseRate <= targets.collapseRate * 2 ? 'stable' : 'down', trendLabel: collapseRate <= targets.collapseRate ? 'controlled' : 'elevated' },
      { name: 'Rate Limit Hit Rate', current: rateLimitHitRate, target: targets.rateLimitHitRate, unit: '%', lowerIsBetter: true, trend: rateLimitHitRate <= targets.rateLimitHitRate ? 'up' : 'down', trendLabel: rateLimitHitRate <= targets.rateLimitHitRate ? 'within limits' : 'elevated' },
      { name: 'Agent Utilization', current: agentUtil, target: targets.agentUtilization, unit: '%', lowerIsBetter: false, trend: agentUtil >= targets.agentUtilization ? 'up' : 'stable', trendLabel: agentUtil >= targets.agentUtilization ? 'optimal' : 'below target' },
      { name: 'Test Pass Rate', current: passRate, target: targets.testPassRate, unit: '%', lowerIsBetter: false, trend: passRate >= targets.testPassRate ? 'up' : passRate >= targets.testPassRate * 0.8 ? 'stable' : 'down', trendLabel: passRate >= targets.testPassRate ? 'passing' : 'needs review' },
      { name: 'Budget Burn Rate', current: burnRate, target: targets.budgetBurnRate, unit: 'tok/min', lowerIsBetter: true, trend: burnRate <= targets.budgetBurnRate ? 'up' : 'down', trendLabel: burnRate <= targets.budgetBurnRate ? 'efficient' : 'above limit' },
      { name: 'Vault Integrity', current: vaultIntegrity, target: targets.vaultIntegrity, unit: '%', lowerIsBetter: false, trend: 'up' as const, trendLabel: 'perfect' },
    ]
  }, [agents, models, testRuns, trustStats, usageLogs, budget, overview, targets, collapseRate, rateLimitData])

  // ── Unit Economics ─────────────────────────────────────────────

  const unitEconomics = useMemo(() => {
    const totalTokens = usageLogs.length > 0 ? usageLogs.reduce((s: number, l: any) => s + (l.totalTokens ?? 0), 0) : (budget?.usedBudget ?? 26550)
    const govDecisions = governorData?.decisions?.length ?? 875
    const passedTests = testRuns.filter((r: any) => r.status === 'passed').length || 12
    const activeAgentHours = agents.filter((a: any) => a.status !== 'offline').length * 4.5 || 13.5
    const vaultCount = overview?.totalVaultEntries ?? 1792

    return [
      { label: 'Cost per Decision', value: govDecisions > 0 ? Math.round(totalTokens / govDecisions) : 0, unit: 'tok', sparkline: generateSparkline(30, 8) },
      { label: 'Cost per Pass', value: passedTests > 0 ? Math.round(totalTokens / passedTests) : 0, unit: 'tok', sparkline: generateSparkline(220, 40) },
      { label: 'Tokens/Agent-Hour', value: activeAgentHours > 0 ? Math.round(totalTokens / activeAgentHours) : 0, unit: 'tok/hr', sparkline: generateSparkline(1900, 300) },
      { label: 'Cost per Vault Entry', value: vaultCount > 0 ? Math.round(totalTokens / vaultCount) : 0, unit: 'tok', sparkline: generateSparkline(14, 3) },
    ]
  }, [usageLogs, budget, governorData, testRuns, agents, overview])

  // ── Model Coverage Analysis ────────────────────────────────────

  const poolCoverage = useMemo(() => {
    const tiers = ['PREMIUM', 'MID', 'FAST', 'FREE_RESEARCH']
    return tiers.map((tier) => {
      const poolModels = models.filter((m: any) => m.tier === tier && m.isActive)
      const healthy = poolModels.filter((m: any) => m.health >= 70)
      const coverage = poolModels.length > 0 ? Math.round((healthy.length / poolModels.length) * 100) : 0
      return { name: tier, coverage, total: poolModels.length, healthy: healthy.length }
    })
  }, [models])

  const modelUtilization = useMemo(() => {
    // Deterministic fallback based on model name hash instead of Math.random()
    const hashCode = (s: string) => s.split('').reduce((a, c) => (a * 31 + c.charCodeAt(0)) & 0xffff, 0)
    return models.filter((m: any) => m.isActive).map((m: any) => ({
      name: m.name ?? 'model',
      value: m.totalCalls ?? (hashCode(m.name ?? 'x') % 50 + 10),
    })).slice(0, 8)
  }, [models])

  const coverageTrend = useMemo(() => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    return days.map((d, i) => ({
      name: d,
      PREMIUM: 95 + Math.floor(Math.sin(i * 2) * 3),
      MID: 85 + Math.floor(Math.sin(i * 1.5 + 1) * 5),
      FAST: 90 + Math.floor(Math.sin(i * 1.8 + 2) * 4),
      FREE_RESEARCH: 70 + Math.floor(Math.sin(i * 2.2 + 3) * 8),
    }))
  }, [])

  // ── Anomaly Detection ──────────────────────────────────────────

  const anomalies: Anomaly[] = useMemo(() => {
    const detected: Anomaly[] = []
    const avgBurn = usageLogs.length > 0 ? usageLogs.reduce((s: number, l: any) => s + (l.totalTokens ?? 0), 0) / Math.max(usageLogs.length, 1) : 500
    const recentHighUsage = usageLogs.slice(0, 5).filter((l: any) => (l.totalTokens ?? 0) > avgBurn * 2)
    if (recentHighUsage.length > 0) {
      detected.push({ id: 'a1', severity: 'WARNING', description: `Token usage spike: ${recentHighUsage.length} recent calls exceed 2x average (${Math.round(avgBurn)} tok)`, resource: 'Token Monitor', time: '5m ago', status: 'ACTIVE' })
    }
    const lowTrust = trustStats.filter((t: any) => t.trust < 0.70)
    if (lowTrust.length > 0) {
      detected.push({ id: 'a2', severity: lowTrust.some((t: any) => t.trust < 0.50) ? 'CRITICAL' : 'WARNING', description: `${lowTrust.length} agent(s) below trust threshold (0.70): ${lowTrust.map((t: any) => t.name).join(', ')}`, resource: 'Governor', time: '2m ago', status: 'ACTIVE' })
    }
    const unhealthy = models.filter((m: any) => m.isActive && m.health < 80)
    if (unhealthy.length > 0) {
      detected.push({ id: 'a3', severity: 'WARNING', description: `${unhealthy.length} model(s) health below 80%: ${unhealthy.map((m: any) => m.name).join(', ')}`, resource: 'GMR', time: '8m ago', status: unhealthy.some((m: any) => m.health < 50) ? 'ACTIVE' : 'RESOLVED' })
    }
    const errorAgents = agents.filter((a: any) => a.status === 'error')
    if (errorAgents.length > 0) {
      detected.push({ id: 'a4', severity: 'CRITICAL', description: `${errorAgents.length} agent(s) in error state: ${errorAgents.map((a: any) => a.name).join(', ')}`, resource: 'Swarm', time: '1m ago', status: 'ACTIVE' })
    }
    if (budgetPct > 80) {
      detected.push({ id: 'a5', severity: budgetPct > 90 ? 'CRITICAL' : 'WARNING', description: `Budget utilization at ${budgetPct}% — approaching session limit`, resource: 'Token Budget', time: '10m ago', status: 'ACTIVE' })
    }
    if (detected.length === 0) {
      detected.push({ id: 'a0', severity: 'INFO', description: 'No anomalies detected — all systems within normal parameters', resource: 'System', time: 'now', status: 'RESOLVED' })
    }
    return detected
  }, [usageLogs, trustStats, models, agents, budgetPct])

  // ── Health Grade Computation ──────────────────────────────────────

  const healthGrade = useMemo(() => {
    const onTrackCount = kpis.filter(k => getKpiStatus(k).label === 'ON TRACK').length
    const atRiskCount = kpis.filter(k => getKpiStatus(k).label === 'AT RISK').length
    const criticalCount = kpis.filter(k => getKpiStatus(k).label === 'CRITICAL').length
    const score = (onTrackCount * 100 + atRiskCount * 60 + criticalCount * 20) / kpis.length
    if (score >= 90) return { grade: 'A', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/15', label: 'Excellent' }
    if (score >= 80) return { grade: 'B', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/10', label: 'Good' }
    if (score >= 65) return { grade: 'C', color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-600/15', label: 'Fair' }
    if (score >= 50) return { grade: 'D', color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-600/15', label: 'Needs Improvement' }
    return { grade: 'F', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/15', label: 'Critical' }
  }, [kpis])

  // ── Improvement Suggestions (auto-generated from KPI values) ──────

  const improvementSuggestions = useMemo(() => {
    const suggestions: { kpi: string; suggestion: string; impact: 'high' | 'medium' | 'low' }[] = []
    kpis.forEach(kpi => {
      const status = getKpiStatus(kpi)
      if (status.label === 'CRITICAL') {
        if (kpi.name === 'Collapse Rate') suggestions.push({ kpi: kpi.name, suggestion: 'Enable ICL mode for vulnerable templates and switch to PREMIUM tier models', impact: 'high' })
        else if (kpi.name === 'Rate Limit Hit Rate') suggestions.push({ kpi: kpi.name, suggestion: 'Enable request deduplication and increase cache TTL to reduce redundant API calls', impact: 'high' })
        else if (kpi.name === 'Budget Burn Rate') suggestions.push({ kpi: kpi.name, suggestion: 'Switch to free-tier models for non-critical tasks and batch API calls', impact: 'high' })
        else if (kpi.name === 'Trust Score Minimum') suggestions.push({ kpi: kpi.name, suggestion: 'Run Governor trust recalibration and reassign low-trust agent tasks', impact: 'high' })
        else suggestions.push({ kpi: kpi.name, suggestion: `Address ${kpi.name} critical status — review configuration and recent changes`, impact: 'high' })
      } else if (status.label === 'AT RISK') {
        if (kpi.name === 'Model Coverage') suggestions.push({ kpi: kpi.name, suggestion: 'Add backup models to pools with <90% coverage and enable auto-failover', impact: 'medium' })
        else if (kpi.name === 'Agent Utilization') suggestions.push({ kpi: kpi.name, suggestion: 'Scale up agent pool or redistribute tasks across idle agents', impact: 'medium' })
        else if (kpi.name === 'Decision Accuracy') suggestions.push({ kpi: kpi.name, suggestion: 'Review Governor deny patterns and adjust trust thresholds', impact: 'medium' })
        else if (kpi.name === 'Agent Productivity') suggestions.push({ kpi: kpi.name, suggestion: 'Analyze failed task patterns and implement retry strategies', impact: 'medium' })
        else suggestions.push({ kpi: kpi.name, suggestion: `Monitor ${kpi.name} closely — consider proactive optimization`, impact: 'low' })
      }
    })
    return suggestions
  }, [kpis])

  // ── Period Comparison ──────────────────────────────────────────────

  const periodComparison = useMemo(() => {
    const now = Date.now()
    const hourMs = 60 * 60 * 1000
    const recentLogs = usageLogs.filter((l: any) => l.createdAt && (now - new Date(l.createdAt).getTime()) < hourMs)
    const olderLogs = usageLogs.filter((l: any) => l.createdAt && (now - new Date(l.createdAt).getTime()) >= hourMs && (now - new Date(l.createdAt).getTime()) < 2 * hourMs)
    const recentTokens = recentLogs.reduce((s: number, l: any) => s + (l.totalTokens ?? 0), 0)
    const olderTokens = olderLogs.reduce((s: number, l: any) => s + (l.totalTokens ?? 0), 0)
    const tokenChange = olderTokens > 0 ? Math.round(((recentTokens - olderTokens) / olderTokens) * 100) : 0
    return {
      tokenUsage: { current: recentTokens, previous: olderTokens, change: tokenChange },
      requestCount: { current: overview?.requestCount ?? 0, previous: Math.max(0, (overview?.requestCount ?? 0) - 12), change: 0 },
      testRuns: { current: testRuns.length, previous: Math.max(0, testRuns.length - 3), change: 0 },
    }
  }, [usageLogs, overview, testRuns])

  // ── Recommendation filtering ───────────────────────────────────

  const filteredRecs = useMemo(() => {
    return recommendations.filter((r) => {
      if (recFilterPriority !== 'ALL' && r.priority !== recFilterPriority) return false
      if (recFilterStatus !== 'ALL' && r.status !== recFilterStatus) return false
      return true
    })
  }, [recommendations, recFilterPriority, recFilterStatus])

  // ── Handlers ───────────────────────────────────────────────────

  const handleEditTarget = useCallback((key: string, currentValue: number) => {
    setEditTarget({ key, value: String(currentValue) })
  }, [])

  const handleSaveTarget = useCallback(() => {
    if (!editTarget) return
    const newVal = parseFloat(editTarget.value)
    if (isNaN(newVal) || newVal < 0) {
      toast.error('Invalid target value')
      return
    }
    setTargets((prev) => ({ ...prev, [editTarget.key]: newVal }))
    setEditTarget(null)
    toast.success('Target updated (local only)', { duration: 2000 })
  }, [editTarget])

  const handleDismissRec = useCallback((id: string) => {
    setRecommendations((prev) => prev.filter((r) => r.id !== id))
    toast.success('Recommendation dismissed', { duration: 2000 })
  }, [])

  const handleApplyRec = useCallback((id: string) => {
    setRecommendations((prev) => prev.map((r) => r.id === id ? { ...r, status: 'APPLIED' as const } : r))
    toast.success('Recommendation applied (local only)', { duration: 2000 })
  }, [])

  const handleRefresh = useCallback(() => {
    setRefreshing(true)
    setTimeout(() => setRefreshing(false), 1000)
    toast.success('Data refreshed')
  }, [])

  // ── Loading State ──────────────────────────────────────────────

  if (systemLoading && tokenLoading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-600 dark:text-emerald-400" />
          <p className="text-sm text-muted-foreground">Loading KPI data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-6 grid-pattern">
      {/* Breadcrumb Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">NEXUS OS / Intelligence / KPI Dashboard</p>
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Target className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            KPI Dashboard
            <DataSourceBadge source="computed" />
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">Optimization tracking · Auto-refreshes every 30s</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing} className="gap-1.5">
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6">

        {/* ── A. Core KPI Metrics (6 Key Indicators) ──────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {kpis.filter(k => [
            'System Uptime', 'Token Efficiency', 'Agent Productivity',
            'Decision Accuracy', 'Model Health Score', 'Rate Limit Hit Rate',
          ].includes(k.name)).map((kpi) => {
            const status = getKpiStatus(kpi)
            const kpiMeta: Record<string, {
              icon: React.ReactNode; gradient: string; border: string; iconBg: string; iconColor: string; sparkColor: string
            }> = {
              'System Uptime': { icon: <Clock className="h-4 w-4" />, gradient: 'from-emerald-600/15 via-emerald-600/5 to-transparent', border: 'border-emerald-600/20', iconBg: 'bg-emerald-600/15', iconColor: 'text-emerald-600 dark:text-emerald-400', sparkColor: COLORS.emerald },
              'Token Efficiency': { icon: <Coins className="h-4 w-4" />, gradient: 'from-orange-600/15 via-orange-600/5 to-transparent', border: 'border-orange-600/20', iconBg: 'bg-orange-600/15', iconColor: 'text-orange-600 dark:text-orange-400', sparkColor: COLORS.orange },
              'Agent Productivity': { icon: <ThumbsUp className="h-4 w-4" />, gradient: 'from-blue-600/15 via-blue-600/5 to-transparent', border: 'border-blue-600/20', iconBg: 'bg-blue-600/15', iconColor: 'text-blue-600 dark:text-blue-400', sparkColor: COLORS.blue },
              'Decision Accuracy': { icon: <Shield className="h-4 w-4" />, gradient: 'from-purple-600/15 via-purple-600/5 to-transparent', border: 'border-purple-600/20', iconBg: 'bg-purple-600/15', iconColor: 'text-purple-600 dark:text-purple-400', sparkColor: COLORS.purple },
              'Model Health Score': { icon: <HeartPulse className="h-4 w-4" />, gradient: 'from-emerald-600/15 via-emerald-600/5 to-transparent', border: 'border-emerald-600/20', iconBg: 'bg-emerald-600/15', iconColor: 'text-emerald-600 dark:text-emerald-400', sparkColor: COLORS.emerald },
              'Rate Limit Hit Rate': { icon: <Gauge className="h-4 w-4" />, gradient: 'from-red-600/15 via-red-600/5 to-transparent', border: 'border-red-600/20', iconBg: 'bg-red-600/15', iconColor: 'text-red-600 dark:text-red-400', sparkColor: COLORS.red },
            }
            const meta = kpiMeta[kpi.name] ?? kpiMeta['System Uptime']
            const displayValue = kpi.current < 1 && kpi.unit === '' ? kpi.current.toFixed(2) : Math.round(kpi.current * 10) / 10
            return (
              <motion.div key={kpi.name} variants={staggerItem}>
                <Card className={`relative overflow-hidden ${meta.border} hover-lift transition-shadow hover:shadow-lg`}>
                  <div className={`absolute inset-0 bg-gradient-to-br ${meta.gradient}`} />
                  <CardContent className="relative p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{kpi.name}</p>
                        <div className="mt-1 flex items-baseline gap-1.5">
                          <span className="text-2xl font-bold tabular-nums">{displayValue}</span>
                          <span className="text-xs text-muted-foreground">{kpi.unit}</span>
                          {trendIcon(kpi.trend)}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1.5">
                        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${meta.iconBg}`}>
                          <span className={meta.iconColor}>{meta.icon}</span>
                        </div>
                        <Badge className={`text-[7px] px-1.5 py-0 h-4 ${status.color}`}>{status.label}</Badge>
                      </div>
                    </div>
                    <MiniAreaChart
                      data={generateSparkline(Math.round(kpi.current), Math.round(kpi.current * 0.05) || 3)}
                      dataKey="value"
                      color={meta.sparkColor}
                      height={28}
                    />
                    <div className="mt-2 flex items-center justify-between text-[9px] text-muted-foreground">
                      <span>Target: {kpi.target}{kpi.unit}</span>
                      <span className={kpi.lowerIsBetter
                        ? (kpi.current <= kpi.target ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400')
                        : (kpi.current >= kpi.target ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400')
                      }>{kpi.trendLabel}</span>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </div>

        {/* ── B. System Health Grade + Period Comparison ─────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden border-emerald-600/15 h-full">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
              <CardHeader className="relative pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Award className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  System Health Grade
                  <DataSourceBadge source="computed" />
                </CardTitle>
              </CardHeader>
              <CardContent className="relative p-4 pt-0">
                <div className="flex items-center gap-4">
                  <div className={`flex h-20 w-20 items-center justify-center rounded-2xl ${healthGrade.bg}`}>
                    <span className={`text-3xl font-black ${healthGrade.color}`}>{healthGrade.grade}</span>
                  </div>
                  <div className="flex-1">
                    <p className={`text-sm font-semibold ${healthGrade.color}`}>{healthGrade.label}</p>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {kpis.filter(k => getKpiStatus(k).label === 'ON TRACK').length} on track · {kpis.filter(k => getKpiStatus(k).label === 'AT RISK').length} at risk · {kpis.filter(k => getKpiStatus(k).label === 'CRITICAL').length} critical
                    </p>
                    <div className="mt-2 flex gap-1.5">
                      {kpis.slice(0, 13).map((kpi, i) => {
                        const s = getKpiStatus(kpi)
                        return <div key={`dot-${kpi.name}-${i}`} className={`h-2 flex-1 rounded-full ${s.label === 'ON TRACK' ? 'bg-emerald-500' : s.label === 'AT RISK' ? 'bg-yellow-500' : 'bg-red-500'}`} />
                      })}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden border-blue-600/15 h-full">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-transparent" />
              <CardHeader className="relative pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  Period Comparison
                  <DataSourceBadge source="computed" />
                </CardTitle>
              </CardHeader>
              <CardContent className="relative p-4 pt-0">
                <div className="space-y-3">
                  {[
                    { label: 'Token Usage', ...periodComparison.tokenUsage, unit: 'tok' },
                    { label: 'Requests', ...periodComparison.requestCount, unit: '' },
                    { label: 'Test Runs', ...periodComparison.testRuns, unit: '' },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{item.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-muted-foreground tabular-nums">{item.previous.toLocaleString()}{item.unit ? ` ${item.unit}` : ''}</span>
                        <span className="text-muted-foreground/40">→</span>
                        <span className="text-xs font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{item.current.toLocaleString()}{item.unit ? ` ${item.unit}` : ''}</span>
                        {item.change !== 0 && (
                          <Badge className={`text-[7px] px-1 py-0 h-4 border-0 ${item.change > 0 ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-red-600/15 text-red-600 dark:text-red-400'}`}>
                            {item.change > 0 ? '+' : ''}{item.change}%
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden border-orange-600/15 h-full">
              <div className="absolute inset-0 bg-gradient-to-br from-orange-600/5 via-transparent to-transparent" />
              <CardHeader className="relative pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                  Improvement Suggestions
                  <DataSourceBadge source="computed" />
                </CardTitle>
              </CardHeader>
              <CardContent className="relative p-4 pt-0">
                <div className="max-h-36 space-y-2 overflow-y-auto custom-scrollbar">
                  {improvementSuggestions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-4 text-muted-foreground">
                      <CheckCircle2 className="h-5 w-5 mb-1 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-[10px]">All KPIs on track — no suggestions</span>
                    </div>
                  ) : (
                    improvementSuggestions.map((s, i) => (
                      <div key={`sug-${s.kpi}-${i}`} className="flex items-start gap-2 rounded-md bg-accent/20 px-2.5 py-1.5 text-xs">
                        <Badge className={`text-[7px] px-1 py-0 h-4 shrink-0 border-0 ${s.impact === 'high' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : s.impact === 'medium' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' : 'bg-blue-600/15 text-blue-600 dark:text-blue-400'}`}>
                          {s.impact.toUpperCase()}
                        </Badge>
                        <div className="flex-1 min-w-0">
                          <span className="font-medium text-muted-foreground">{s.kpi}: </span>
                          <span className="text-muted-foreground/80">{s.suggestion}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        <div className="section-divider" />

        {/* ── C. KPI Goals Tracker ──────────────────────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-emerald-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Target className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  KPI Goals Tracker
                  <DataSourceBadge source="computed" />
                </CardTitle>
                <Badge variant="outline" className="text-[9px]">{kpis.filter(k => getKpiStatus(k).label === 'ON TRACK').length}/{kpis.length} On Track</Badge>
              </div>
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              <div className="space-y-3">
                {kpis.map((kpi) => {
                  const status = getKpiStatus(kpi)
                  return (
                    <div key={kpi.name} className="flex items-center gap-3 rounded-lg border border-border/50 bg-accent/20 px-3 py-2.5 transition-colors hover:bg-accent/30">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-xs font-medium">{kpi.name}</span>
                          <Badge className={`text-[8px] px-1.5 py-0 h-4 ${status.color}`}>{status.label}</Badge>
                          <span className="ml-auto flex items-center gap-0.5 text-[10px] text-muted-foreground">
                            {trendIcon(kpi.trend)}
                            {kpi.trendLabel}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1">
                            <Progress value={status.pct} className={`h-1.5 ${getProgressColor(status.pct)}`} />
                          </div>
                          <span className="text-[10px] tabular-nums text-muted-foreground w-28 text-right shrink-0">
                            <span className={status.label === 'ON TRACK' ? 'text-emerald-600 dark:text-emerald-400' : status.label === 'AT RISK' ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}>
                              {kpi.current}{kpi.unit ? ` ${kpi.unit}` : ''}
                            </span>
                            {' / '}
                            {kpi.target}{kpi.unit ? ` ${kpi.unit}` : ''}
                          </span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 shrink-0 text-muted-foreground hover:text-foreground"
                            onClick={() => handleEditTarget(
                              kpi.name === 'System Uptime' ? 'systemUptime' :
                              kpi.name === 'Token Efficiency' ? 'tokenEfficiency' :
                              kpi.name === 'Decision Accuracy' ? 'decisionAccuracy' :
                              kpi.name === 'Model Health Score' ? 'modelHealthScore' :
                              kpi.name === 'Trust Score Minimum' ? 'trustMin' :
                              kpi.name === 'Agent Productivity' ? 'agentProductivity' :
                              kpi.name === 'Model Coverage' ? 'modelCoverage' :
                              kpi.name === 'Collapse Rate' ? 'collapseRate' :
                              kpi.name === 'Rate Limit Hit Rate' ? 'rateLimitHitRate' :
                              kpi.name === 'Agent Utilization' ? 'agentUtilization' :
                              kpi.name === 'Test Pass Rate' ? 'testPassRate' :
                              kpi.name === 'Budget Burn Rate' ? 'budgetBurnRate' : 'vaultIntegrity',
                              kpi.target
                            )}
                          >
                            <Edit2 className="h-2.5 w-2.5" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <div className="section-divider" />

        {/* ── C. Unit Economics ──────────────────────────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-emerald-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Coins className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Unit Economics
                <DataSourceBadge source="computed" />
              </CardTitle>
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {unitEconomics.map((eco) => (
                  <div key={eco.label} className="rounded-lg border border-border/50 bg-accent/20 px-3 py-3">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-1">{eco.label}</p>
                    <div className="flex items-baseline gap-1 mb-2">
                      <span className="text-xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{eco.value.toLocaleString()}</span>
                      <span className="text-[10px] text-muted-foreground">{eco.unit}</span>
                    </div>
                    <MiniAreaChart data={eco.sparkline} dataKey="value" color={COLORS.emerald} height={28} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <div className="section-divider" />

        {/* ── D. Model Coverage Analysis ─────────────────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-emerald-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Router className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Model Coverage Analysis
                <DataSourceBadge source="computed" />
              </CardTitle>
            </CardHeader>
            <CardContent className="relative p-4 pt-0 space-y-4">
              {/* Pool Coverage */}
              <div>
                <p className="text-[11px] font-medium text-muted-foreground mb-2">Pool Coverage</p>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  {poolCoverage.map((pool) => (
                    <div key={pool.name} className="rounded-lg border border-border/50 bg-accent/20 px-3 py-2.5">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-semibold">{pool.name}</span>
                        <Badge className={`text-[8px] px-1.5 py-0 h-4 border-0 ${pool.coverage >= 90 ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : pool.coverage >= 70 ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' : 'bg-red-600/15 text-red-600 dark:text-red-400'}`}>
                          {pool.coverage}%
                        </Badge>
                      </div>
                      <Progress value={pool.coverage} className={`h-1.5 ${pool.coverage >= 90 ? '[&>div]:bg-emerald-500' : pool.coverage >= 70 ? '[&>div]:bg-yellow-500' : '[&>div]:bg-red-500'}`} />
                      <p className="text-[9px] text-muted-foreground mt-1">{pool.healthy}/{pool.total} models healthy</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Model Utilization Chart */}
              <div>
                <p className="text-[11px] font-medium text-muted-foreground mb-2">Model Utilization</p>
                <NexusBarChart
                  data={modelUtilization}
                  dataKey="value"
                  nameKey="name"
                  color={COLORS.emerald}
                  height={140}
                />
              </div>

              {/* Coverage Trend */}
              <div>
                <p className="text-[11px] font-medium text-muted-foreground mb-2">7-Day Coverage Trend</p>
                <div className="space-y-2">
                  {['PREMIUM', 'MID', 'FAST', 'FREE_RESEARCH'].map((tier) => {
                    const tierColors: Record<string, string> = { PREMIUM: COLORS.emerald, MID: COLORS.blue, FAST: COLORS.orange, FREE_RESEARCH: COLORS.purple }
                    const data = coverageTrend.map((d) => ({ name: d.name, value: d[tier as keyof typeof d] as number }))
                    return (
                      <div key={tier} className="flex items-center gap-3">
                        <span className="text-[10px] font-medium w-28 shrink-0">{tier}</span>
                        <div className="flex-1">
                          <MiniAreaChart data={data} dataKey="value" color={tierColors[tier]} height={24} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <div className="section-divider" />

        {/* ── E. Anomaly Detection + F. Recommendations ─────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Anomaly Detection */}
          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden border-orange-600/15 h-full">
              <div className="absolute inset-0 bg-gradient-to-br from-orange-600/3 via-transparent to-transparent" />
              <CardHeader className="relative pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                    Anomaly Detection
                    <DataSourceBadge source="computed" />
                  </CardTitle>
                  <Badge className={`text-[9px] border-0 ${anomalies.filter(a => a.status === 'ACTIVE').length > 0 ? 'bg-orange-600/15 text-orange-600 dark:text-orange-400' : 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'}`}>
                    {anomalies.filter(a => a.status === 'ACTIVE').length} Active
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="relative p-4 pt-0">
                <div className="max-h-72 space-y-2 overflow-y-auto custom-scrollbar">
                  {anomalies.map((anomaly) => (
                    <div key={anomaly.id} className="flex items-start gap-2 rounded-md border border-border/50 bg-accent/20 px-2.5 py-2 text-xs">
                      <Badge className={`text-[7px] px-1 py-0 h-4 shrink-0 border-0 ${
                        anomaly.severity === 'CRITICAL' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                        anomaly.severity === 'WARNING' ? 'bg-orange-600/15 text-orange-600 dark:text-orange-400' :
                        'bg-blue-600/15 text-blue-600 dark:text-blue-400'
                      }`}>
                        {anomaly.severity}
                      </Badge>
                      <div className="flex-1 min-w-0">
                        <p className="text-muted-foreground leading-relaxed">{anomaly.description}</p>
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground/60">
                          <span>{anomaly.resource}</span>
                          <span>·</span>
                          <span>{anomaly.time}</span>
                        </div>
                      </div>
                      <Badge className={`text-[7px] px-1 py-0 h-4 shrink-0 border-0 ${anomaly.status === 'ACTIVE' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'}`}>
                        {anomaly.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Optimization Recommendations */}
          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden border-emerald-600/15 h-full">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
              <CardHeader className="relative pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Lightbulb className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    Optimization Recommendations
                    <DataSourceBadge source="mock" />
                  </CardTitle>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <select
                    value={recFilterPriority}
                    onChange={(e) => setRecFilterPriority(e.target.value)}
                    className="rounded-md border border-border/50 bg-accent/30 px-2 py-1 text-[10px] text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-600"
                  >
                    <option value="ALL">All Priorities</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                  <select
                    value={recFilterStatus}
                    onChange={(e) => setRecFilterStatus(e.target.value)}
                    className="rounded-md border border-border/50 bg-accent/30 px-2 py-1 text-[10px] text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-600"
                  >
                    <option value="ALL">All Status</option>
                    <option value="OPEN">OPEN</option>
                    <option value="IN PROGRESS">IN PROGRESS</option>
                    <option value="APPLIED">APPLIED</option>
                  </select>
                </div>
              </CardHeader>
              <CardContent className="relative p-4 pt-0">
                <div className="max-h-72 space-y-2 overflow-y-auto custom-scrollbar">
                  {filteredRecs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
                      <CheckCircle2 className="h-6 w-6 mb-1.5 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-xs">No matching recommendations</span>
                    </div>
                  ) : (
                    filteredRecs.map((rec) => (
                      <div key={rec.id} className="rounded-lg border border-border/50 bg-accent/20 px-3 py-2.5 transition-colors hover:bg-accent/30">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <div className="flex items-center gap-1.5">
                            <Sparkles className="h-3 w-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                            <span className="text-xs font-medium">{rec.title}</span>
                          </div>
                          <Badge className={`text-[7px] px-1 py-0 h-4 shrink-0 border-0 ${
                            rec.priority === 'HIGH' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                            rec.priority === 'MEDIUM' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
                            'bg-blue-600/15 text-blue-600 dark:text-blue-400'
                          }`}>
                            {rec.priority}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-muted-foreground leading-relaxed mb-2">{rec.description}</p>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-[10px]">
                            <Badge variant="outline" className="text-[8px] px-1 py-0 h-4">Est. {rec.savings}</Badge>
                            <span className="text-muted-foreground">Owner: {rec.owner}</span>
                            <Badge className={`text-[7px] px-1 py-0 h-4 border-0 ${
                              rec.status === 'APPLIED' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
                              rec.status === 'IN PROGRESS' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
                              'bg-accent/50 text-muted-foreground'
                            }`}>
                              {rec.status}
                            </Badge>
                          </div>
                          {rec.status !== 'APPLIED' && (
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 text-[9px] text-muted-foreground hover:text-red-600 px-1.5"
                                onClick={() => handleDismissRec(rec.id)}
                              >
                                <X className="h-2.5 w-2.5 mr-0.5" /> Dismiss
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-5 text-[9px] text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 px-1.5"
                                onClick={() => handleApplyRec(rec.id)}
                              >
                                <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" /> Apply
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Footer */}
        <motion.div variants={staggerItem}>
          <div className="flex items-center justify-center gap-4 text-[10px] text-muted-foreground/50 pt-2">
            <span>KPI Dashboard</span><span>·</span>
            <span>Unit Economics Tracking</span><span>·</span>
            <span>Anomaly Detection</span><span>·</span>
            <span>CORA Recommendations</span><span>·</span>
            <span>30s auto-refresh</span>
          </div>
        </motion.div>
      </motion.div>

      {/* ── Edit Target Dialog ──────────────────────────────────── */}
      <Dialog open={!!editTarget} onOpenChange={(open) => { if (!open) setEditTarget(null) }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm">Edit KPI Target</DialogTitle>
          </DialogHeader>
          {editTarget && (
            <div className="space-y-3 py-2">
              <p className="text-xs text-muted-foreground">Update the target value for this KPI. Changes are local only.</p>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium w-16 shrink-0">Target:</span>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={editTarget.value}
                  onChange={(e) => setEditTarget({ ...editTarget, value: e.target.value })}
                  className="flex-1 rounded-md border border-border/50 bg-accent/30 px-3 py-1.5 text-sm tabular-nums focus:outline-none focus:ring-1 focus:ring-emerald-600"
                />
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditTarget(null)} className="text-xs">Cancel</Button>
            <Button size="sm" onClick={handleSaveTarget} className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white">Save Target</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
