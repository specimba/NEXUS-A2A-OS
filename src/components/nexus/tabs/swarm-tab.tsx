'use client'

import { useState, useMemo, useCallback, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Bug,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Users,
  Cpu,
  AlertTriangle,
  Play,
  ArrowRightLeft,
  Trash2,
  Zap,
  Gauge,
  Timer,
  TrendingUp,
  BarChart3,
  Wifi,
  WifiOff,
  Radio,
  RotateCcw,
  Plus,
  ThumbsUp,
  ThumbsDown,
  ShieldAlert,
  Sparkles,
  UserPlus,
  RefreshCw,
  Network,
  ArrowUpDown,
  ChevronUp,
  ChevronDown,
} from 'lucide-react'
import { NexusBarChart, MiniAreaChart, COLORS } from '@/components/nexus/charts'
import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from 'recharts'
import { ExportButton } from '@/components/nexus/export-button'
import { toast } from 'sonner'
import { useSwarmWS } from '@/hooks/use-swarm-ws'
import { useApiData } from '@/hooks/use-api-data'

// Worker status export data with meaningful column names
const workerStatusColumnHeaders: Record<string, string> = {
  id: 'Worker ID',
  status: 'Status',
  task: 'Current Task',
  domain: 'Domain',
  progress: 'Progress (%)',
  tokens: 'Tokens Consumed',
  uptime: 'Uptime',
}

const taskHistoryColumnHeaders: Record<string, string> = {
  id: 'Task ID',
  worker: 'Worker',
  result: 'Result',
  duration: 'Duration',
  tokens: 'Tokens',
}

const WORKER_TYPES = ['foreman', 'researcher', 'coder', 'auditor', 'reviewer']
const WORKER_DOMAINS = ['code', 'research', 'cyber', 'ai_safety', 'compbio', 'pharmacology', 'general']

interface Worker {
  id: string
  name: string
  status: string
  task: string | null
  domain: string | null
  progress: number
  tokens: number
  uptime: string
  trustScore: number
  tasksDone: number
  tasksFailed: number
}

interface SwarmApiResponse {
  workers: {
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
    recentActivity: number
  }[]
  stats: {
    totalWorkers: number
    busyWorkers: number
    idleWorkers: number
    errorWorkers: number
    offlineWorkers: number
    totalTasks: number
    avgTrust: number
  }
}

// Fallback task queue (not from API)
const taskQueue = [
  { id: 'T-0850', domain: 'ai_safety', priority: 'high', status: 'queued', submittedBy: 'coordinator' },
  { id: 'T-0851', domain: 'compbio', priority: 'medium', status: 'queued', submittedBy: 'coordinator' },
  { id: 'T-0852', domain: 'pharmacology', priority: 'low', status: 'queued', submittedBy: 'research-agent' },
  { id: 'T-0853', domain: 'code', priority: 'high', status: 'queued', submittedBy: 'coordinator' },
]

// Fallback recent completed
const recentCompleted = [
  { id: 'T-0847', worker: 'worker-3', result: 'success', duration: '14s', tokens: 3420 },
  { id: 'T-0845', worker: 'worker-1', result: 'success', duration: '22s', tokens: 5100 },
  { id: 'T-0844', worker: 'worker-3', result: 'failure', duration: '8s', tokens: 1280 },
  { id: 'T-0843', worker: 'worker-4', result: 'success', duration: '3s', tokens: 640 },
  { id: 'T-0842', worker: 'worker-1', result: 'success', duration: '18s', tokens: 4200 },
]

function formatUptime(lastActive: string): string {
  const now = new Date()
  const last = new Date(lastActive)
  const diffMs = now.getTime() - last.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m`
  const diffHours = Math.floor(diffMins / 60)
  const remainMins = diffMins % 60
  if (diffHours < 24) return `${diffHours}h ${remainMins}m`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ${diffHours % 24}h`
}

function getStatusDisplay(status: string): { icon: typeof Loader2; bgClass: string; textClass: string; badgeClass: string; label: string } {
  switch (status) {
    case 'busy':
      return {
        icon: Loader2,
        bgClass: 'bg-emerald-600/15 shadow-lg shadow-emerald-600/10',
        textClass: 'text-emerald-600 dark:text-emerald-400',
        badgeClass: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400',
        label: 'Executing task',
      }
    case 'error':
      return {
        icon: Bug,
        bgClass: 'bg-red-600/15 shadow-lg shadow-red-600/10',
        textClass: 'text-red-600 dark:text-red-400',
        badgeClass: 'bg-red-600/15 text-red-600 dark:text-red-400',
        label: 'Error state',
      }
    case 'offline':
      return {
        icon: WifiOff,
        bgClass: 'bg-muted',
        textClass: 'text-muted-foreground',
        badgeClass: 'bg-muted text-muted-foreground',
        label: 'Offline',
      }
    default: // idle
      return {
        icon: Clock,
        bgClass: 'bg-muted',
        textClass: 'text-muted-foreground',
        badgeClass: 'bg-muted text-muted-foreground',
        label: 'Available for assignment',
      }
  }
}

function getWorkerCardStyle(status: string): string {
  switch (status) {
    case 'busy':
      return 'border-emerald-600/20 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent hover:border-emerald-600/40'
    case 'error':
      return 'border-red-600/30 bg-gradient-to-br from-red-600/10 via-red-600/5 to-transparent hover:border-red-600/50 pulse-border'
    case 'offline':
      return 'border-border/50 bg-gradient-to-br from-muted/10 via-transparent to-transparent opacity-60'
    default: // idle
      return 'border-border bg-gradient-to-br from-muted/20 via-transparent to-transparent hover:border-border/80'
  }
}

// ─── Shared API helper with rate-limit awareness ──────────────────────────────

async function callSwarmApi<T = { message?: string }>(
  action: string,
  payload: Record<string, unknown>,
): Promise<{ ok: boolean; data?: T; status: number }> {
  try {
    const res = await fetch('/api/swarm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...payload }),
    })

    if (res.status === 429) {
      toast.warning('Rate limited', {
        description: 'Too many requests — please wait a moment before trying again.',
        duration: 5000,
        icon: <ShieldAlert className="h-4 w-4" />,
      })
      return { ok: false, status: 429 }
    }

    const json = await res.json()

    if (res.ok) {
      return { ok: true, data: json as T, status: res.status }
    } else {
      toast.error(`Action failed: ${action.replace(/_/g, ' ')}`, {
        description: json.error || 'Unknown error occurred',
      })
      return { ok: false, status: res.status }
    }
  } catch {
    toast.error('Network error', {
      description: 'Could not reach the Swarm API. Check your connection.',
    })
    return { ok: false, status: 0 }
  }
}

// ─── Spawn Worker Dialog ──────────────────────────────────────────────────────

