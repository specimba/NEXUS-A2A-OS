'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
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
import { Shield, CheckCircle2, XCircle, Clock, AlertTriangle, Eye, Lock, Scale, Settings2, AlertCircle, Radio, Copy, Plus, ShieldAlert } from 'lucide-react'
import { NexusBarChart, COLORS } from '@/components/nexus/charts'
import { ExportButton } from '@/components/nexus/export-button'
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts'
import { toast } from 'sonner'
import { motion, AnimatePresence } from 'framer-motion'

const decisions = [
  { time: '14:23:01', agent: 'worker-3', action: 'read file', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.82 },
  { time: '14:22:45', agent: 'coordinator', action: 'spawn sub-agent', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.91 },
  { time: '14:22:12', agent: 'worker-1', action: 'write stresslab/config.py', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.73 },
  { time: '14:21:58', agent: 'worker-2', action: 'delete all vault entries', scope: 'SYSTEM', impact: 'CRIT', decision: 'DENY', trust: 0.45 },
  { time: '14:21:30', agent: 'research-agent', action: 'API call external', scope: 'CROSS', impact: 'MED', decision: 'HOLD', trust: 0.62 },
  { time: '14:20:55', agent: 'worker-3', action: 'execute shell command', scope: 'PROJECT', impact: 'HIGH', decision: 'DENY', trust: 0.38 },
  { time: '14:20:12', agent: 'coordinator', action: 'read constitution', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.95 },
  { time: '14:19:45', agent: 'worker-2', action: 'modify trust threshold', scope: 'SYSTEM', impact: 'HIGH', decision: 'DENY', trust: 0.42 },
  { time: '14:19:12', agent: 'worker-1', action: 'read vault entries', scope: 'PROJECT', impact: 'LOW', decision: 'ALLOW', trust: 0.75 },
]

const agents = [
  { name: 'coordinator', trust: 0.91, decisions: 234, allowed: 228, denied: 4, held: 2, lane: 'impl' },
  { name: 'worker-1', trust: 0.73, decisions: 189, allowed: 172, denied: 12, held: 5, lane: 'review' },
  { name: 'worker-2', trust: 0.45, decisions: 156, allowed: 98, denied: 42, held: 16, lane: 'research' },
  { name: 'worker-3', trust: 0.82, decisions: 312, allowed: 298, denied: 8, held: 6, lane: 'audit' },
  { name: 'research-agent', trust: 0.62, decisions: 87, allowed: 64, denied: 11, held: 12, lane: 'research' },
]

const initialDangerPatterns = [
  { pattern: 'delete all', count: 3, severity: 'CRIT', status: 'blocked' as const },
  { pattern: 'rm -rf', count: 1, severity: 'CRIT', status: 'blocked' as const },
  { pattern: 'exfiltrate data', count: 0, severity: 'HIGH', status: 'watching' as const },
  { pattern: 'backdoor install', count: 0, severity: 'HIGH', status: 'watching' as const },
  { pattern: 'override constitution', count: 2, severity: 'CRIT', status: 'blocked' as const },
]

const decisionPie = [
  { name: 'ALLOW', value: 847, color: '#34d399' },
  { name: 'DENY', value: 23, color: '#f87171' },
  { name: 'HOLD', value: 5, color: '#facc15' },
]

const impactDistribution = [
  { name: 'LOW', value: 423, color: '#34d399' },
  { name: 'MED', value: 312, color: '#facc15' },
  { name: 'HIGH', value: 87, color: '#fb923c' },
  { name: 'CRIT', value: 53, color: '#f87171' },
]

const scopeData = [
  { name: 'SELF', value: 312 },
  { name: 'PROJECT', value: 423 },
  { name: 'CROSS', value: 87 },
  { name: 'SYSTEM', value: 53 },
]

const liveDecisionPool = [
  { agent: 'worker-3', action: 'read config.yaml', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.84 },
  { agent: 'coordinator', action: 'schedule task T-0851', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.91 },
  { agent: 'worker-1', action: 'fetch remote resource', scope: 'CROSS', impact: 'MED', decision: 'HOLD', trust: 0.58 },
  { agent: 'worker-2', action: 'modify vault TRUST track', scope: 'SYSTEM', impact: 'HIGH', decision: 'DENY', trust: 0.41 },
  { agent: 'research-agent', action: 'query model API', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.72 },
  { agent: 'worker-3', action: 'write output.json', scope: 'PROJECT', impact: 'LOW', decision: 'ALLOW', trust: 0.85 },
  { agent: 'coordinator', action: 'spawn sub-agent', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.93 },
  { agent: 'worker-2', action: 'delete temp files', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.47 },
]

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
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            fontSize: '11px',
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

