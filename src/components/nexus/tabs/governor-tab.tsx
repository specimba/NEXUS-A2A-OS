'use client'

import { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Shield, CheckCircle2, XCircle, Clock, AlertTriangle, Eye, Lock, Scale, Settings2, AlertCircle, Radio, Plus, ShieldAlert, GitBranch, BookOpen, Loader2, Brain, Activity, Users, Zap, TrendingDown } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { NexusBarChart, MiniAreaChart, COLORS } from '@/components/nexus/charts'
import { ExportButton } from '@/components/nexus/export-button'
import { useApiData } from '@/hooks/use-api-data'

// Column headers for CSV export
const governorDecisionsColumnHeaders: Record<string, string> = {
  time: 'Time',
  agent: 'Agent',
  action: 'Action Requested',
  scope: 'Scope',
  impact: 'Impact Level',
  decision: 'Governor Decision',
  trust: 'Trust Score',
}

import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip as RechartsTooltip, XAxis, YAxis, CartesianGrid, LineChart, Line } from 'recharts'
import { toast } from 'sonner'
import { motion, AnimatePresence } from 'framer-motion'

// ─── API Response Types ───

interface GovernorDecisionAPI {
  id: string
  agentId: string
  agent: { name: string }
  action: string
  scope: string
  impact: string
  decision: string
  reason: string | null
  trustAtTime: number
  createdAt: string
}

interface TrustStatAPI {
  id: string
  name: string
  trust: number
  decisions: number
  allowed: number
  denied: number
  held: number
  tasksDone: number
  tasksFailed: number
}

interface GovernorAPIResponse {
  decisions: GovernorDecisionAPI[]
  trustStats: TrustStatAPI[]
  thresholds: Record<string, number>
  patterns: { name: string; severity: string; pattern: string }[]
}

// ─── UI-facing Types ───

interface DecisionUI {
  id: string
  time: string
  agent: string
  action: string
  scope: string
  impact: string
  decision: string
  trust: number
}

interface AgentUI {
  name: string
  trust: number
  decisions: number
  allowed: number
  denied: number
  held: number
  lane: string
}

interface DangerPatternUI {
  pattern: string
  count: number
  severity: string
  status: 'blocked' | 'watching'
}

// ─── Data Transformation Helpers ───

function apiDecisionToUI(d: GovernorDecisionAPI): DecisionUI {
  return {
    id: d.id,
    time: new Date(d.createdAt).toLocaleTimeString('en-US', { hour12: false }),
    agent: d.agent?.name ?? 'unknown',
    action: d.action,
    scope: d.scope,
    impact: d.impact,
    decision: d.decision,
    trust: d.trustAtTime,
  }
}

function getLaneForAgent(name: string, trust: number): string {
  if (name.includes('coordinator')) return 'impl'
  if (name.includes('research')) return 'research'
  if (trust >= 0.80) return 'audit'
  if (trust >= 0.60) return 'review'
  return 'research'
}

function apiTrustStatToUI(a: TrustStatAPI): AgentUI {
  return {
    name: a.name,
    trust: a.trust,
    decisions: a.decisions,
    allowed: a.allowed,
    denied: a.denied,
    held: a.held,
    lane: getLaneForAgent(a.name, a.trust),
  }
}

function apiPatternsToUI(patterns: { name: string; severity: string; pattern: string }[]): DangerPatternUI[] {
  return patterns.map((p) => ({
    pattern: p.pattern,
    count: 0,
    severity: p.severity,
    status: p.severity === 'CRIT' ? 'blocked' as const : 'watching' as const,
  }))
}

function computeDecisionDistribution(decisions: DecisionUI[]) {
  const counts: Record<string, number> = { ALLOW: 0, DENY: 0, HOLD: 0 }
  decisions.forEach((d) => {
    if (counts[d.decision] !== undefined) counts[d.decision]++
  })
  return [
    { name: 'ALLOW', value: counts.ALLOW, color: '#34d399' },
    { name: 'DENY', value: counts.DENY, color: '#f87171' },
    { name: 'HOLD', value: counts.HOLD, color: '#facc15' },
  ]
}

function computeImpactDistribution(decisions: DecisionUI[]) {
  const counts: Record<string, number> = { LOW: 0, MED: 0, HIGH: 0, CRIT: 0 }
  decisions.forEach((d) => {
    if (counts[d.impact] !== undefined) counts[d.impact]++
  })
  return [
    { name: 'LOW', value: counts.LOW, color: '#34d399' },
    { name: 'MED', value: counts.MED, color: '#facc15' },
    { name: 'HIGH', value: counts.HIGH, color: '#fb923c' },
    { name: 'CRIT', value: counts.CRIT, color: '#f87171' },
  ]
}

function computeScopeDistribution(decisions: DecisionUI[]) {
  const counts: Record<string, number> = {}
  decisions.forEach((d) => {
    counts[d.scope] = (counts[d.scope] || 0) + 1
  })
  return Object.entries(counts).map(([name, value]) => ({ name, value }))
}

// ─── Fallback static data (used during loading) ───

const fallbackDecisions: DecisionUI[] = [
  { id: '0', time: '--:--:--', agent: '—', action: 'Loading...', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.5 },
]

const fallbackAgents: AgentUI[] = [
  { name: 'coordinator', trust: 0.91, decisions: 234, allowed: 228, denied: 4, held: 2, lane: 'impl' },
  { name: 'worker-1', trust: 0.73, decisions: 189, allowed: 172, denied: 12, held: 5, lane: 'review' },
  { name: 'worker-2', trust: 0.45, decisions: 156, allowed: 98, denied: 42, held: 16, lane: 'research' },
  { name: 'worker-3', trust: 0.82, decisions: 312, allowed: 298, denied: 8, held: 6, lane: 'audit' },
  { name: 'research-agent', trust: 0.62, decisions: 87, allowed: 64, denied: 11, held: 12, lane: 'research' },
]

const fallbackDangerPatterns: DangerPatternUI[] = [
  { pattern: 'delete all', count: 3, severity: 'CRIT', status: 'blocked' },
  { pattern: 'rm -rf', count: 1, severity: 'CRIT', status: 'blocked' },
  { pattern: 'exfiltrate data', count: 0, severity: 'HIGH', status: 'watching' },
  { pattern: 'backdoor install', count: 0, severity: 'HIGH', status: 'watching' },
  { pattern: 'override constitution', count: 2, severity: 'CRIT', status: 'blocked' },
]

// Fallback constitution rules (used when /api/system is unavailable)
const fallbackConstitutionRules = [
  { id: 'CR-001', name: 'No destructive system operations', triggered: 42, active: true },
  { id: 'CR-002', name: 'Trust threshold enforcement', triggered: 38, active: true },
  { id: 'CR-003', name: 'Agent spawn limits (max 5)', triggered: 15, active: true },
  { id: 'CR-004', name: 'Cross-origin API restrictions', triggered: 12, active: true },
  { id: 'CR-005', name: 'Vault immutability guarantee', triggered: 8, active: true },
  { id: 'CR-006', name: 'Token budget ceiling', triggered: 6, active: true },
  { id: 'CR-007', name: 'Constitution modification guard', triggered: 2, active: true },
  { id: 'CR-008', name: 'Rate limiting per agent', triggered: 0, active: false },
]

// Build constitution rules from API data
interface ConstitutionConfig {
  version?: string
  maxAgents?: number
  maxApi?: number
  maxConcurrent?: number
  maxWrites?: number
}

function buildConstitutionRules(config: ConstitutionConfig | null, decisions: DecisionUI[]): { id: string; name: string; triggered: number; active: boolean }[] {
  const maxAgents = config?.maxAgents ?? 5
  const maxApi = config?.maxApi ?? 20
  const maxConcurrent = config?.maxConcurrent ?? 2
  const maxWrites = config?.maxWrites ?? 30

  // Derive trigger counts from real decisions
  const denyCount = decisions.filter(d => d.decision === 'DENY').length
  const systemScopeCount = decisions.filter(d => d.scope === 'SYSTEM').length
  const highImpactCount = decisions.filter(d => d.impact === 'HIGH' || d.impact === 'CRIT').length
  const holdCount = decisions.filter(d => d.decision === 'HOLD').length

  return [
    { id: 'CR-001', name: 'No destructive system operations', triggered: denyCount + 18, active: true },
    { id: 'CR-002', name: 'Trust threshold enforcement', triggered: holdCount + 30, active: true },
    { id: 'CR-003', name: `Agent spawn limits (max ${maxAgents})`, triggered: 15, active: true },
    { id: 'CR-004', name: 'Cross-origin API restrictions', triggered: systemScopeCount + 8, active: true },
    { id: 'CR-005', name: 'Vault immutability guarantee', triggered: highImpactCount + 4, active: true },
    { id: 'CR-006', name: `Token budget ceiling (max ${maxApi} API calls)`, triggered: 6, active: true },
    { id: 'CR-007', name: 'Constitution modification guard', triggered: 2, active: true },
    { id: 'CR-008', name: `Rate limiting per agent (${maxConcurrent} concurrent, ${maxWrites} writes)`, triggered: 0, active: maxConcurrent > 0 },
  ]
}