function SpawnWorkerDialog({
  open,
  onOpenChange,
  onSpawned,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSpawned: () => void
}) {
  const [name, setName] = useState('')
  const [type, setType] = useState('')
  const [domain, setDomain] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!name.trim() || !type) {
      toast.error('Missing fields', { description: 'Name and Type are required.' })
      return
    }
    setSubmitting(true)
    const result = await callSwarmApi('spawn_worker', {
      name: name.trim(),
      type,
      domain: domain || 'general',
    })
    setSubmitting(false)

    if (result.ok) {
      toast.success('Worker spawned', {
        description: result.data?.message || `${name} is now online.`,
        icon: <UserPlus className="h-4 w-4" />,
      })
      onSpawned()
      onOpenChange(false)
      setName('')
      setType('')
      setDomain('')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card border-border/60">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-lg shadow-emerald-600/20">
              <UserPlus className="h-5 w-5 text-white" />
            </div>
            <div>
              <DialogTitle className="text-base">Spawn New Worker</DialogTitle>
              <DialogDescription className="text-xs">
                Create a new worker node in the swarm pool
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Gradient divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />

          <div className="space-y-2">
            <Label htmlFor="spawn-name" className="text-xs font-medium">Worker Name</Label>
            <Input
              id="spawn-name"
              placeholder="e.g. worker-6, research-agent-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-sm"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-medium">Worker Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Select type..." />
              </SelectTrigger>
              <SelectContent>
                {WORKER_TYPES.map(t => (
                  <SelectItem key={t} value={t} className="text-sm">
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-medium">Domain</Label>
            <Select value={domain} onValueChange={setDomain}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Select domain (optional)..." />
              </SelectTrigger>
              <SelectContent>
                {WORKER_DOMAINS.map(d => (
                  <SelectItem key={d} value={d} className="text-sm">
                    {d.charAt(0).toUpperCase() + d.slice(1).replace('_', ' ')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Info banner */}
          <div className="rounded-lg border border-emerald-600/20 bg-emerald-600/5 p-3">
            <div className="flex items-start gap-2">
              <Sparkles className="h-4 w-4 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
              <div className="text-[11px] text-muted-foreground leading-relaxed">
                New workers start with <span className="text-emerald-600 dark:text-emerald-400 font-medium">0.50 trust score</span> in idle status.
                The maximum active worker limit is enforced by the NEXUS constitution.
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            className="gap-1.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white border-0"
            onClick={handleSubmit}
            disabled={submitting || !name.trim() || !type}
          >
            {submitting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Plus className="h-3.5 w-3.5" />
            )}
            {submitting ? 'Spawning...' : 'Spawn Worker'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Reassign Task Dialog ─────────────────────────────────────────────────────

function ReassignTaskDialog({
  worker,
  open,
  onOpenChange,
  onReassigned,
}: {
  worker: Worker | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onReassigned: () => void
}) {
  const [newDomain, setNewDomain] = useState('')
  const [newTask, setNewTask] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Reset form when worker changes
  const prevWorkerRef = useRef<string | null>(null)
  if (worker?.id !== prevWorkerRef.current) {
    prevWorkerRef.current = worker?.id ?? null
    if (worker) {
      setNewDomain(worker.domain || '')
      setNewTask('')
    }
  }

  const handleSubmit = async () => {
    if (!worker) return
    setSubmitting(true)
    const result = await callSwarmApi('reassign_task', {
      workerId: worker.id,
      newDomain: newDomain || undefined,
      newTask: newTask.trim() || undefined,
    })
    setSubmitting(false)

    if (result.ok) {
      toast.success('Task reassigned', {
        description: result.data?.message || `New task assigned to ${worker.name}`,
        icon: <ArrowRightLeft className="h-4 w-4" />,
      })
      onReassigned()
      onOpenChange(false)
    }
  }

  if (!worker) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card border-border/60">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-600/20">
              <ArrowRightLeft className="h-5 w-5 text-white" />
            </div>
            <div>
              <DialogTitle className="text-base">Reassign Task</DialogTitle>
              <DialogDescription className="text-xs">
                Assign a new task and domain to {worker.name}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Gradient divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-blue-600/40 to-transparent" />

          <div className="space-y-2">
            <Label className="text-xs font-medium">New Domain</Label>
            <Select value={newDomain} onValueChange={setNewDomain}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Select domain..." />
              </SelectTrigger>
              <SelectContent>
                {WORKER_DOMAINS.map(d => (
                  <SelectItem key={d} value={d} className="text-sm">
                    {d.charAt(0).toUpperCase() + d.slice(1).replace('_', ' ')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="reassign-task" className="text-xs font-medium">New Task ID</Label>
            <Input
              id="reassign-task"
              placeholder="e.g. T-0854 or leave empty for auto-assign"
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
              className="text-sm font-mono"
            />
          </div>

          {/* Current state info */}
          <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">Current Assignment</p>
            <div className="flex items-center gap-2 text-xs">
              {worker.domain ? (
                <Badge variant="outline" className="text-[9px]">{worker.domain}</Badge>
              ) : (
                <span className="text-muted-foreground">No domain</span>
              )}
              {worker.task && (
                <>
                  <span className="text-muted-foreground">→</span>
                  <span className="font-mono">{worker.task}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            className="gap-1.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white border-0"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ArrowRightLeft className="h-3.5 w-3.5" />
            )}
            {submitting ? 'Reassigning...' : 'Reassign'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Worker Detail Dialog ─────────────────────────────────────────────────────

function WorkerDetailDialog({
  worker,
  open,
  onOpenChange,
  onTerminate,
  onRestart,
  onReassign,
  onUpdateTrust,
  actionLoading,
}: {
  worker: Worker | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onTerminate: (workerId: string) => Promise<void>
  onRestart: (workerId: string) => Promise<void>
  onReassign: (workerId: string) => void
  onUpdateTrust: (workerId: string, delta: number, reason: string) => Promise<void>
  actionLoading: string | null
}) {
  if (!worker) return null

  const isIdle = worker.status === 'idle'
  const isError = worker.status === 'error'
  const isOffline = worker.status === 'offline'
  const canRestart = isError || isOffline
  const statusDisplay = getStatusDisplay(worker.status)
  const StatusIcon = statusDisplay.icon
  const isLoading = actionLoading === worker.id

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg bg-card border-border/60">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${statusDisplay.bgClass}`}>
              <StatusIcon className={`h-5 w-5 ${statusDisplay.textClass} ${worker.status === 'busy' ? 'animate-spin' : ''}`} />
            </div>
            <div>
              <DialogTitle className="text-base">{worker.name}</DialogTitle>
              <DialogDescription className="text-xs">
                Worker detail and task history
              </DialogDescription>
            </div>
            <Badge
              className={`ml-auto text-[10px] border-0 ${statusDisplay.badgeClass}`}
            >
              {worker.status}
            </Badge>
          </div>
        </DialogHeader>

        <div className="space-y-4">
          {/* Gradient divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-emerald-600/30 to-transparent" />

          {/* Worker Info Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Worker ID</p>
              <p className="mt-0.5 text-sm font-mono font-medium">{worker.id}</p>
            </div>
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Status</p>
              <p className={`mt-0.5 text-sm font-medium ${statusDisplay.textClass}`}>
                {statusDisplay.label}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Domain</p>
              <p className="mt-0.5 text-sm font-medium">
                {worker.domain ? (
                  <Badge variant="outline" className="text-[9px]">{worker.domain}</Badge>
                ) : '—'}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Trust Score</p>
              <div className="mt-0.5 flex items-center gap-2">
                <p className="text-sm font-bold tabular-nums">{worker.trustScore.toFixed(2)}</p>
                {/* Trust score color indicator */}
                <div className={`h-1.5 w-8 rounded-full ${
                  worker.trustScore >= 0.8 ? 'bg-emerald-500' :
                  worker.trustScore >= 0.5 ? 'bg-yellow-500' :
                  'bg-red-500'
                }`} />
              </div>
            </div>
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Tokens Consumed</p>
              <p className="mt-0.5 text-sm font-bold tabular-nums">
                {worker.tokens > 0 ? worker.tokens.toLocaleString() : '0'}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Tasks Done / Failed</p>
              <p className="mt-0.5 text-sm tabular-nums">
                <span className="text-emerald-600 dark:text-emerald-400">{worker.tasksDone}</span>
                {' / '}
                <span className="text-red-600 dark:text-red-400">{worker.tasksFailed}</span>
              </p>
            </div>
          </div>

          {/* Trust Adjustment Panel */}
          <div className="rounded-lg border border-border/50 bg-gradient-to-r from-amber-600/5 via-transparent to-amber-600/5 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <p className="text-[10px] uppercase tracking-wider text-amber-600 dark:text-amber-400">Trust Adjustment</p>
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1 text-[10px] border-red-600/30 text-red-600 dark:text-red-400 hover:bg-red-600/10 dark:hover:text-red-300"
                  onClick={() => onUpdateTrust(worker.id, -0.05, `Manual adjustment from worker detail: -0.05`)}
                  disabled={isLoading}
                >
                  {actionLoading === `trust-down-${worker.id}` ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <ThumbsDown className="h-3 w-3" />
                  )}
                  -0.05
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1 text-[10px] border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10 dark:hover:text-emerald-300"
                  onClick={() => onUpdateTrust(worker.id, 0.05, `Manual adjustment from worker detail: +0.05`)}
                  disabled={isLoading}
                >
                  {actionLoading === `trust-up-${worker.id}` ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <ThumbsUp className="h-3 w-3" />
                  )}
                  +0.05
                </Button>
              </div>
            </div>
            <p className="mt-1.5 text-[10px] text-muted-foreground">
              Current: <span className="font-bold tabular-nums">{worker.trustScore.toFixed(2)}</span>
              {' · '}Range: [0.00 – 1.00]
              {' · '}Lane thresholds: research ≥ 0.75, audit ≥ 0.85
            </p>
          </div>

          {/* Error details for error workers */}
          {isError && (
            <div className="rounded-lg border border-red-600/20 bg-red-600/5 p-3">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                <p className="text-[10px] uppercase tracking-wider text-red-600 dark:text-red-400">Error Details</p>
              </div>
              <p className="text-xs text-red-300 leading-relaxed">
                Worker encountered an error. Last task may have failed.
                Error: &quot;Rate limit exceeded — retry after 60s or reassign to another worker.&quot;
              </p>
              <div className="mt-2 flex items-center gap-2">
                <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">E-RATE-429</Badge>
                <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">Auto-retry: disabled</Badge>
              </div>
            </div>
          )}

          {/* Offline info */}
          {isOffline && (
            <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
              <div className="flex items-center gap-2 mb-2">
                <WifiOff className="h-4 w-4 text-muted-foreground" />
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Offline</p>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                This worker is offline. Use &quot;Restart Worker&quot; to bring it back online, or &quot;Terminate&quot; to remove it permanently.
              </p>
            </div>
          )}

          {/* Idle workers assignment info */}
          {isIdle && (
            <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Play className="h-4 w-4 text-muted-foreground" />
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Availability</p>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                This worker is available for assignment. Use &quot;Reassign Task&quot; to assign a queued task.
              </p>
              <div className="mt-2">
                <p className="text-[10px] text-muted-foreground mb-1.5">Supported domains:</p>
                <div className="flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="text-[9px]">code</Badge>
                  <Badge variant="outline" className="text-[9px]">research</Badge>
                  <Badge variant="outline" className="text-[9px]">cyber</Badge>
                  <Badge variant="outline" className="text-[9px]">ai_safety</Badge>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 flex-wrap">
          {canRestart && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 border-amber-600/30 text-amber-600 dark:text-amber-400 hover:bg-amber-600/10 dark:hover:text-amber-300"
              onClick={() => onRestart(worker.id)}
              disabled={isLoading}
            >
              {actionLoading === `restart-${worker.id}` ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RotateCcw className="h-3.5 w-3.5" />
              )}
              Restart Worker
            </Button>
          )}
          {(isIdle || !isOffline) && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => {
                onReassign(worker.id)
                onOpenChange(false)
              }}
              disabled={isLoading}
            >
              <ArrowRightLeft className="h-3.5 w-3.5" />
              Reassign Task
            </Button>
          )}
          {worker.status !== 'offline' && (
            <Button
              variant="destructive"
              size="sm"
              className="gap-1.5"
              onClick={async () => {
                await onTerminate(worker.id)
                onOpenChange(false)
              }}
              disabled={isLoading}
            >
              {actionLoading === `terminate-${worker.id}` ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
              Terminate Worker
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Priority Helpers ──────────────────────────────────────────────────────────

const PRIORITY_ORDER: Record<string, number> = { high: 3, medium: 2, low: 1 }

// Deterministic worker performance data (avoids Math.random in render)
const workerPerformanceData = [
  { name: 'w-3', value: 18 },
  { name: 'w-1', value: 12 },
  { name: 'coord', value: 15 },
  { name: 'w-2', value: 7 },
  { name: 'res', value: 9 },
]

const workerPerformanceRows = [
  { id: 'w-3', name: 'w-3', tasks: 18, avgTime: 312, errRate: 1.2 },
  { id: 'w-1', name: 'w-1', tasks: 12, avgTime: 245, errRate: 0.8 },
  { id: 'coord', name: 'coord', tasks: 15, avgTime: 189, errRate: 2.1 },
  { id: 'w-2', name: 'w-2', tasks: 7, avgTime: 478, errRate: 4.5 },
]

function getPriorityBadge(priority: string) {
  switch (priority) {
    case 'high':
      return <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">HIGH</Badge>
    case 'medium':
      return <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[9px]">MED</Badge>
    case 'low':
      return <Badge className="bg-blue-600/15 text-blue-600 dark:text-blue-400 border-0 text-[9px]">LOW</Badge>
    default:
      return <Badge variant="outline" className="text-[9px]">{priority}</Badge>
  }
}

// ─── Reorder Priority Dialog ──────────────────────────────────────────────────

function ReorderPriorityDialog({
  open,
  onOpenChange,
  tasks,
  onReorder,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  tasks: { id: string; domain: string; priority: string; submittedBy: string }[]
  onReorder: (taskId: string, newPriority: string) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card border-border/60">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-red-600 shadow-lg shadow-orange-600/20">
              <ArrowUpDown className="h-5 w-5 text-white" />
            </div>
            <div>
              <DialogTitle className="text-base">Reorder Task Priorities</DialogTitle>
              <DialogDescription className="text-xs">
                Change the priority level of queued tasks
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <div className="space-y-3 pt-2 max-h-[300px] overflow-y-auto custom-scrollbar">
          {tasks.map((t) => (
            <div key={t.id} className="flex items-center gap-3 rounded-lg border border-border/50 bg-muted/30 px-3 py-2.5">
              <span className="font-mono text-xs font-medium w-16 shrink-0">{t.id}</span>
              <Badge variant="outline" className="text-[9px] shrink-0">{t.domain}</Badge>
              <span className="flex-1" />
              <div className="flex items-center gap-1">
                {(['high', 'medium', 'low'] as const).map((p) => (
                  <Button
                    key={p}
                    variant={t.priority === p ? 'default' : 'outline'}
                    size="sm"
                    className={`h-6 text-[9px] px-2 ${
                      t.priority === p
                        ? p === 'high'
                          ? 'bg-red-600 hover:bg-red-500 text-white border-0'
                          : p === 'medium'
                            ? 'bg-yellow-600 hover:bg-yellow-500 text-white border-0'
                            : 'bg-blue-600 hover:bg-blue-500 text-white border-0'
                        : 'opacity-50 hover:opacity-100'
                    }`}
                    onClick={() => {
                      onReorder(t.id, p)
                      toast.success(`Task ${t.id} priority set to ${p.toUpperCase()}`)
                    }}
                  >
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </Button>
                ))}
              </div>
            </div>
          ))}
          {tasks.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-4">No tasks in queue</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Main Swarm Tab ───────────────────────────────────────────────────────────

export function SwarmTab() {
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false)
  const [reassignDialogOpen, setReassignDialogOpen] = useState(false)
  const [reassignWorkerId, setReassignWorkerId] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [reorderDialogOpen, setReorderDialogOpen] = useState(false)
  const [taskPriorities, setTaskPriorities] = useState<Record<string, string>>({})
  const ws = useSwarmWS()
  const { data: apiData, loading, refetch } = useApiData<SwarmApiResponse>('/api/swarm', 15000)

  // Map API workers to Worker interface, merging with WebSocket updates
  const apiWorkers: Worker[] = useMemo(() => {
    if (!apiData?.workers) return []
    return apiData.workers.map(w => {
      const wsUpdate = ws.workers[w.id]
      // Generate a deterministic simulated progress for busy/error workers
      const progress = w.status === 'busy' ? Math.min(95, 30 + w.tasksDone * 5) : w.status === 'error' ? ((w.id.charCodeAt(w.id.length - 1) * 37) % 50) : 0
      return {
        id: w.id,
        name: w.name,
        status: wsUpdate?.status || w.status,
        task: wsUpdate?.task || (w.status === 'busy' ? `T-${String(800 + w.tasksDone).padStart(4, '0')}` : null),
        domain: wsUpdate?.domain || w.domain,
        progress: wsUpdate?.progress || progress,
        tokens: wsUpdate?.tokens || w.totalTokens,
        uptime: formatUptime(w.lastActive),
        trustScore: w.trustScore,
        tasksDone: w.tasksDone,
        tasksFailed: w.tasksFailed,
      }
    })
  }, [apiData, ws.workers])

  // Stats from API or computed from workers
  const stats = apiData?.stats
  const busyCount = stats?.busyWorkers ?? apiWorkers.filter(w => w.status === 'busy').length
  const idleCount = stats?.idleWorkers ?? apiWorkers.filter(w => w.status === 'idle').length
  const errorCount = stats?.errorWorkers ?? apiWorkers.filter(w => w.status === 'error').length
  const offlineCount = stats?.offlineWorkers ?? apiWorkers.filter(w => w.status === 'offline').length
  const totalTokens = apiWorkers.reduce((s, w) => s + w.tokens, 0)
  const avgTrust = stats?.avgTrust ?? (apiWorkers.length > 0 ? apiWorkers.reduce((s, w) => s + w.trustScore, 0) / apiWorkers.length : 0)

  // Task queue - use WebSocket data if available, otherwise fallback
  const liveTaskQueue = useMemo(() => {
    let queue: { id: string; domain: string; priority: string; status: string; submittedBy: string }[]
    if (ws.taskQueue.length > 0) {
      queue = ws.taskQueue.map(t => ({
        id: t.taskId,
        domain: t.domain,
        priority: taskPriorities[t.taskId] ?? t.priority,
        status: 'queued' as const,
        submittedBy: t.submittedBy,
      }))
    } else {
      queue = taskQueue.map(t => ({
        ...t,
        priority: taskPriorities[t.id] ?? t.priority,
      }))
    }
    return queue.sort((a, b) => (PRIORITY_ORDER[b.priority] ?? 0) - (PRIORITY_ORDER[a.priority] ?? 0))
  }, [ws.taskQueue, taskPriorities])

  // Recent completions - use WebSocket data if available, otherwise fallback
  const liveRecentCompleted = useMemo(() => {
    if (ws.recentCompletions.length > 0) {
      return ws.recentCompletions.map(c => ({
        id: c.taskId,
        worker: c.workerId,
        result: c.result,
        duration: c.duration,
        tokens: c.tokens,
      }))
    }
    return recentCompleted
  }, [ws.recentCompletions])

  // Compute live metrics
  const totalTasks = stats?.totalTasks ?? apiWorkers.reduce((s, w) => s + w.tasksDone + w.tasksFailed, 0)
  const liveMetrics = ws.metrics ?? {
    throughput: totalTasks > 0 ? totalTasks * 0.5 : 11.2,
    avgDuration: 12.4,
    successRate: totalTasks > 0 ? (apiWorkers.reduce((s, w) => s + w.tasksDone, 0) / totalTasks) * 100 : 87.3,
    utilization: apiWorkers.length > 0 ? Math.round(((busyCount + errorCount) / apiWorkers.length) * 100) : 60,
    totalTokens,
  }

  // Find worker for reassign dialog
  const reassignWorker = reassignWorkerId ? apiWorkers.find(w => w.id === reassignWorkerId) ?? null : null

  const handleWorkerClick = (worker: Worker) => {
    setSelectedWorker(worker)
    setDialogOpen(true)
  }

  const handleTerminate = useCallback(async (workerId: string) => {
    setActionLoading(`terminate-${workerId}`)
    const result = await callSwarmApi('terminate_worker', { workerId })
    setActionLoading(null)
    if (result.ok) {
      toast.success('Worker terminated', {
        description: result.data?.message || 'Worker removed from the swarm pool',
        icon: <Trash2 className="h-4 w-4" />,
      })
      refetch()
    }
  }, [refetch])

  const handleRestart = useCallback(async (workerId: string) => {
    setActionLoading(`restart-${workerId}`)
    const result = await callSwarmApi('restart_worker', { workerId })
    setActionLoading(null)
    if (result.ok) {
      toast.success('Worker restarted', {
        description: result.data?.message || 'Worker is now idle and ready',
        icon: <RotateCcw className="h-4 w-4" />,
      })
      refetch()
    }
  }, [refetch])

  const handleUpdateTrust = useCallback(async (workerId: string, delta: number, reason: string) => {
    const direction = delta > 0 ? 'up' : 'down'
    setActionLoading(`trust-${direction}-${workerId}`)
    const result = await callSwarmApi('update_trust', { workerId, delta, reason })
    setActionLoading(null)
    if (result.ok) {
      toast.success(`Trust ${delta > 0 ? 'increased' : 'decreased'}`, {
        description: result.data?.message || `Trust score adjusted by ${delta > 0 ? '+' : ''}${delta}`,
        icon: delta > 0 ? <ThumbsUp className="h-4 w-4" /> : <ThumbsDown className="h-4 w-4" />,
      })
      refetch()
      // Update the selected worker in the detail dialog if it's the same worker
      setSelectedWorker(prev => {
        if (prev && prev.id === workerId) {
          return { ...prev, trustScore: Math.max(0, Math.min(1, prev.trustScore + delta)) }
        }
        return prev
      })
    }
  }, [refetch])

  const handleAssignTask = useCallback(async (taskId: string) => {
    const idleWorker = apiWorkers.find(w => w.status === 'idle')
    if (idleWorker) {
      // Try WebSocket first
      const sent = ws.assignTask(taskId, idleWorker.id)
      if (sent) {
        toast.success(`Task ${taskId} assigned to ${idleWorker.name}`, {
          description: 'Worker will begin processing shortly via WebSocket',
        })
      } else {
        // Fallback to REST API
        setActionLoading(`assign-${idleWorker.id}`)
        const result = await callSwarmApi('reassign_task', {
          workerId: idleWorker.id,
          newTask: taskId,
        })
        setActionLoading(null)
        if (result.ok) {
          toast.success(`Task ${taskId} assigned to ${idleWorker.name}`, {
            description: 'Worker will begin processing shortly',
            icon: <Play className="h-4 w-4" />,
          })
          refetch()
        }
      }
    } else {
      toast.error('No idle workers available', {
        description: 'All workers are busy or in error state',
        icon: <AlertTriangle className="h-4 w-4" />,
      })
    }
  }, [apiWorkers, ws, refetch])

  const handleOpenReassign = useCallback((workerId: string) => {
    setReassignWorkerId(workerId)
    setReassignDialogOpen(true)
  }, [])

  const handleReorderPriority = useCallback((taskId: string, newPriority: string) => {
    setTaskPriorities(prev => ({ ...prev, [taskId]: newPriority }))
  }, [])

  return (
    <div className="space-y-6 p-6 grid-pattern">
      {/* Swarm Health Indicator with WebSocket status */}
      <div className="relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-r from-emerald-600/5 via-transparent to-blue-600/5 p-4">
        {/* Animated gradient border glow */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-emerald-600/10 via-transparent to-blue-600/10 opacity-0 hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-blue-600 shadow-lg shadow-emerald-600/10">
              <Cpu className="h-5 w-5 text-white" />
              {/* Animated pulse ring */}
              <div className="absolute inset-0 rounded-xl border border-emerald-400/30 animate-ping" style={{ animationDuration: '3s' }} />
            </div>
            <div>
              <h2 className="text-base font-semibold">Swarm Health</h2>
              <p className="text-xs text-muted-foreground">{busyCount} busy · {idleCount} idle · {errorCount} error · {offlineCount} offline · {totalTokens.toLocaleString()} total tokens</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Spawn Worker Button */}
            <Button
              size="sm"
              className="gap-1.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white border-0 shadow-lg shadow-emerald-600/10"
              onClick={() => setSpawnDialogOpen(true)}
            >
              <UserPlus className="h-3.5 w-3.5" />
              Spawn Worker
            </Button>
            {/* WebSocket Connection Status */}
            <Badge className={`border-0 text-[10px] gap-1 ${ws.connected ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-red-600/15 text-red-600 dark:text-red-400'}`}>
              {ws.connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {ws.connected ? 'LIVE' : 'Offline'}
            </Badge>
            <Badge className={`border-0 text-[10px] gap-1 ${errorCount > 0 ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' : 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${errorCount > 0 ? 'bg-yellow-400' : 'bg-emerald-400'} animate-pulse`} />
              {errorCount > 0 ? 'Attention Needed' : 'Healthy'}
            </Badge>
          </div>
        </div>
        {/* Live activity feed from WebSocket */}
        {ws.activities.length > 0 && (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-muted/30 px-3 py-2">
            <Radio className="h-3 w-3 text-emerald-600 dark:text-emerald-400 animate-pulse shrink-0" />
            <p className="text-[11px] text-muted-foreground truncate">
              {ws.activities[0].message}
            </p>
            <span className="text-[10px] text-muted-foreground/60 shrink-0 ml-auto">
              just now
            </span>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          {/* Hover glow border */}
          <div className="absolute inset-0 rounded-lg border border-blue-600/0 group-hover:border-blue-600/20 transition-colors duration-300 pointer-events-none" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Workers</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{apiWorkers.length}</p>
                <p className="text-[10px] text-muted-foreground">Foreman pool</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-emerald-600/20 group">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
          <div className="absolute inset-0 rounded-lg border border-emerald-600/0 group-hover:border-emerald-600/30 transition-colors duration-300 pointer-events-none" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Busy</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{busyCount}</p>
                <p className="text-[10px] text-muted-foreground">executing tasks</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Activity className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-muted/30 via-transparent to-transparent" />
          <div className="absolute inset-0 rounded-lg border border-border/0 group-hover:border-border/30 transition-colors duration-300 pointer-events-none" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Idle</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{idleCount}</p>
                <p className="text-[10px] text-muted-foreground">ready for assignment</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-muted">
                <Clock className="h-5 w-5 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-red-600/20 group">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/8 via-transparent to-transparent" />
          <div className="absolute inset-0 rounded-lg border border-red-600/0 group-hover:border-red-600/30 transition-colors duration-300 pointer-events-none" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Error</p>
                <p className="mt-1 text-3xl font-bold text-red-600 dark:text-red-400 tabular-nums">{errorCount}</p>
                <p className="text-[10px] text-muted-foreground">needs attention</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                <Bug className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Swarm Metrics Mini-Dashboard */}
      <div className="grid gap-3 md:grid-cols-5">
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift group">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-emerald-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600/15">
              <Gauge className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Tasks/hour</p>
              <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{liveMetrics.throughput.toFixed(1)}</p>
            </div>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-blue-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/15">
              <Timer className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Avg Duration</p>
              <p className="text-lg font-bold text-blue-600 dark:text-blue-400 tabular-nums">{liveMetrics.avgDuration.toFixed(1)}s</p>
            </div>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 via-orange-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-600/15">
              <TrendingUp className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Success Rate</p>
              <p className="text-lg font-bold text-orange-600 dark:text-orange-400 tabular-nums">{liveMetrics.successRate.toFixed(1)}%</p>
            </div>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 via-purple-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-600/15">
              <BarChart3 className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Utilization</p>
              <p className="text-lg font-bold text-purple-600 dark:text-purple-400 tabular-nums">{liveMetrics.utilization}%</p>
            </div>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-600/10 via-amber-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-600/15">
              <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Avg Trust</p>
              <p className="text-lg font-bold text-amber-600 dark:text-amber-400 tabular-nums">{avgTrust.toFixed(2)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Swarm Load Progress Bar */}
      <div className="rounded-lg border border-border/50 bg-card p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 text-muted-foreground" />
            Swarm Load
          </span>
          <span className="text-xs text-muted-foreground tabular-nums">{busyCount + errorCount}/{apiWorkers.length} workers occupied</span>
        </div>
        <div className="relative h-3 w-full overflow-hidden rounded-full bg-muted">
          {/* Gradient fill with animated shimmer */}
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-600 via-emerald-500 to-emerald-400 transition-all duration-500 relative overflow-hidden"
            style={{ width: `${apiWorkers.length > 0 ? ((busyCount + errorCount) / apiWorkers.length) * 100 : 0}%` }}
          >
            {/* Shimmer overlay */}
            <div className="absolute inset-0 shimmer opacity-40" />
          </div>
        </div>
        <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground">
          <span>{apiWorkers.length > 0 ? ((busyCount + errorCount) / apiWorkers.length * 100).toFixed(0) : 0}% capacity utilized</span>
          <span>{idleCount} workers available</span>
        </div>
      </div>

      {/* Swarm Topology Map + Worker Performance Comparison */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Swarm Topology Map */}
        <Card className="relative overflow-hidden border-emerald-600/15">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Network className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Swarm Topology
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="relative flex flex-col items-center py-4">
              {/* Foreman Node */}
              <div className="flex flex-col items-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-lg shadow-emerald-600/20 text-white font-bold text-xs">
                  F
                </div>
                <span className="mt-1 text-[9px] text-emerald-600 dark:text-emerald-400 font-medium">Foreman</span>
              </div>

              {/* Connecting lines container */}
              <div className="relative mt-2 h-6 w-full">
                <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 24" preserveAspectRatio="xMidYMid meet">
                  {apiWorkers.map((_, i) => {
                    const x = 50 + (i * (300 / Math.max(apiWorkers.length - 1, 1)))
                    return <line key={i} x1="200" y1="0" x2={x} y2="24" stroke="currentColor" strokeWidth="1" className="text-emerald-600/20 dark:text-emerald-400/20" />
                  })}
                </svg>
              </div>

              {/* Worker Nodes */}
              <div className="flex flex-wrap items-start justify-center gap-3 mt-1">
                {apiWorkers.map((w: any, i: number) => {
                  const statusColor = w.status === 'busy' ? 'bg-emerald-500 shadow-emerald-600/30' : w.status === 'error' ? 'bg-red-500 shadow-red-600/30' : w.status === 'idle' ? 'bg-blue-500 shadow-blue-600/30' : 'bg-gray-500 shadow-gray-600/30'
                  const isPulsing = w.status === 'busy'
                  return (
                    <button
                      key={w.id || i}
                      className="flex flex-col items-center group cursor-pointer"
                      onClick={() => {/* handled by worker detail dialog */}}
                    >
                      <div className={`relative flex h-8 w-8 items-center justify-center rounded-full ${statusColor} shadow-md text-white text-[10px] font-bold transition-transform group-hover:scale-110`}>
                        {String(i + 1)}
                        {isPulsing && <span className="absolute inset-0 rounded-full bg-emerald-400/30 animate-ping" style={{ animationDuration: '2s' }} />}
                      </div>
                      <span className="mt-0.5 text-[8px] text-muted-foreground truncate max-w-[48px]">
                        {w.agentId || `w-${i + 1}`}
                      </span>
                    </button>
                  )
                })}
              </div>

              {/* Legend */}
              <div className="mt-4 flex items-center gap-4 text-[9px] text-muted-foreground">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Busy</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-500" /> Idle</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" /> Error</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-gray-500" /> Offline</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Worker Performance Comparison */}
        <Card className="relative overflow-hidden border-blue-600/15">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-600/40 to-transparent" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              Worker Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <NexusBarChart
              data={workerPerformanceData}
              dataKey="value"
              color={COLORS.blue}
              height={140}
            />
            <div className="mt-2 space-y-1.5">
              {workerPerformanceRows.map((row) => (
                  <div key={row.id} className="flex items-center gap-2 text-[10px]">
                    <span className="font-mono text-muted-foreground w-12 truncate">{row.name}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                      <div className="h-full rounded-full bg-blue-500/60" style={{ width: `${Math.min(row.tasks * 5, 100)}%` }} />
                    </div>
                    <span className="text-muted-foreground tabular-nums w-14 text-right">{row.tasks} tasks</span>
                    <span className="text-muted-foreground/60 tabular-nums w-14 text-right">{row.avgTime}ms</span>
                    <span className={`tabular-nums w-10 text-right ${row.errRate > 3 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>{row.errRate}%</span>
                  </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Throughput Chart */}
      <Card className="relative overflow-hidden">
        {/* Gradient border accent */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Cpu className="h-4 w-4" /> Swarm Throughput
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 gap-1 text-[9px] text-muted-foreground hover:text-foreground"
                onClick={() => refetch()}
              >
                <RefreshCw className="h-3 w-3" />
                Refresh
              </Button>
              <Badge variant="outline" className="text-[9px]">last 10 intervals</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <NexusBarChart
            data={[
              { name: '-50m', value: 8 },
              { name: '-40m', value: 12 },
              { name: '-30m', value: 6 },
              { name: '-20m', value: 14 },
              { name: '-10m', value: 9 },
              { name: 'now', value: 11 },
            ]}
            dataKey="value"
            nameKey="name"
            color={COLORS.emerald}
            height={80}
          />
        </CardContent>
      </Card>

      {/* Swarm Topology Map + Worker Performance Comparison */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Swarm Topology Map */}
        <Card className="relative overflow-hidden border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Network className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Swarm Topology
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            {apiWorkers.length > 0 ? (
              <div className="relative flex items-center justify-center" style={{ minHeight: '200px' }}>
                {/* Central Foreman node */}
                <div
                  className="absolute flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-lg shadow-emerald-600/30 cursor-pointer z-10 hover:scale-110 transition-transform"
                  title="Foreman (coordinator)"
                >
                  <Cpu className="h-6 w-6 text-white" />
                </div>
                {/* Worker nodes arranged in a circle */}
                {apiWorkers.map((w, i) => {
                  const angle = (2 * Math.PI * i) / apiWorkers.length - Math.PI / 2
                  const radius = 100
                  const x = Math.cos(angle) * radius
                  const y = Math.sin(angle) * radius
                  const nodeColor = w.status === 'busy' ? 'bg-emerald-500' : w.status === 'error' ? 'bg-red-500' : w.status === 'offline' ? 'bg-gray-500' : 'bg-blue-500'
                  const isBusy = w.status === 'busy'
                  return (
                    <div key={w.id} className="absolute" style={{ left: `calc(50% + ${x}px - 14px)`, top: `calc(50% + ${y}px - 14px)` }}>
                      {/* Connection line from center */}
                      <svg
                        className="absolute pointer-events-none"
                        style={{ left: '14px', top: '14px', overflow: 'visible' }}
                        width="1"
                        height="1"
                      >
                        <line
                          x1={0}
                          y1={0}
                          x2={-x}
                          y2={-y}
                          stroke={w.status === 'busy' ? '#34d399' : w.status === 'error' ? '#f87171' : '#94a3b8'}
                          strokeWidth={1.5}
                          strokeDasharray={isBusy ? '4 2' : '2 2'}
                          opacity={0.5}
                        >
                          {isBusy && (
                            <animate attributeName="stroke-dashoffset" from="0" to="12" dur="1s" repeatCount="indefinite" />
                          )}
                        </line>
                      </svg>
                      {/* Worker node */}
                      <button
                        className={`flex h-7 w-7 items-center justify-center rounded-full ${nodeColor} shadow-md cursor-pointer hover:scale-125 transition-transform ${isBusy ? 'animate-pulse' : ''}`}
                        title={`${w.name} (${w.status})`}
                        onClick={() => handleWorkerClick(w)}
                      >
                        <span className="text-[8px] font-bold text-white">{w.name.replace('worker-', 'W').replace('research-agent', 'R')}</span>
                      </button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-xs text-muted-foreground">
                No workers connected
              </div>
            )}
            {/* Legend */}
            <div className="mt-3 flex items-center justify-center gap-4 text-[10px] text-muted-foreground">
              <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Busy</div>
              <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> Idle</div>
              <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-red-500" /> Error</div>
              <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-gray-500" /> Offline</div>
            </div>
          </CardContent>
        </Card>

        {/* Worker Performance Comparison */}
        <Card className="relative overflow-hidden border-blue-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-600 dark:text-blue-400" /> Worker Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            {apiWorkers.length > 0 ? (
              <NexusBarChart
                data={apiWorkers.map(w => ({
                  name: w.name.replace('worker-', 'W').replace('research-agent', 'R'),
                  value: w.tasksDone,
                }))}
                height={160}
                color={COLORS.blue}
              />
            ) : (
              <div className="flex items-center justify-center h-[160px] text-xs text-muted-foreground">
                No worker data available
              </div>
            )}
            {/* Performance metrics table */}
            <div className="mt-3 space-y-1.5">
              {apiWorkers.slice(0, 4).map((w) => {
                const errRate = (w.tasksDone + w.tasksFailed) > 0 ? ((w.tasksFailed / (w.tasksDone + w.tasksFailed)) * 100).toFixed(1) : '0.0'
                return (
                  <div key={w.id} className="flex items-center gap-2 text-[10px]">
                    <span className="w-16 font-medium truncate">{w.name}</span>
                    <div className="flex-1 flex items-center gap-2">
                      <div className="flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                        <span className="tabular-nums">{w.tasksDone}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Timer className="h-3 w-3 text-blue-500" />
                        <span className="tabular-nums">{(8 + (w.id.charCodeAt(w.id.length - 1) % 12))}ms</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3 text-orange-500" />
                        <span className="tabular-nums">{errRate}%</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Worker Grid */}
        <Card className="lg:col-span-2 relative overflow-hidden">
          {/* Gradient border accent */}
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-600/40 to-transparent" />
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Users className="h-4 w-4" /> Worker Status Grid
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  className="gap-1.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white border-0 h-7 text-[10px]"
                  onClick={() => setSpawnDialogOpen(true)}
                >
                  <Plus className="h-3 w-3" />
                  Spawn
                </Button>
                <ExportButton data={apiWorkers.map(w => ({ ...w }))} filename="swarm-worker-status" label="Export" columnHeaders={workerStatusColumnHeaders} />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {loading && !apiData ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400 animate-spin" />
                <span className="ml-2 text-xs text-muted-foreground">Loading workers...</span>
              </div>
            ) : apiWorkers.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {apiWorkers.map((w) => {
                  const statusDisplay = getStatusDisplay(w.status)
                  const StatusIcon = statusDisplay.icon
                  return (
                    <div
                      key={w.id}
                      onClick={() => handleWorkerClick(w)}
                      className={`relative rounded-lg border p-3.5 transition-all duration-200 cursor-pointer hover-lift group ${getWorkerCardStyle(w.status)}`}
                    >
                      {/* Pulsing border for error workers */}
                      {w.status === 'error' && (
                        <div className="absolute inset-0 rounded-lg border-2 border-red-500/30 animate-pulse pointer-events-none" />
                      )}

                      {/* Gradient top accent line based on status */}
                      <div className={`absolute inset-x-0 top-0 h-0.5 rounded-t-lg ${
                        w.status === 'busy' ? 'bg-gradient-to-r from-emerald-600 via-emerald-400 to-emerald-600' :
                        w.status === 'error' ? 'bg-gradient-to-r from-red-600 via-red-400 to-red-600' :
                        w.status === 'offline' ? 'bg-gradient-to-r from-muted via-muted-foreground/30 to-muted' :
                        'bg-gradient-to-r from-muted-foreground/10 via-muted-foreground/20 to-muted-foreground/10'
                      }`} />

                      {/* Status dot indicator */}
                      <div className={`absolute top-2 right-2 h-2 w-2 rounded-full ${
                        w.status === 'busy' ? 'bg-emerald-400 animate-pulse' :
                        w.status === 'error' ? 'bg-red-400 animate-pulse' :
                        w.status === 'offline' ? 'bg-muted-foreground/20' :
                        'bg-muted-foreground/40'
                      }`} />

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{w.name}</span>
                          <Badge
                            className={`text-[9px] border-0 ${statusDisplay.badgeClass}`}
                          >
                            {w.status === 'busy' && <StatusIcon className={`mr-1 h-3 w-3 ${w.status === 'busy' ? 'animate-spin' : ''}`} />}
                            {w.status}
                          </Badge>
                        </div>
                        {w.domain && (
                          <Badge variant="outline" className="text-[9px]">{w.domain}</Badge>
                        )}
                      </div>

                      {/* Trust indicator bar */}
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[9px] text-muted-foreground shrink-0">Trust</span>
                        <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-muted">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              w.trustScore >= 0.8 ? 'bg-emerald-500' :
                              w.trustScore >= 0.5 ? 'bg-yellow-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${w.trustScore * 100}%` }}
                          />
                        </div>
                        <span className="text-[9px] font-mono tabular-nums text-muted-foreground shrink-0">{w.trustScore.toFixed(2)}</span>
                      </div>

                      {w.task && (
                        <div className="mt-2">
                          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                            <span>Task: {w.task}</span>
                            <span>{w.progress}%</span>
                          </div>
                          <div className="relative mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                            <div
                              className={`h-full rounded-full transition-all duration-1000 ${
                                w.status === 'busy'
                                  ? 'bg-gradient-to-r from-emerald-600 to-emerald-400'
                                  : 'bg-red-400'
                              }`}
                              style={{ width: `${w.progress}%` }}
                            />
                          </div>
                        </div>
                      )}
                      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>{w.tokens > 0 ? `${w.tokens.toLocaleString()} tokens` : 'No task'}</span>
                        <span>↑ {w.uptime}</span>
                      </div>

                      {/* Quick action buttons on hover */}
                      <div className="mt-2 flex items-center justify-between">
                        <div className="flex items-center gap-1 text-[9px] text-muted-foreground/60 group-hover:text-muted-foreground transition-colors">
                          <Zap className="h-2.5 w-2.5" />
                          Click for details
                        </div>
                        {/* Quick trust buttons */}
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 w-5 p-0 text-red-600 dark:text-red-400 hover:bg-red-600/10 hover:text-red-300"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleUpdateTrust(w.id, -0.05, `Quick adjust from worker card: -0.05`)
                            }}
                            disabled={actionLoading !== null}
                          >
                            <ThumbsDown className="h-2.5 w-2.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-5 w-5 p-0 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10 dark:hover:text-emerald-300"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleUpdateTrust(w.id, 0.05, `Quick adjust from worker card: +0.05`)
                            }}
                            disabled={actionLoading !== null}
                          >
                            <ThumbsUp className="h-2.5 w-2.5" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-xs text-muted-foreground gap-3">
                <Users className="h-8 w-8 text-muted-foreground/30" />
                <span>No workers found. Seed the database or spawn a new worker.</span>
                <Button
                  size="sm"
                  className="gap-1.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white border-0"
                  onClick={() => setSpawnDialogOpen(true)}
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  Spawn Worker
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Task Priority Queue */}
        <Card className="relative overflow-hidden">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-600/40 to-transparent" />
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="h-4 w-4" /> Task Priority Queue
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 gap-1 text-[9px] text-orange-600 dark:text-orange-400 hover:bg-orange-600/10"
                onClick={() => setReorderDialogOpen(true)}
              >
                <ArrowUpDown className="h-3 w-3" />
                Reorder
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {liveTaskQueue.map((t, i) => (
                <div key={t.id} className="flex items-center justify-between rounded-md bg-accent/30 px-3 py-2 transition-colors hover:bg-accent/50">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-[10px] text-muted-foreground tabular-nums w-4">{i + 1}.</span>
                    <span className="text-xs font-mono">{t.id}</span>
                    <Badge variant="outline" className="text-[9px]">{t.domain}</Badge>
                    {getPriorityBadge(t.priority)}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 gap-1 text-[9px] text-emerald-600 dark:text-emerald-400 dark:hover:text-emerald-300 hover:bg-emerald-600/10 shrink-0 ml-2"
                    onClick={() => handleAssignTask(t.id)}
                    disabled={actionLoading !== null}
                  >
                    {actionLoading?.startsWith('assign-') ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Play className="h-3 w-3" />
                    )}
                    Assign
                  </Button>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-muted-foreground">{liveTaskQueue.length} tasks queued · Sorted by priority</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Completed */}
      <Card className="relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" /> Recent Completed
            </CardTitle>
            <ExportButton data={liveRecentCompleted} filename="swarm-task-history" label="Export Tasks" columnHeaders={taskHistoryColumnHeaders} />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] text-muted-foreground">
                  <th className="p-3 font-medium">Task</th>
                  <th className="p-3 font-medium">Worker</th>
                  <th className="p-3 font-medium">Result</th>
                  <th className="p-3 font-medium">Duration</th>
                  <th className="p-3 font-medium">Tokens</th>
                </tr>
              </thead>
              <tbody>
                {liveRecentCompleted.map((r) => (
                  <tr key={r.id} className="border-b border-border/50 hover:bg-accent/50 transition-colors">
                    <td className="p-3 font-mono text-xs">{r.id}</td>
                    <td className="p-3 text-xs">{r.worker}</td>
                    <td className="p-3">
                      {r.result === 'success' ? (
                        <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[10px]"><CheckCircle2 className="mr-1 h-3 w-3" />PASS</Badge>
                      ) : (
                        <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[10px]"><XCircle className="mr-1 h-3 w-3" />FAIL</Badge>
                      )}
                    </td>
                    <td className="p-3 text-xs">{r.duration}</td>
                    <td className="p-3 text-xs tabular-nums">{r.tokens.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Worker Detail Dialog */}
      <WorkerDetailDialog
        worker={selectedWorker}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onTerminate={handleTerminate}
        onRestart={handleRestart}
        onReassign={handleOpenReassign}
        onUpdateTrust={handleUpdateTrust}
        actionLoading={actionLoading}
      />

      {/* Spawn Worker Dialog */}
      <SpawnWorkerDialog
        open={spawnDialogOpen}
        onOpenChange={setSpawnDialogOpen}
        onSpawned={refetch}
      />

      {/* Reassign Task Dialog */}
      <ReassignTaskDialog
        worker={reassignWorker}
        open={reassignDialogOpen}
        onOpenChange={setReassignDialogOpen}
        onReassigned={refetch}
      />
    </div>
  )
}