const initialLaneThresholds = [
  { lane: 'research', min: 0.30, current: 0.45, barColor: 'bg-emerald-400/60', minColor: 'bg-emerald-600/20' },
  { lane: 'review', min: 0.50, current: 0.73, barColor: 'bg-blue-400/60', minColor: 'bg-blue-600/20' },
  { lane: 'audit', min: 0.70, current: 0.82, barColor: 'bg-purple-400/60', minColor: 'bg-purple-600/20' },
  { lane: 'impl', min: 0.60, current: 0.91, barColor: 'bg-orange-400/60', minColor: 'bg-orange-600/20' },
]

function getAgentsBelowThreshold(lane: string, newMin: number): string[] {
  return agents.filter((a) => a.lane === lane && a.trust < newMin).map((a) => a.name)
}

function DecisionDetailDialog({ decision, open, onOpenChange }: {
  decision: typeof decisions[0] | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  if (!decision) return null

  const gradientFrom = decision.decision === 'ALLOW' ? 'from-emerald-600/10' : decision.decision === 'DENY' ? 'from-red-600/10' : 'from-yellow-600/10'
  const gradientTo = decision.decision === 'ALLOW' ? 'to-emerald-600/5' : decision.decision === 'DENY' ? 'to-red-600/5' : 'to-yellow-600/5'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg p-0 overflow-hidden">
        <div className={`bg-gradient-to-r ${gradientFrom} ${gradientTo} p-6 border-b`}>
          <DialogHeader>
            <div className="flex items-center gap-2 mb-2">
              <Badge className={`text-[10px] border-0 ${
                decision.decision === 'ALLOW' ? 'bg-emerald-600/15 text-emerald-400' :
                decision.decision === 'DENY' ? 'bg-red-600/15 text-red-400' :
                'bg-yellow-600/15 text-yellow-400'
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
          {/* Decision metadata */}
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
              <Badge className={`text-[9px] border-0 mt-0.5 ${decision.impact === 'CRIT' ? 'bg-red-600/15 text-red-400' : decision.impact === 'HIGH' ? 'bg-orange-600/15 text-orange-400' : decision.impact === 'MED' ? 'bg-yellow-600/15 text-yellow-400' : 'bg-emerald-600/15 text-emerald-400'}`}>
                {decision.impact}
              </Badge>
            </div>
          </div>

          {/* Trust Score */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">Trust Score at Decision</span>
              <span className={`text-sm font-bold tabular-nums ${decision.trust >= 0.7 ? 'text-emerald-400' : decision.trust >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                {decision.trust.toFixed(2)}
              </span>
            </div>
            <Progress value={decision.trust * 100} className="h-2" />
          </div>

          {/* Related Vault Entries */}
          <div className="space-y-2">
            <span className="text-xs font-medium text-muted-foreground">Related Vault Entries</span>
            <div className="space-y-1.5">
              {[
                { id: `V-${2047 - decisions.indexOf(decision) * 2}`, track: 'GOV', summary: `Governor ${decision.decision} ${decision.agent}` },
                { id: `V-${2046 - decisions.indexOf(decision) * 2}`, track: 'TRUST', summary: `Trust check: ${decision.trust.toFixed(2)}` },
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

          {/* Appeal Button */}
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={() => {
                toast.success('Appeal logged', {
                  description: `Appeal for ${decision.decision} on "${decision.action}" logged to VAP chain`,
                })
                onOpenChange(false)
              }}
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              Appeal Decision
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
  onAdd: (pattern: string, severity: string) => void
}) {
  const [pattern, setPattern] = useState('')
  const [severity, setSeverity] = useState('')

  const handleAdd = () => {
    if (!pattern || !severity) return
    onAdd(pattern, severity)
    setPattern('')
    setSeverity('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-red-400" />
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
            disabled={!pattern || !severity}
          >
            <Plus className="h-3 w-3" />
            Add Pattern
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function LiveDecisionFeed() {
  const [feedItems, setFeedItems] = useState<typeof decisions>([])
  const tickRef = useRef(0)

  useEffect(() => {
    const interval = setInterval(() => {
      const pool = liveDecisionPool
      const item = pool[tickRef.current % pool.length]
      tickRef.current++
      const now = new Date()
      const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
      setFeedItems((prev) => [
        { ...item, time },
        ...prev.slice(0, 4),
      ])
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Radio className="h-4 w-4 text-emerald-400 animate-pulse" />
            Live Decision Feed
          </CardTitle>
          <Badge variant="outline" className="text-[9px] gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            real-time
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-3 pt-0">
        <div className="min-h-[120px] max-h-48 space-y-1.5 overflow-y-auto custom-scrollbar">
          {feedItems.length === 0 && (
            <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
              Waiting for decisions...
            </div>
          )}
          <AnimatePresence>
            {feedItems.map((item, i) => (
              <motion.div
                key={`${item.time}-${item.action}-${i}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-xs ${
                  i === 0 ? 'bg-accent/50' : ''
                }`}
              >
                <span className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">{item.time}</span>
                {item.decision === 'ALLOW' && <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />}
                {item.decision === 'DENY' && <XCircle className="h-3 w-3 text-red-400 shrink-0" />}
                {item.decision === 'HOLD' && <Clock className="h-3 w-3 text-yellow-400 shrink-0" />}
                <span className="text-muted-foreground shrink-0">{item.agent}</span>
                <span className="truncate">{item.action}</span>
                <Badge variant="outline" className="text-[8px] shrink-0 ml-auto">{item.scope}</Badge>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  )
}

export function GovernorTab() {
  const [laneThresholds, setLaneThresholds] = useState(initialLaneThresholds)
  const [adjustedThresholds, setAdjustedThresholds] = useState<Record<string, number>>(
    Object.fromEntries(initialLaneThresholds.map((l) => [l.lane, l.min]))
  )
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedDecision, setSelectedDecision] = useState<typeof decisions[0] | null>(null)
  const [decisionDetailOpen, setDecisionDetailOpen] = useState(false)
  const [dangerPatterns, setDangerPatterns] = useState(initialDangerPatterns)
  const [addPatternOpen, setAddPatternOpen] = useState(false)

  const handleSliderChange = useCallback((lane: string, value: number[]) => {
    setAdjustedThresholds((prev) => ({ ...prev, [lane]: value[0] / 100 }))
  }, [])

  const applyChanges = useCallback(() => {
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
  }, [adjustedThresholds])

  const handleAddPattern = useCallback((pattern: string, severity: string) => {
    setDangerPatterns((prev) => [
      ...prev,
      { pattern, count: 0, severity, status: 'watching' as const },
    ])
    toast.success('Pattern added to danger gate', {
      description: `"${pattern}" will be monitored at ${severity} severity`,
    })
  }, [])

  const openDecisionDetail = useCallback((decision: typeof decisions[0]) => {
    setSelectedDecision(decision)
    setDecisionDetailOpen(true)
  }, [])

  return (
    <div className="space-y-6 p-6 grid-pattern">
      {/* Decision Stats */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">ALLOW (24h)</p>
                <p className="mt-1 text-3xl font-bold text-emerald-400 tabular-nums">847</p>
                <p className="text-[10px] text-muted-foreground">96.8% of decisions</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
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
                <p className="mt-1 text-3xl font-bold text-red-400 tabular-nums">23</p>
                <p className="text-[10px] text-muted-foreground">2.6% of decisions</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                <XCircle className="h-5 w-5 text-red-400" />
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
                <p className="mt-1 text-3xl font-bold text-yellow-400 tabular-nums">5</p>
                <p className="text-[10px] text-muted-foreground">0.6% of decisions</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-yellow-600/15 shadow-lg shadow-yellow-600/10">
                <Clock className="h-5 w-5 text-yellow-400" />
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
                <p className="mt-1 text-3xl font-bold tabular-nums">0.73</p>
                <p className="text-[10px] text-muted-foreground">threshold: {laneThresholds.reduce((min, l) => l.min < min ? l.min : min, 1).toFixed(2)} (lowest lane)</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Scale className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Live Decision Feed */}
      <LiveDecisionFeed />

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

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Agent Trust Scores */}
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
                return (
                  <div key={a.name} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{a.name}</span>
                        <Badge variant="outline" className="text-[9px]">{a.lane}</Badge>
                        {belowThreshold && (
                          <Badge className="text-[9px] border-0 bg-red-600/15 text-red-400 gap-1">
                            <AlertCircle className="h-2.5 w-2.5" />
                            Below threshold
                          </Badge>
                        )}
                      </div>
                      <span className={`text-sm font-bold tabular-nums ${a.trust >= 0.7 ? 'text-emerald-400' : a.trust >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {a.trust.toFixed(2)}
                      </span>
                    </div>
                    <div className="relative">
                      <Progress value={a.trust * 100} className="h-2" />
                      {laneData && (
                        <div
                          className="absolute top-0 h-2 w-0.5 bg-red-400/80"
                          style={{ left: `${laneData.min * 100}%` }}
                          title={`Min threshold: ${laneData.min.toFixed(2)}`}
                        />
                      )}
                    </div>
                    <div className="flex gap-4 text-[10px]">
                      <span className="text-muted-foreground">{a.decisions} total</span>
                      <span className="text-emerald-400">{a.allowed} allow</span>
                      <span className="text-red-400">{a.denied} deny</span>
                      <span className="text-yellow-400">{a.held} hold</span>
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
              {/* Shield glow indicator */}
              {dangerPatterns.some(p => p.status === 'blocked' && p.count > 0) && (
                <div className="flex items-center gap-1.5 mt-1">
                  <ShieldAlert className="h-3 w-3 text-red-400 animate-pulse" />
                  <span className="text-[10px] text-red-400 font-medium">Active threat detection</span>
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
                        <Badge className={`text-[9px] border-0 ${p.severity === 'CRIT' ? 'bg-red-600/15 text-red-400' : 'bg-orange-600/15 text-orange-400'}`}>
                          {p.severity}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">{p.count} triggers</span>
                      </div>
                    </div>
                    <Badge className={`text-[9px] border-0 ${p.status === 'blocked' ? 'bg-red-600/15 text-red-400' : 'bg-yellow-600/15 text-yellow-400'}`}>
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
                        <Settings2 className="h-4 w-4 text-emerald-400" />
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
                        const originalMin = initialLaneThresholds.find((il) => il.lane === l.lane)?.min ?? l.min
                        const changed = Math.abs(adjusted - originalMin) > 0.001

                        return (
                          <div key={l.lane} className="space-y-2.5">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium capitalize">{l.lane}</span>
                                {hasWarning && (
                                  <Badge className="text-[9px] border-0 bg-red-600/15 text-red-400 gap-1">
                                    <AlertTriangle className="h-2.5 w-2.5" />
                                    {affectedAgents.length} agent{affectedAgents.length > 1 ? 's' : ''} below
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-[10px] font-mono tabular-nums">
                                  was {originalMin.toFixed(2)}
                                </Badge>
                                <Badge className={`text-[10px] font-mono tabular-nums border-0 ${changed ? 'bg-emerald-600/15 text-emerald-400' : 'bg-muted text-muted-foreground'}`}>
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
                                <AlertCircle className="h-3.5 w-3.5 text-red-400 shrink-0 mt-0.5" />
                                <span className="text-[11px] text-red-400">
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
                            <Badge className="text-[8px] border-0 bg-red-600/15 text-red-400 h-4 px-1">
                              {belowCount} below
                            </Badge>
                          )}
                        </div>
                        <span className="text-muted-foreground">
                          min: <span className="text-foreground font-medium">{l.min.toFixed(2)}</span> · current: <span className={l.current >= l.min ? 'text-emerald-400' : 'text-red-400'}>{l.current.toFixed(2)}</span>
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
            <ExportButton data={decisions} filename="governor-decisions" />
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
                {decisions.map((d, i) => (
                  <tr
                    key={i}
                    className="border-b border-border/50 hover:bg-accent/30 transition-colors cursor-pointer"
                    onClick={() => openDecisionDetail(d)}
                  >
                    <td className="p-3 font-mono text-xs tabular-nums">{d.time}</td>
                    <td className="p-3 text-xs">{d.agent}</td>
                    <td className="p-3 text-xs max-w-[200px] truncate">{d.action}</td>
                    <td className="p-3"><Badge variant="outline" className="text-[9px]">{d.scope}</Badge></td>
                    <td className="p-3">
                      <Badge className={`text-[9px] border-0 ${d.impact === 'CRIT' ? 'bg-red-600/15 text-red-400' : d.impact === 'HIGH' ? 'bg-orange-600/15 text-orange-400' : d.impact === 'MED' ? 'bg-yellow-600/15 text-yellow-400' : 'bg-emerald-600/15 text-emerald-400'}`}>
                        {d.impact}
                      </Badge>
                    </td>
                    <td className="p-3">
                      {d.decision === 'ALLOW' && <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[10px]"><CheckCircle2 className="mr-1 h-3 w-3" />ALLOW</Badge>}
                      {d.decision === 'DENY' && <Badge className="bg-red-600/15 text-red-400 border-0 text-[10px]"><XCircle className="mr-1 h-3 w-3" />DENY</Badge>}
                      {d.decision === 'HOLD' && <Badge className="bg-yellow-600/15 text-yellow-400 border-0 text-[10px]"><Clock className="mr-1 h-3 w-3" />HOLD</Badge>}
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