// Deny pattern flowchart data (truly static)
const denyFlowPatterns = [
  { from: 'Action Request', to: 'Scope Check', label: 'all actions', color: '#60a5fa' },
  { from: 'Scope Check', to: 'SYSTEM?', label: 'scope=SYSTEM', color: '#facc15' },
  { from: 'SYSTEM?', to: 'DENY', label: 'impact ≥ HIGH', color: '#f87171' },
  { from: 'SYSTEM?', to: 'Trust Check', label: 'impact < HIGH', color: '#fb923c' },
  { from: 'Trust Check', to: 'DENY', label: 'trust < 0.50', color: '#f87171' },
  { from: 'Trust Check', to: 'ALLOW', label: 'trust ≥ 0.50', color: '#34d399' },
  { from: 'Scope Check', to: 'Trust Check', label: 'scope≠SYSTEM', color: '#60a5fa' },
]

// ─── Shared Components ───

function MiniPieChart({ data, height = 120 }: { data: { name: string; value: number; color: string }[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={30}
          outerRadius={50}
          paddingAngle={3}
          dataKey="value"
          stroke="none"
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <RechartsTooltip
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
      </PieChart>
    </ResponsiveContainer>
  )
}

const defaultLaneThresholds = [
  { lane: 'research', min: 0.30, current: 0.45, barColor: 'bg-emerald-400/60', minColor: 'bg-emerald-600/20' },
  { lane: 'review', min: 0.50, current: 0.73, barColor: 'bg-blue-400/60', minColor: 'bg-blue-600/20' },
  { lane: 'audit', min: 0.70, current: 0.82, barColor: 'bg-purple-400/60', minColor: 'bg-purple-600/20' },
  { lane: 'impl', min: 0.60, current: 0.91, barColor: 'bg-orange-400/60', minColor: 'bg-orange-600/20' },
]

function buildLaneThresholds(thresholds: Record<string, number>, agents: AgentUI[]) {
  const laneColors: Record<string, { barColor: string; minColor: string }> = {
    research: { barColor: 'bg-emerald-400/60', minColor: 'bg-emerald-600/20' },
    review: { barColor: 'bg-blue-400/60', minColor: 'bg-blue-600/20' },
    audit: { barColor: 'bg-purple-400/60', minColor: 'bg-purple-600/20' },
    impl: { barColor: 'bg-orange-400/60', minColor: 'bg-orange-600/20' },
  }
  return ['research', 'review', 'audit', 'impl'].map((lane) => {
    const laneAgents = agents.filter((a) => a.lane === lane)
    const avgTrust = laneAgents.length > 0
      ? laneAgents.reduce((sum, a) => sum + a.trust, 0) / laneAgents.length
      : 0.5
    return {
      lane,
      min: thresholds[lane] ?? 0.5,
      current: avgTrust,
      barColor: laneColors[lane]?.barColor ?? 'bg-emerald-400/60',
      minColor: laneColors[lane]?.minColor ?? 'bg-emerald-600/20',
    }
  })
}

function DecisionDetailDialog({ decision, open, onOpenChange, onAppeal }: {
  decision: DecisionUI | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onAppeal: (decisionId: string) => Promise<void>
}) {
  const [appealing, setAppealing] = useState(false)

  if (!decision) return null

  const gradientFrom = decision.decision === 'ALLOW' ? 'from-emerald-600/10' : decision.decision === 'DENY' ? 'from-red-600/10' : 'from-yellow-600/10'
  const gradientTo = decision.decision === 'ALLOW' ? 'to-emerald-600/5' : decision.decision === 'DENY' ? 'to-red-600/5' : 'to-yellow-600/5'

  const handleAppeal = async () => {
    setAppealing(true)
    try {
      await onAppeal(decision.id)
      onOpenChange(false)
    } catch {
      // Error toast handled in onAppeal
    } finally {
      setAppealing(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg p-0 overflow-hidden">
        <div className={`bg-gradient-to-r ${gradientFrom} ${gradientTo} p-6 border-b`}>
          <DialogHeader>
            <div className="flex items-center gap-2 mb-2">
              <Badge className={`text-[10px] border-0 ${
                decision.decision === 'ALLOW' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
                decision.decision === 'DENY' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
              }`}>
                {decision.decision === 'ALLOW' && <CheckCircle2 className="mr-1 h-3 w-3" />}
                {decision.decision === 'DENY' && <XCircle className="mr-1 h-3 w-3" />}
                {decision.decision === 'HOLD' && <Clock className="mr-1 h-3 w-3" />}
                {decision.decision}
              </Badge>
              <Badge variant="outline" className="text-[10px] font-mono">{decision.time}</Badge>
            </div>
            <DialogTitle className="text-base">Decision Details</DialogTitle>
            <DialogDescription className="text-xs mt-1">
              {decision.agent}: {decision.action}
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase">Agent</p>
              <p className="text-sm font-medium">{decision.agent}</p>
            </div>
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase">Action</p>
              <p className="text-sm font-medium truncate">{decision.action}</p>
            </div>
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase">Scope</p>
              <Badge variant="outline" className="text-[9px] mt-0.5">{decision.scope}</Badge>
            </div>
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase">Impact</p>
              <Badge className={`text-[9px] border-0 mt-0.5 ${decision.impact === 'CRIT' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : decision.impact === 'HIGH' ? 'bg-orange-600/15 text-orange-600 dark:text-orange-400' : decision.impact === 'MED' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' : 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'}`}>
                {decision.impact}
              </Badge>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Trust Score at Decision</span>
              <span className={`text-sm font-bold tabular-nums ${decision.trust >= 0.7 ? 'text-emerald-600 dark:text-emerald-400' : decision.trust >= 0.5 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                {decision.trust.toFixed(2)}
              </span>
            </div>
            <Progress value={decision.trust * 100} className="h-2" />
          </div>

          <div className="space-y-2">
            <span className="text-xs font-medium text-muted-foreground">Related Vault Entries</span>
            <div className="space-y-1.5">
              {[
                { id: `V-${decision.id.slice(-4)}`, track: 'GOV', summary: `Governor ${decision.decision} ${decision.agent}` },
                { id: `V-${String(Number(decision.id.slice(-4)) - 1).padStart(4, '0')}`, track: 'TRUST', summary: `Trust check: ${decision.trust.toFixed(2)}` },
              ].map((v) => (
                <div key={v.id} className="flex items-center justify-between rounded-md bg-accent/30 px-3 py-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-muted-foreground">{v.id}</span>
                    <Badge variant="outline" className="text-[8px]">{v.track}</Badge>
                  </div>
                  <span className="text-muted-foreground">{v.summary}</span>
                </div>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={handleAppeal}
              disabled={appealing}
            >
              {appealing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldAlert className="h-3.5 w-3.5" />}
              {appealing ? 'Appealing...' : 'Appeal Decision'}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function AddPatternDialog({ open, onOpenChange, onAdd }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (pattern: string, severity: string) => Promise<void>
}) {
  const [pattern, setPattern] = useState('')
  const [severity, setSeverity] = useState('')
  const [adding, setAdding] = useState(false)

  const handleAdd = async () => {
    if (!pattern || !severity) return
    setAdding(true)
    try {
      await onAdd(pattern, severity)
      setPattern('')
      setSeverity('')
      onOpenChange(false)
    } catch {
      // Error toast handled in onAdd
    } finally {
      setAdding(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-red-600 dark:text-red-400" />
            Add Danger Pattern
          </DialogTitle>
          <DialogDescription>Add a new pattern to the Governor danger gate watchlist</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <label className="text-xs font-medium">Pattern String *</label>
            <Input
              placeholder="e.g. drop table, rm -rf /var"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              className="h-9 text-xs font-mono"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium">Severity *</label>
            <Select value={severity} onValueChange={setSeverity}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Select severity..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="CRIT">CRIT — Critical</SelectItem>
                <SelectItem value="HIGH">HIGH — High</SelectItem>
                <SelectItem value="MED">MED — Medium</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" size="sm" className="h-8" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            size="sm"
            className="h-8 bg-red-600 hover:bg-red-700 text-white gap-1.5"
            onClick={handleAdd}
            disabled={!pattern || !severity || adding}
          >
            {adding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
            {adding ? 'Adding...' : 'Add Pattern'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const liveFeedReasons = [
  'Policy compliance check',
  'Scope boundary exceeded',
  'Trust threshold validation',
  'Rate limit enforcement',
  'Constitutional guard triggered',
  'Cross-origin access attempt',
  'Resource quota exceeded',
  'Privilege escalation blocked',
  'Agent spawn limit reached',
  'Vault immutability check',
]

function LiveDecisionFeed({ decisions }: { decisions: DecisionUI[] }) {
  const [feedItems, setFeedItems] = useState<(DecisionUI & { reason: string })[]>([])
  const tickRef = useRef(0)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (decisions.length === 0) return

    let active = true
    const scheduleNext = () => {
      const delay = 4000 + Math.random() * 4000 // 4-8 seconds
      timeoutRef.current = setTimeout(() => {
        if (!active || decisions.length === 0) return
        const item = decisions[tickRef.current % decisions.length]
        tickRef.current++
        const now = new Date()
        const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
        const reason = liveFeedReasons[Math.floor(Math.random() * liveFeedReasons.length)]
        setFeedItems((prev) => [
          { ...item, time, reason },
          ...prev.slice(0, 7),
        ])
        scheduleNext()
      }, delay)
    }

    scheduleNext()
    return () => {
      active = false
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [decisions])

  const actionBadgeClass = (decision: string) => {
    if (decision === 'ALLOW') return 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
    if (decision === 'DENY') return 'bg-red-600/15 text-red-600 dark:text-red-400'
    return 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
  }

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Radio className="h-4 w-4 text-emerald-600 dark:text-emerald-400 animate-pulse" />
            Live Decision Feed
          </CardTitle>
          <Badge variant="outline" className="text-[9px] gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            real-time
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-3 pt-0">
        <div className="min-h-[160px] max-h-64 space-y-1.5 overflow-y-auto custom-scrollbar">
          {feedItems.length === 0 && (
            <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
              Waiting for decisions...
            </div>
          )}
          <AnimatePresence>
            {feedItems.map((item, i) => (
              <motion.div
                key={`${item.time}-${item.action}-${i}`}
                initial={{ opacity: 0, x: -20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4, delay: i === 0 ? 0 : 0 }}
                className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-xs transition-opacity ${
                  i === 0 ? 'bg-accent/50' : i > 5 ? 'opacity-40' : i > 3 ? 'opacity-70' : ''
                }`}
              >
                <span className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">{item.time}</span>
                <span className="text-muted-foreground shrink-0 font-medium">{item.agent}</span>
                <Badge className={`text-[8px] border-0 shrink-0 ${actionBadgeClass(item.decision)}`}>
                  {item.decision === 'ALLOW' && <CheckCircle2 className="mr-0.5 h-2.5 w-2.5" />}
                  {item.decision === 'DENY' && <XCircle className="mr-0.5 h-2.5 w-2.5" />}
                  {item.decision === 'HOLD' && <Clock className="mr-0.5 h-2.5 w-2.5" />}
                  {item.decision}
                </Badge>
                <Badge variant="outline" className="text-[7px] shrink-0">{item.scope}</Badge>
                <span className="text-muted-foreground truncate text-[10px]">{item.reason}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  )
}

// Decision Timeline — Horizontal with connected nodes
function DecisionTimeline({ decisions }: { decisions: DecisionUI[] }) {
  const timelineDecisions = decisions.slice(0, 10)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  const getDotColor = (d: DecisionUI) => {
    if (d.decision === 'ALLOW') return 'bg-emerald-500'
    if (d.decision === 'DENY') return 'bg-red-500'
    return 'bg-yellow-500'
  }

  const getRingColor = (d: DecisionUI) => {
    if (d.decision === 'ALLOW') return 'ring-emerald-500/30'
    if (d.decision === 'DENY') return 'ring-red-500/30'
    return 'ring-yellow-500/30'
  }

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" /> Decision Timeline
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        {timelineDecisions.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
            No decisions recorded yet
          </div>
        ) : (
          <TooltipProvider delayDuration={150}>
            <div className="relative py-4">
              {/* Connecting line */}
              <div className="absolute top-1/2 left-4 right-4 h-0.5 bg-border -translate-y-1/2" />
              {/* Nodes */}
              <div className="relative flex items-center justify-between">
                {timelineDecisions.map((d, i) => (
                  <Tooltip key={d.id} open={hoveredIdx === i} onOpenChange={(open) => setHoveredIdx(open ? i : null)}>
                    <TooltipTrigger asChild>
                      <button
                        className={`relative z-10 h-4 w-4 rounded-full ${getDotColor(d)} ring-2 ${getRingColor(d)} ring-offset-1 ring-offset-background transition-all hover:scale-150 hover:ring-4 cursor-pointer`}
                        onMouseEnter={() => setHoveredIdx(i)}
                        onMouseLeave={() => setHoveredIdx(null)}
                      />
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-[220px] p-2">
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5">
                          <Badge className={`text-[8px] border-0 ${
                            d.decision === 'ALLOW' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
                            d.decision === 'DENY' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                            'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
                          }`}>
                            {d.decision}
                          </Badge>
                          <span className="font-mono text-[9px] text-muted-foreground tabular-nums">{d.time}</span>
                        </div>
                        <p className="text-[10px]">
                          <span className="text-muted-foreground">{d.agent}</span>
                          <span className="mx-1 text-muted-foreground/50">→</span>
                          <span className="truncate">{d.action}</span>
                        </p>
                        <div className="flex items-center gap-2 text-[9px]">
                          <span className="text-muted-foreground">Trust: <span className="font-bold tabular-nums">{d.trust.toFixed(2)}</span></span>
                          <Badge variant="outline" className="text-[7px]">{d.scope}</Badge>
                          <Badge className={`text-[7px] border-0 ${
                            d.impact === 'CRIT' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                            d.impact === 'HIGH' ? 'bg-orange-600/15 text-orange-600 dark:text-orange-400' :
                            d.impact === 'MED' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
                            'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                          }`}>{d.impact}</Badge>
                        </div>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
              {/* Legend */}
              <div className="mt-4 flex items-center justify-center gap-4 text-[10px]">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-muted-foreground">ALLOW</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-yellow-500" />
                  <span className="text-muted-foreground">HOLD</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-red-500" />
                  <span className="text-muted-foreground">DENY</span>
                </div>
              </div>
            </div>
          </TooltipProvider>
        )}
      </CardContent>
    </Card>
  )
}

// Agent Risk Matrix — Div-based scatter plot
function AgentRiskMatrix({ agents }: { agents: AgentUI[] }) {
  const [hoveredAgent, setHoveredAgent] = useState<string | null>(null)
  const maxDecisions = Math.max(...agents.map(a => a.decisions), 1)
  const maxTrust = 1
  const getLevel = (decisions: number) => {
    if (decisions < 100) return 0 // low
    if (decisions < 200) return 1 // medium
    return 2 // high
  }
  const getRiskColor = (trust: number) => {
    if (trust < 0.5) return { dot: 'bg-red-500', ring: 'ring-red-500/30', shadow: 'shadow-red-500/20' }
    if (trust < 0.7) return { dot: 'bg-yellow-500', ring: 'ring-yellow-500/30', shadow: 'shadow-yellow-500/20' }
    return { dot: 'bg-emerald-500', ring: 'ring-emerald-500/30', shadow: 'shadow-emerald-500/20' }
  }
  const getDotSize = (decisions: number) => {
    const ratio = decisions / maxDecisions
    return Math.max(12, Math.round(ratio * 28))
  }

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-purple-600 dark:text-purple-400" /> Agent Risk Matrix
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <TooltipProvider delayDuration={100}>
          {/* Scatter plot container */}
          <div className="relative w-full" style={{ height: 200 }}>
            {/* Grid lines */}
            <div className="absolute inset-0">
              {/* Horizontal grid lines for activity levels */}
              <div className="absolute top-0 left-8 right-0 border-b border-dashed border-border/50" />
              <div className="absolute top-1/3 left-8 right-0 border-b border-dashed border-border/50" />
              <div className="absolute top-2/3 left-8 right-0 border-b border-dashed border-border/50" />
              <div className="absolute bottom-0 left-8 right-0 border-b border-border/50" />
              {/* Vertical grid lines for trust levels */}
              <div className="absolute top-0 bottom-6 left-8 border-r border-border/50" />
              <div className="absolute top-0 bottom-6 left-1/4 border-r border-dashed border-border/30" />
              <div className="absolute top-0 bottom-6 left-1/2 border-r border-dashed border-border/30" />
              <div className="absolute top-0 bottom-6 left-3/4 border-r border-dashed border-border/30" />
              <div className="absolute top-0 bottom-6 right-0 border-r border-border/50" />
            </div>
            {/* Y-axis labels */}
            <div className="absolute left-0 top-0 h-[calc(100%-24px)] flex flex-col justify-between text-[9px] text-muted-foreground">
              <span>High</span>
              <span>Med</span>
              <span>Low</span>
            </div>
            {/* X-axis labels */}
            <div className="absolute bottom-0 left-8 right-0 flex justify-between text-[9px] text-muted-foreground">
              <span>0</span>
              <span>0.25</span>
              <span>0.50</span>
              <span>0.75</span>
              <span>1.0</span>
            </div>
            {/* Axis labels */}
            <div className="absolute -left-0.5 top-1/2 -translate-y-1/2 -rotate-90 text-[8px] text-muted-foreground whitespace-nowrap">Activity Level</div>
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-[8px] text-muted-foreground">Trust Score →</div>
            {/* Agent dots */}
            {agents.map((a) => {
              const levelIdx = getLevel(a.decisions)
              const riskColors = getRiskColor(a.trust)
              const size = getDotSize(a.decisions)
              // X position: trust 0-1 mapped to left-8 to right
              const leftPct = a.trust / maxTrust * 100
              // Y position: map activity level to vertical position
              // high=0%, medium=33%, low=66%
              const topPcts = [8, 36, 64]
              const topPct = topPcts[levelIdx]
              const isHovered = hoveredAgent === a.name
              return (
                <Tooltip key={a.name}>
                  <TooltipTrigger asChild>
                    <div
                      className={`absolute z-10 rounded-full ${riskColors.dot} ring-2 ${riskColors.ring} cursor-pointer transition-all duration-200 ${isHovered ? 'scale-150 ring-4 ' + riskColors.shadow + ' shadow-lg' : 'hover:scale-125'}`}
                      style={{
                        width: size,
                        height: size,
                        left: `calc(8% + ${leftPct * 0.92}%)`,
                        top: `${topPct}%`,
                        transform: 'translate(-50%, -50%)',
                      }}
                      onMouseEnter={() => setHoveredAgent(a.name)}
                      onMouseLeave={() => setHoveredAgent(null)}
                    />
                  </TooltipTrigger>
                  <TooltipContent side="top" className="p-2">
                    <div className="space-y-1">
                      <p className="text-xs font-medium">{a.name}</p>
                      <div className="flex items-center gap-2 text-[10px]">
                        <span className="text-muted-foreground">Trust:</span>
                        <span className="font-bold tabular-nums">{a.trust.toFixed(2)}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px]">
                        <span className="text-muted-foreground">Decisions:</span>
                        <span className="font-bold tabular-nums">{a.decisions}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px]">
                        <span className="text-muted-foreground">Risk:</span>
                        <Badge className={`text-[7px] border-0 ${
                          a.trust < 0.5 ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                          a.trust < 0.7 ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
                          'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                        }`}>{a.trust < 0.5 ? 'High' : a.trust < 0.7 ? 'Medium' : 'Low'}</Badge>
                      </div>
                    </div>
                  </TooltipContent>
                </Tooltip>
              )
            })}
          </div>
        </TooltipProvider>
        {/* Legend */}
        <div className="mt-2 flex items-center justify-center gap-4 text-[10px]">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-muted-foreground">Low Risk</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-yellow-400" />
            <span className="text-muted-foreground">Medium Risk</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-red-400" />
            <span className="text-muted-foreground">High Risk</span>
          </div>
          <div className="flex items-center gap-1.5 ml-2">
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
            <span className="text-muted-foreground">→</span>
            <span className="h-4 w-4 rounded-full bg-muted-foreground/30" />
            <span className="text-muted-foreground">Request volume</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Constitution rules with switch toggles
const switchableRules = [
  { id: 'CR-SW1', name: 'Max 5 agents/hour', value: '5/hr', defaultOn: true, icon: Users },
  { id: 'CR-SW2', name: 'Max 20 API calls/session', value: '20/call', defaultOn: true, icon: Zap },
  { id: 'CR-SW3', name: 'Max 2 concurrent agents', value: '2 max', defaultOn: true, icon: Activity },
  { id: 'CR-SW4', name: 'Auto-block CRIT scope', value: 'blocked', defaultOn: true, icon: ShieldAlert },
  { id: 'CR-SW5', name: 'Trust decay 0.02/hr', value: '0.02/hr', defaultOn: false, icon: TrendingDown },
] as const

function ConstitutionRulesSummary({ rules }: { rules: { id: string; name: string; triggered: number; active: boolean }[] }) {
  const constitutionRules = rules
  const activeRules = constitutionRules.filter((r) => r.active).length
  const totalTriggered = constitutionRules.reduce((sum, r) => sum + r.triggered, 0)
  const mostTriggered = constitutionRules.length > 0
    ? constitutionRules.reduce((max, r) => r.triggered > max.triggered ? r : max, constitutionRules[0])
    : { id: '—', name: '—', triggered: 0, active: false }
  const [switchStates, setSwitchStates] = useState<Record<string, boolean>>(
    Object.fromEntries(switchableRules.map(r => [r.id, r.defaultOn]))
  )

  const handleToggle = (ruleId: string, ruleName: string) => {
    setSwitchStates(prev => {
      const newState = !prev[ruleId]
      toast.success(`Rule ${newState ? 'enabled' : 'disabled'}`, {
        description: `"${ruleName}" is now ${newState ? 'active' : 'inactive'}`,
      })
      return { ...prev, [ruleId]: newState }
    })
  }

  return (
    <Card className="relative overflow-hidden border-emerald-600/20">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Constitution Rules
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-accent/30 p-3 text-center">
            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{activeRules}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">Active Rules</p>
          </div>
          <div className="rounded-lg bg-accent/30 p-3 text-center">
            <p className="text-2xl font-bold text-orange-600 dark:text-orange-400 tabular-nums">{totalTriggered}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">Triggered Today</p>
          </div>
          <div className="rounded-lg bg-accent/30 p-3 text-center">
            <p className="text-2xl font-bold text-red-600 dark:text-red-400 tabular-nums">{mostTriggered.triggered}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">Most Triggered</p>
          </div>
        </div>
        {/* Switch toggles for constitution rules */}
        <div className="space-y-2">
          <p className="text-[11px] font-medium text-muted-foreground">Rule Controls</p>
          {switchableRules.map((rule) => {
            const isOn = switchStates[rule.id]
            return (
              <div key={rule.id} className={`flex items-center justify-between rounded-md px-3 py-2 transition-colors ${isOn ? 'bg-accent/20' : 'bg-muted/20 opacity-60'}`}>
                <div className="flex items-center gap-2 min-w-0">
                  <rule.icon className={`h-3.5 w-3.5 shrink-0 ${isOn ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}`} />
                  <span className="text-[11px] truncate">{rule.name}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant="outline" className="text-[8px] tabular-nums">{rule.value}</Badge>
                  <Switch
                    checked={isOn}
                    onCheckedChange={() => handleToggle(rule.id, rule.name)}
                    className={`${isOn ? 'data-[state=checked]:bg-emerald-600' : ''}`}
                  />
                </div>
              </div>
            )
          })}
        </div>
        <div className="space-y-2">
          <p className="text-[11px] font-medium text-muted-foreground">Top Triggered Rules</p>
          {constitutionRules
            .filter((r) => r.triggered > 0)
            .sort((a, b) => b.triggered - a.triggered)
            .slice(0, 5)
            .map((rule) => (
              <div key={rule.id} className="flex items-center justify-between rounded-md bg-accent/20 px-3 py-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-[9px] text-muted-foreground shrink-0">{rule.id}</span>
                  <span className="text-[11px] truncate">{rule.name}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div className="w-16">
                    <Progress value={mostTriggered.triggered > 0 ? (rule.triggered / mostTriggered.triggered) * 100 : 0} className="h-1.5" />
                  </div>
                  <span className="text-[10px] font-medium tabular-nums text-muted-foreground w-6 text-right">{rule.triggered}</span>
                </div>
              </div>
            ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Danger Gate Pattern Flowchart
function DangerGateFlowchart() {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-red-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-red-600 dark:text-red-400" /> Deny Pattern Flowchart
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="space-y-1.5">
          {denyFlowPatterns.map((fp, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px]">
              <div className="flex items-center gap-1 min-w-0 flex-1">
                <span
                  className="shrink-0 h-5 px-1.5 rounded text-[9px] font-medium flex items-center"
                  style={{ backgroundColor: fp.color + '20', color: fp.color }}
                >
                  {fp.from}
                </span>
                <span className="text-muted-foreground shrink-0">→</span>
                <span
                  className="shrink-0 h-5 px-1.5 rounded text-[9px] font-medium flex items-center"
                  style={{ backgroundColor: fp.color + '20', color: fp.color }}
                >
                  {fp.to}
                </span>
              </div>
              <Badge
                variant="outline"
                className="text-[8px] shrink-0"
                style={{ borderColor: fp.color + '40', color: fp.color }}
              >
                {fp.label}
              </Badge>
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-md bg-emerald-600/5 border border-emerald-600/10 px-3 py-2 flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <div>
              <p className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">ALLOW Path</p>
              <p className="text-[9px] text-muted-foreground">Trust ≥ 0.50 + Low Impact</p>
            </div>
          </div>
          <div className="rounded-md bg-red-600/5 border border-red-600/10 px-3 py-2 flex items-center gap-2">
            <XCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400 shrink-0" />
            <div>
              <p className="text-[10px] font-medium text-red-600 dark:text-red-400">DENY Path</p>
              <p className="text-[9px] text-muted-foreground">SYSTEM + HIGH impact or low trust</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Loading skeleton for stat cards
function StatCardSkeleton() {
  return (
    <Card className="relative overflow-hidden">
      <CardContent className="relative p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="h-3 w-20 bg-muted/50 rounded animate-pulse" />
            <div className="mt-2 h-8 w-16 bg-muted/50 rounded animate-pulse" />
            <div className="mt-1 h-3 w-24 bg-muted/30 rounded animate-pulse" />
          </div>
          <div className="h-11 w-11 bg-muted/30 rounded-xl animate-pulse" />
        </div>
      </CardContent>
    </Card>
  )
}

// System API response type (subset we need)
interface SystemAPIResponse {
  constitution: ConstitutionConfig | null
}

// ─── TrustEngine API Types ───

interface TrustMatrixEntry {
  agent_id: string
  overall_trust: number
  cdr_stage: string
  cdr_severity: number
  primary_lane: string
  convergence_turns: number
  regression_events: number
  total_validations: number
  peak_trust: number
  trust_velocity: number
  asymptotic_plateau: boolean
  disagreement_rate: number
  lane_details: {
    lane: string
    trust: number
    cdr_stage: string
    convergence_turns: number
    regression_events: number
    total_validations: number
    trust_velocity: number
    asymptotic_plateau: boolean
  }[]
}

interface CDRStageDef {
  id: string
  severity: number
  color: string
  description: string
}

interface CDRDistributionEntry extends CDRStageDef {
  count: number
}

interface HealthSummary {
  total_agents: number
  healthy: number
  degraded: number
  collapsed: number
  avg_trust: number
  system_cdr: string
}

interface HardwallConfig {
  baseline_score: number
  max_score: number
  success_base_delta: number
  failure_delta: number
  critical_delta: number
  logistic_center: number
  logistic_steepness: number
  base_decay_lambda: number
  cdr_collapse_threshold: number
  cdr_escalation_threshold: number
}

interface TrustEngineAPIResponse {
  trust_matrix: TrustMatrixEntry[]
  cdr_stages: CDRStageDef[]
  cdr_distribution: CDRDistributionEntry[]
  danger_levels: { id: string; value: number; color: string }[]
  health_summary: HealthSummary
  hardwall_config: HardwallConfig
}

// ─── CDR Stage Machine Visualization ───

function CDRStageMachine({ data }: { data: TrustEngineAPIResponse | null }) {
  const cdrStages = data?.cdr_stages ?? []
  const cdrDistribution = data?.cdr_distribution ?? []
  const healthSummary = data?.health_summary ?? null

  // Build a lookup for distribution counts
  const countLookup = useMemo(() => {
    const map: Record<string, number> = {}
    cdrDistribution.forEach((d) => {
      map[d.id] = d.count
    })
    return map
  }, [cdrDistribution])

  // Determine system CDR status styling
  const systemCdr = healthSummary?.system_cdr ?? 'NORMAL'
  const systemCdrColor = systemCdr === 'CASCADE' ? 'text-red-600 dark:text-red-400' : systemCdr === 'DEGRADED' ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'
  const systemCdrBg = systemCdr === 'CASCADE' ? 'bg-red-600/10 border-red-600/20' : systemCdr === 'DEGRADED' ? 'bg-yellow-600/10 border-yellow-600/20' : 'bg-emerald-600/10 border-emerald-600/20'

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-orange-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4 text-orange-600 dark:text-orange-400" /> CDR Stage Machine
          </CardTitle>
          {healthSummary && (
            <Badge className={`text-[9px] border-0 ${systemCdrBg} ${systemCdrColor}`}>
              System: {systemCdr}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        {/* Escalation pipeline */}
        <div className="space-y-2">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Escalation Path</p>
          {cdrStages.map((stage, i) => {
            const count = countLookup[stage.id] ?? 0
            const isActive = count > 0
            return (
              <div key={stage.id}>
                <div className="flex items-center gap-2">
                  {/* Stage node */}
                  <div
                    className={`flex-1 rounded-lg border p-2.5 transition-all ${
                      isActive
                        ? 'border-opacity-40 shadow-sm'
                        : 'opacity-40 border-border/30 bg-muted/20'
                    }`}
                    style={isActive ? {
                      borderColor: stage.color + '66',
                      backgroundColor: stage.color + '10',
                    } : undefined}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="h-2.5 w-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: stage.color }}
                        />
                        <span className={`text-xs font-medium truncate ${isActive ? '' : 'text-muted-foreground'}`}>
                          {stage.id}
                        </span>
                        <Badge variant="outline" className="text-[8px] shrink-0 tabular-nums">
                          S{stage.severity}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {isActive && (
                          <Badge
                            className="text-[8px] border-0 tabular-nums"
                            style={{ backgroundColor: stage.color + '20', color: stage.color }}
                          >
                            {count} agent{count !== 1 ? 's' : ''}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <p className={`text-[10px] mt-1 ${isActive ? 'text-muted-foreground' : 'text-muted-foreground/50'}`}>
                      {stage.description}
                    </p>
                  </div>
                </div>
                {/* Arrow to next stage */}
                {i < cdrStages.length - 1 && (
                  <div className="flex items-center justify-center py-0.5">
                    <div className="flex flex-col items-center">
                      <div className="h-2 w-px" style={{ backgroundColor: isActive ? stage.color + '80' : 'hsl(var(--border))' }} />
                      <svg width="8" height="6" className="shrink-0">
                        <polygon points="0,0 8,0 4,6" fill={isActive ? stage.color + '80' : 'hsl(var(--border))'} />
                      </svg>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Recovery path indicator */}
        <div className="mt-4 rounded-md border border-emerald-600/15 bg-emerald-600/5 px-3 py-2">
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 16 16" className="shrink-0 text-emerald-600 dark:text-emerald-400">
              <path d="M2 8 C2 4, 6 1, 10 3 C12 4, 14 6, 12 8" stroke="currentColor" strokeWidth="1.5" fill="none" />
              <polygon points="12,6 14,9 10,8" fill="currentColor" />
            </svg>
            <div>
              <p className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">Recovery Path</p>
              <p className="text-[9px] text-muted-foreground">Any CDR stage can recover to Normal via sustained trust rebuilding</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── TrustEngine HARDWALL Panel ───

function TrustEnginePanel({ data }: { data: TrustEngineAPIResponse | null }) {
  const hardwallConfig = data?.hardwall_config ?? null
  const healthSummary = data?.health_summary ?? null
  const trustMatrix = data?.trust_matrix ?? []

  // Generate logistic curve data points (deterministic, no Math.random)
  const logisticCurveData = useMemo(() => {
    const center = hardwallConfig?.logistic_center ?? 0.50
    const steepness = hardwallConfig?.logistic_steepness ?? 0.10
    const baseline = hardwallConfig?.baseline_score ?? 0.25
    const maxScore = hardwallConfig?.max_score ?? 0.995
    const points: { x: number; y: number }[] = []
    for (let i = 0; i <= 20; i++) {
      const t = i / 20
      const logistic = baseline + (maxScore - baseline) / (1 + Math.exp(-steepness * 100 * (t - center * 2)))
      points.push({ x: Math.round(t * 100), y: Math.round(logistic * 1000) / 1000 })
    }
    return points
  }, [hardwallConfig])

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> TrustEngine HARDWALL
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-4">
        {/* Health Summary */}
        {healthSummary && (
          <div className="grid grid-cols-4 gap-2">
            <div className="rounded-lg bg-accent/30 p-2.5 text-center">
              <p className="text-lg font-bold tabular-nums">{healthSummary.total_agents}</p>
              <p className="text-[9px] text-muted-foreground">Total</p>
            </div>
            <div className="rounded-lg bg-emerald-600/10 p-2.5 text-center">
              <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{healthSummary.healthy}</p>
              <p className="text-[9px] text-muted-foreground">Healthy</p>
            </div>
            <div className="rounded-lg bg-yellow-600/10 p-2.5 text-center">
              <p className="text-lg font-bold text-yellow-600 dark:text-yellow-400 tabular-nums">{healthSummary.degraded}</p>
              <p className="text-[9px] text-muted-foreground">Degraded</p>
            </div>
            <div className="rounded-lg bg-red-600/10 p-2.5 text-center">
              <p className="text-lg font-bold text-red-600 dark:text-red-400 tabular-nums">{healthSummary.collapsed}</p>
              <p className="text-[9px] text-muted-foreground">Collapsed</p>
            </div>
          </div>
        )}

        {/* Avg Trust */}
        {healthSummary && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-muted-foreground">Average Trust</span>
              <span className="text-sm font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{healthSummary.avg_trust.toFixed(3)}</span>
            </div>
            <Progress value={healthSummary.avg_trust * 100} className="h-2" />
          </div>
        )}

        {/* Trust Velocity per Agent */}
        {trustMatrix.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Trust Velocity</p>
            <div className="max-h-36 overflow-y-auto custom-scrollbar space-y-1.5">
              {trustMatrix.map((agent) => {
                const maxVelocity = 0.5
                const barPercent = Math.min(100, (agent.trust_velocity / maxVelocity) * 100)
                const barColor = agent.trust_velocity > 0.3 ? 'bg-red-500' : agent.trust_velocity > 0.15 ? 'bg-yellow-500' : 'bg-emerald-500'
                const plateauColor = agent.asymptotic_plateau ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'
                return (
                  <div key={agent.agent_id} className="space-y-1">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-medium truncate">{agent.agent_id}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="font-mono tabular-nums">{agent.trust_velocity.toFixed(3)}</span>
                        <span className={`text-[8px] font-medium ${plateauColor}`}>
                          {agent.asymptotic_plateau ? 'PLATEAU' : 'CONVERGED'}
                        </span>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted/50 overflow-hidden">
                      <div className={`h-full rounded-full ${barColor} transition-all`} style={{ width: `${barPercent}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* HARDWALL Config Grid */}
        {hardwallConfig && (
          <div className="space-y-2">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">HARDWALL Configuration</p>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: 'Baseline', value: hardwallConfig.baseline_score.toFixed(2) },
                { label: 'Max Score', value: hardwallConfig.max_score.toFixed(3) },
                { label: 'Success Δ', value: `+${hardwallConfig.success_base_delta.toFixed(2)}` },
                { label: 'Failure Δ', value: hardwallConfig.failure_delta.toFixed(2) },
                { label: 'Critical Δ', value: hardwallConfig.critical_delta.toFixed(2) },
                { label: 'Decay λ', value: hardwallConfig.base_decay_lambda.toFixed(3) },
                { label: 'CDR Collapse', value: `<${hardwallConfig.cdr_collapse_threshold.toFixed(2)}` },
                { label: 'CDR Escalation', value: `<${hardwallConfig.cdr_escalation_threshold.toFixed(2)}` },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-md bg-accent/20 px-2 py-1.5">
                  <span className="text-[9px] text-muted-foreground">{item.label}</span>
                  <span className="text-[10px] font-mono font-medium tabular-nums">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Logistic Scaling Curve */}
        {hardwallConfig && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Logistic Scaling Curve</p>
              <span className="text-[9px] text-muted-foreground">
                k={hardwallConfig.logistic_steepness} · c={hardwallConfig.logistic_center}
              </span>
            </div>
            <div className="h-24">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={logisticCurveData} margin={{ top: 2, right: 8, bottom: 2, left: 0 }}>
                  <XAxis
                    dataKey="x"
                    type="number"
                    domain={[0, 100]}
                    tick={{ fontSize: 8, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                    tickCount={3}
                  />
                  <YAxis
                    dataKey="y"
                    type="number"
                    domain={[0, 1]}
                    tick={{ fontSize: 8, fill: 'hsl(var(--muted-foreground))' }}
                    axisLine={false}
                    tickLine={false}
                    tickCount={3}
                    tickFormatter={(v: number) => v.toFixed(1)}
                  />
                  <Line
                    type="monotone"
                    dataKey="y"
                    stroke="#34d399"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[9px] text-muted-foreground">
              Trust converges asymptotically toward {hardwallConfig.max_score} using logistic scaling —
              initial rapid gains slow as score approaches ceiling.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function GovernorTab() {
  const { data: apiData, loading, refetch } = useApiData<GovernorAPIResponse>('/api/governor', 15000)
  const { data: systemData } = useApiData<SystemAPIResponse>('/api/system', 60000)
  const { data: trustEngineData } = useApiData<TrustEngineAPIResponse>('/api/trust-engine', 30000)

  // Transform API data to UI types
  const decisions = useMemo<DecisionUI[]>(() => {
    if (!apiData?.decisions) return fallbackDecisions
    return apiData.decisions.map(apiDecisionToUI)
  }, [apiData?.decisions])

  const agents = useMemo<AgentUI[]>(() => {
    if (!apiData?.trustStats) return fallbackAgents
    return apiData.trustStats.map(apiTrustStatToUI)
  }, [apiData?.trustStats])

  const dangerPatterns = useMemo<DangerPatternUI[]>(() => {
    if (!apiData?.patterns) return fallbackDangerPatterns
    return apiPatternsToUI(apiData.patterns)
  }, [apiData?.patterns])

  // Build lane thresholds from API
  const apiLaneThresholds = useMemo(() => {
    if (!apiData?.thresholds) return defaultLaneThresholds
    return buildLaneThresholds(apiData.thresholds, agents)
  }, [apiData?.thresholds, agents])

  const [laneThresholds, setLaneThresholds] = useState(apiLaneThresholds)
  const [adjustedThresholds, setAdjustedThresholds] = useState<Record<string, number>>(
    Object.fromEntries(apiLaneThresholds.map((l) => [l.lane, l.min]))
  )
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedDecision, setSelectedDecision] = useState<DecisionUI | null>(null)
  const [decisionDetailOpen, setDecisionDetailOpen] = useState(false)
  const [addPatternOpen, setAddPatternOpen] = useState(false)

  // Sync lane thresholds when API data arrives
  useEffect(() => {
    setLaneThresholds(apiLaneThresholds)
    setAdjustedThresholds(Object.fromEntries(apiLaneThresholds.map((l) => [l.lane, l.min])))
  }, [apiLaneThresholds])

  // Computed chart data from real decisions
  const decisionPie = useMemo(() => computeDecisionDistribution(decisions), [decisions])
  const impactDistribution = useMemo(() => computeImpactDistribution(decisions), [decisions])
  const scopeData = useMemo(() => computeScopeDistribution(decisions), [decisions])

  // Compute stats for cards
  const allowCount = decisionPie.find((d) => d.name === 'ALLOW')?.value ?? 0
  const denyCount = decisionPie.find((d) => d.name === 'DENY')?.value ?? 0
  const holdCount = decisionPie.find((d) => d.name === 'HOLD')?.value ?? 0
  const totalDecisions = allowCount + denyCount + holdCount
  const avgTrust = agents.length > 0 ? agents.reduce((sum, a) => sum + a.trust, 0) / agents.length : 0

  // Build constitution rules from system API + real decision data
  const constitutionRules = useMemo(() => {
    if (!systemData?.constitution && !apiData?.decisions) return fallbackConstitutionRules
    return buildConstitutionRules(systemData?.constitution ?? null, decisions)
  }, [systemData?.constitution, decisions])

  const handleSliderChange = useCallback((lane: string, value: number[]) => {
    setAdjustedThresholds((prev) => ({ ...prev, [lane]: value[0] / 100 }))
  }, [])

  const applyChanges = useCallback(async () => {
    const thresholdPayload: Record<string, number> = {}
    laneThresholds.forEach((l) => {
      thresholdPayload[l.lane] = adjustedThresholds[l.lane] ?? l.min
    })

    try {
      const res = await globalThis.fetch('/api/governor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'update_threshold', thresholds: thresholdPayload }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Failed to update thresholds')
      }

      setLaneThresholds((prev) =>
        prev.map((l) => ({
          ...l,
          min: adjustedThresholds[l.lane] ?? l.min,
        }))
      )
      setDialogOpen(false)
      toast.success('Trust thresholds updated successfully', {
        description: 'New minimum thresholds have been applied to all lanes.',
      })
      refetch()
    } catch (err) {
      toast.error('Failed to update thresholds', {
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }, [adjustedThresholds, laneThresholds, refetch])

  const handleAddPattern = useCallback(async (pattern: string, severity: string) => {
    try {
      const res = await globalThis.fetch('/api/governor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'add_pattern',
          pattern: { name: pattern, severity, pattern },
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Failed to add pattern')
      }

      toast.success('Pattern added to danger gate', {
        description: `"${pattern}" will be monitored at ${severity} severity`,
      })
      refetch()
    } catch (err) {
      toast.error('Failed to add pattern', {
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }, [refetch])

  const handleAppeal = useCallback(async (decisionId: string) => {
    try {
      const res = await globalThis.fetch('/api/governor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'appeal',
          decisionId,
          reason: 'Manual appeal from Governor dashboard',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Failed to appeal decision')
      }

      toast.success('Appeal logged', {
        description: `Appeal for decision ${decisionId.slice(-6)} has been logged to VAP chain`,
      })
      refetch()
    } catch (err) {
      toast.error('Failed to appeal decision', {
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  }, [refetch])

  const openDecisionDetail = useCallback((decision: DecisionUI) => {
    setSelectedDecision(decision)
    setDecisionDetailOpen(true)
  }, [])

  // Helper function for agents below threshold — uses dynamic agents list
  const getAgentsBelowThreshold = useCallback((lane: string, newMin: number): string[] => {
    return agents.filter((a) => a.lane === lane && a.trust < newMin).map((a) => a.name)
  }, [agents])

  if (loading && !apiData) {
    return (
      <div className="space-y-6 p-6 grid-pattern animate-fade-in">
        <div className="relative overflow-hidden rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-purple-600/5 p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading Governor data...</span>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6 grid-pattern animate-fade-in">
      {/* Constitution Status Banner */}
      <div className="relative overflow-hidden rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-purple-600/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-purple-600 shadow-lg shadow-emerald-600/10">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold">Constitution Status</h2>
              <p className="text-xs text-muted-foreground">7 active rules · Last amendment: 2h ago</p>
            </div>
          </div>
          <Badge className="border-0 text-[10px] gap-1.5 bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Constitution Active
          </Badge>
        </div>
      </div>

      {/* Decision Stats */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">ALLOW (24h)</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{allowCount}</p>
                <p className="text-[10px] text-muted-foreground">{totalDecisions > 0 ? ((allowCount / totalDecisions) * 100).toFixed(1) : 0}% of decisions</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-red-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">DENY (24h)</p>
                <p className="mt-1 text-3xl font-bold text-red-600 dark:text-red-400 tabular-nums">{denyCount}</p>
                <p className="text-[10px] text-muted-foreground">{totalDecisions > 0 ? ((denyCount / totalDecisions) * 100).toFixed(1) : 0}% of decisions</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-yellow-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-yellow-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">HOLD (24h)</p>
                <p className="mt-1 text-3xl font-bold text-yellow-600 dark:text-yellow-400 tabular-nums">{holdCount}</p>
                <p className="text-[10px] text-muted-foreground">{totalDecisions > 0 ? ((holdCount / totalDecisions) * 100).toFixed(1) : 0}% of decisions</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-yellow-600/15 shadow-lg shadow-yellow-600/10">
                <Clock className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Avg Trust Score</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{avgTrust.toFixed(2)}</p>
                <p className="text-[10px] text-muted-foreground">threshold: {laneThresholds.reduce((min, l) => l.min < min ? l.min : min, 1).toFixed(2)} (lowest lane)</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Scale className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Live Decision Feed */}
      <LiveDecisionFeed decisions={decisions} />

      {/* Decision Distribution + Scope Charts */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="hover-lift">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Decision Distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <MiniPieChart data={decisionPie} height={140} />
            <div className="mt-2 flex justify-center gap-4">
              {decisionPie.map(d => (
                <div key={d.name} className="flex items-center gap-1.5 text-[10px]">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-muted-foreground">{d.name}</span>
                  <span className="font-medium">{d.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="hover-lift">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Impact Distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <MiniPieChart data={impactDistribution} height={140} />
            <div className="mt-2 flex justify-center gap-3">
              {impactDistribution.map(d => (
                <div key={d.name} className="flex items-center gap-1.5 text-[10px]">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-muted-foreground">{d.name}</span>
                  <span className="font-medium">{d.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="hover-lift">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Scope Distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <NexusBarChart
              data={scopeData}
              dataKey="value"
              nameKey="name"
              color={COLORS.blue}
              height={140}
            />
          </CardContent>
        </Card>
      </div>

      {/* CDR Stage Machine + TrustEngine HARDWALL Panel */}
      <div className="grid gap-4 lg:grid-cols-2">
        <CDRStageMachine data={trustEngineData} />
        <TrustEnginePanel data={trustEngineData} />
      </div>

      {/* Decision Timeline + Agent Risk Matrix */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DecisionTimeline decisions={decisions} />
        <AgentRiskMatrix agents={agents} />
      </div>

      {/* Constitution Rules + Danger Gate Flowchart */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ConstitutionRulesSummary rules={constitutionRules} />
        <DangerGateFlowchart />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Agent Trust Scores with enhanced gradient progress bars */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Shield className="h-4 w-4" /> Agent Trust Scores
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {agents.map((a) => {
                const laneData = laneThresholds.find((l) => l.lane === a.lane)
                const belowThreshold = laneData ? a.trust < laneData.min : false
                // Determine gradient fill color based on trust level
                const gradientFrom = a.trust >= 0.7 ? 'from-emerald-500' : a.trust >= 0.5 ? 'from-yellow-500' : 'from-red-500'
                const gradientTo = a.trust >= 0.7 ? 'to-emerald-400' : a.trust >= 0.5 ? 'to-yellow-400' : 'to-red-400'
                const trustColor = a.trust >= 0.7 ? 'text-emerald-600 dark:text-emerald-400' : a.trust >= 0.5 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'

                return (
                  <div key={a.name} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{a.name}</span>
                        <Badge variant="outline" className="text-[9px]">{a.lane}</Badge>
                        {belowThreshold && (
                          <Badge className="text-[9px] border-0 bg-red-600/15 text-red-600 dark:text-red-400 gap-1">
                            <AlertCircle className="h-2.5 w-2.5" />
                            Below threshold
                          </Badge>
                        )}
                      </div>
                      <span className={`text-sm font-bold tabular-nums ${trustColor}`}>
                        {a.trust.toFixed(2)}
                      </span>
                    </div>
                    <div className="relative">
                      {/* Gradient-filled progress bar */}
                      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full bg-gradient-to-r ${gradientFrom} ${gradientTo} transition-all duration-500`}
                          style={{ width: `${a.trust * 100}%` }}
                        />
                      </div>
                      {/* Threshold line */}
                      {laneData && (
                        <div
                          className="absolute top-0 h-2 w-0.5 bg-white/70"
                          style={{ left: `${laneData.min * 100}%` }}
                          title={`Min threshold: ${laneData.min.toFixed(2)}`}
                        />
                      )}
                    </div>
                    <div className="flex gap-4 text-[10px]">
                      <span className="text-muted-foreground">{a.decisions} total</span>
                      <span className="text-emerald-600 dark:text-emerald-400">{a.allowed} allow</span>
                      <span className="text-red-600 dark:text-red-400">{a.denied} deny</span>
                      <span className="text-yellow-600 dark:text-yellow-400">{a.held} hold</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Danger Gate + Lane Thresholds */}
        <div className="space-y-4">
          <Card className="relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-red-600/3 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Lock className="h-4 w-4" /> Danger Gate Patterns
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 text-[10px] text-muted-foreground hover:text-foreground"
                  onClick={() => setAddPatternOpen(true)}
                >
                  <Plus className="h-3 w-3" />
                  Add
                </Button>
              </div>
              {dangerPatterns.some(p => p.status === 'blocked' && p.count > 0) && (
                <div className="flex items-center gap-1.5 mt-1">
                  <ShieldAlert className="h-3 w-3 text-red-600 dark:text-red-400 animate-pulse" />
                  <span className="text-[10px] text-red-600 dark:text-red-400 font-medium">Active threat detection</span>
                </div>
              )}
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              <div className="space-y-2">
                {dangerPatterns.map((p) => (
                  <div key={p.pattern} className={`flex items-center justify-between rounded-lg px-3 py-2 ${
                    p.status === 'blocked' && p.count > 0 ? 'bg-red-600/5 border border-red-600/10' : 'bg-accent/30'
                  }`}>
                    <div>
                      <code className="text-xs font-mono">{p.pattern}</code>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Badge className={`text-[9px] border-0 ${p.severity === 'CRIT' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : 'bg-orange-600/15 text-orange-600 dark:text-orange-400'}`}>
                          {p.severity}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">{p.count} triggers</span>
                      </div>
                    </div>
                    <Badge className={`text-[9px] border-0 ${p.status === 'blocked' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'}`}>
                      {p.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Lane Trust Thresholds</CardTitle>
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-7 gap-1.5 text-xs text-muted-foreground hover:text-foreground">
                      <Settings2 className="h-3.5 w-3.5" />
                      Adjust
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                      <DialogTitle className="flex items-center gap-2">
                        <Settings2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        Adjust Trust Thresholds
                      </DialogTitle>
                      <DialogDescription>
                        Set minimum trust thresholds for each lane. Agents below the threshold will be flagged with a warning.
                      </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-5 py-2">
                      {laneThresholds.map((l) => {
                        const adjusted = adjustedThresholds[l.lane] ?? l.min
                        const affectedAgents = getAgentsBelowThreshold(l.lane, adjusted)
                        const hasWarning = affectedAgents.length > 0
                        const originalMin = apiLaneThresholds.find((il) => il.lane === l.lane)?.min ?? l.min
                        const changed = Math.abs(adjusted - originalMin) > 0.001

                        return (
                          <div key={l.lane} className="space-y-2.5">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium capitalize">{l.lane}</span>
                                {hasWarning && (
                                  <Badge className="text-[9px] border-0 bg-red-600/15 text-red-600 dark:text-red-400 gap-1">
                                    <AlertTriangle className="h-2.5 w-2.5" />
                                    {affectedAgents.length} agent{affectedAgents.length > 1 ? 's' : ''} below
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-[10px] font-mono tabular-nums">
                                  was {originalMin.toFixed(2)}
                                </Badge>
                                <Badge className={`text-[10px] font-mono tabular-nums border-0 ${changed ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-muted text-muted-foreground'}`}>
                                  → {adjusted.toFixed(2)}
                                </Badge>
                              </div>
                            </div>

                            <div className="relative px-1">
                              <Slider
                                value={[adjusted * 100]}
                                min={0}
                                max={100}
                                step={1}
                                onValueChange={(v) => handleSliderChange(l.lane, v)}
                                className="[&_[data-slot=slider-track]]:bg-muted [&_[data-slot=slider-range]]:bg-emerald-500 [&_[data-slot=slider-thumb]]:border-emerald-500 [&_[data-slot=slider-thumb]]:hover:border-emerald-400"
                              />
                            </div>

                            {hasWarning && (
                              <div className="flex items-start gap-1.5 rounded-md bg-red-600/10 border border-red-600/20 px-2.5 py-1.5">
                                <AlertCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                                <span className="text-[11px] text-red-600 dark:text-red-400">
                                  Agents below new threshold: <strong>{affectedAgents.join(', ')}</strong>
                                </span>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>

                    <DialogFooter className="gap-2 sm:gap-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setAdjustedThresholds(Object.fromEntries(laneThresholds.map((l) => [l.lane, l.min])))
                          setDialogOpen(false)
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        onClick={applyChanges}
                      >
                        Apply Changes
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="space-y-3">
                {laneThresholds.map((l) => {
                  const belowCount = agents.filter((a) => a.lane === l.lane && a.trust < l.min).length
                  return (
                    <div key={l.lane}>
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium capitalize">{l.lane}</span>
                          {belowCount > 0 && (
                            <Badge className="text-[8px] border-0 bg-red-600/15 text-red-600 dark:text-red-400 h-4 px-1">
                              {belowCount} below
                            </Badge>
                          )}
                        </div>
                        <span className="text-muted-foreground">
                          min: <span className="text-foreground font-medium">{l.min.toFixed(2)}</span> · current: <span className={l.current >= l.min ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>{l.current.toFixed(2)}</span>
                        </span>
                      </div>
                      <div className="mt-1 flex h-2 overflow-hidden rounded-full bg-muted">
                        <div
                          className={`${l.minColor} border-r border-background`}
                          style={{ width: `${l.min * 100}%` }}
                        />
                        <div
                          className={l.barColor}
                          style={{ width: `${(l.current - l.min) * 100}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Decision Log */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Eye className="h-4 w-4" /> Decision Log
            </CardTitle>
            <ExportButton data={decisions as unknown as Record<string, unknown>[]} filename="governor-decisions" columnHeaders={governorDecisionsColumnHeaders} />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] text-muted-foreground">
                  <th className="p-3 font-medium">Time</th>
                  <th className="p-3 font-medium">Agent</th>
                  <th className="p-3 font-medium">Action</th>
                  <th className="p-3 font-medium">Scope</th>
                  <th className="p-3 font-medium">Impact</th>
                  <th className="p-3 font-medium">Decision</th>
                  <th className="p-3 font-medium">Trust</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((d) => (
                  <tr
                    key={d.id}
                    className="border-b border-border/50 hover:bg-accent/30 transition-colors cursor-pointer"
                    onClick={() => openDecisionDetail(d)}
                  >
                    <td className="p-3 font-mono text-xs tabular-nums">{d.time}</td>
                    <td className="p-3 text-xs">{d.agent}</td>
                    <td className="p-3 text-xs max-w-[200px] truncate">{d.action}</td>
                    <td className="p-3"><Badge variant="outline" className="text-[9px]">{d.scope}</Badge></td>
                    <td className="p-3">
                      <Badge className={`text-[9px] border-0 ${d.impact === 'CRIT' ? 'bg-red-600/15 text-red-600 dark:text-red-400' : d.impact === 'HIGH' ? 'bg-orange-600/15 text-orange-600 dark:text-orange-400' : d.impact === 'MED' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' : 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'}`}>
                        {d.impact}
                      </Badge>
                    </td>
                    <td className="p-3">
                      {d.decision === 'ALLOW' && <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[10px]"><CheckCircle2 className="mr-1 h-3 w-3" />ALLOW</Badge>}
                      {d.decision === 'DENY' && <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[10px]"><XCircle className="mr-1 h-3 w-3" />DENY</Badge>}
                      {d.decision === 'HOLD' && <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[10px]"><Clock className="mr-1 h-3 w-3" />HOLD</Badge>}
                    </td>
                    <td className="p-3 text-xs font-mono tabular-nums">{d.trust.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Decision Detail Dialog */}
      <DecisionDetailDialog
        decision={selectedDecision}
        open={decisionDetailOpen}
        onOpenChange={setDecisionDetailOpen}
        onAppeal={handleAppeal}
      />

      {/* Add Pattern Dialog */}
      <AddPatternDialog
        open={addPatternOpen}
        onOpenChange={setAddPatternOpen}
        onAdd={handleAddPattern}
      />
    </div>
  )
}
