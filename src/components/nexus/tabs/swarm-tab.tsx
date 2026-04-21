'use client'

import { useState, useMemo, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Bug,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Users,
  Cpu,
  X,
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
} from 'lucide-react'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'
import { ExportButton } from '@/components/nexus/export-button'
import { toast } from 'sonner'
import { useSwarmWS, type WorkerUpdate, type TaskQueued, type TaskComplete } from '@/hooks/use-swarm-ws'
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

const taskQueueColumnHeaders: Record<string, string> = {
  id: 'Task ID',
  domain: 'Domain',
  priority: 'Priority',
  status: 'Status',
  submittedBy: 'Submitted By',
}

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
        textClass: 'text-emerald-400',
        badgeClass: 'bg-emerald-600/15 text-emerald-400',
        label: 'Executing task',
      }
    case 'error':
      return {
        icon: Bug,
        bgClass: 'bg-red-600/15 shadow-lg shadow-red-600/10',
        textClass: 'text-red-400',
        badgeClass: 'bg-red-600/15 text-red-400',
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

function WorkerDetailDialog({
  worker,
  open,
  onOpenChange,
  onTerminate,
  onReassign,
}: {
  worker: Worker | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onTerminate: (workerId: string) => void
  onReassign: (workerId: string) => void
}) {
  if (!worker) return null

  const isIdle = worker.status === 'idle'
  const isError = worker.status === 'error'
  const statusDisplay = getStatusDisplay(worker.status)
  const StatusIcon = statusDisplay.icon

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
              <p className="mt-0.5 text-sm font-bold tabular-nums">{worker.trustScore.toFixed(2)}</p>
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
                <span className="text-emerald-400">{worker.tasksDone}</span>
                {' / '}
                <span className="text-red-400">{worker.tasksFailed}</span>
              </p>
            </div>
          </div>

          {/* Error details for error workers */}
          {isError && (
            <div className="rounded-lg border border-red-600/20 bg-red-600/5 p-3">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-red-400" />
                <p className="text-[10px] uppercase tracking-wider text-red-400">Error Details</p>
              </div>
              <p className="text-xs text-red-300 leading-relaxed">
                Worker encountered an error. Last task may have failed.
                Error: &quot;Rate limit exceeded — retry after 60s or reassign to another worker.&quot;
              </p>
              <div className="mt-2 flex items-center gap-2">
                <Badge className="bg-red-600/15 text-red-400 border-0 text-[9px]">E-RATE-429</Badge>
                <Badge className="bg-red-600/15 text-red-400 border-0 text-[9px]">Auto-retry: disabled</Badge>
              </div>
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

        <DialogFooter className="gap-2">
          {isIdle && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => {
                onReassign(worker.id)
                onOpenChange(false)
              }}
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
              onClick={() => {
                onTerminate(worker.id)
                onOpenChange(false)
              }}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Terminate Worker
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function SwarmTab() {
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const ws = useSwarmWS()
  const { data: apiData, loading, refetch } = useApiData<SwarmApiResponse>('/api/swarm', 15000)

  // Map API workers to Worker interface, merging with WebSocket updates
  const apiWorkers: Worker[] = useMemo(() => {
    if (!apiData?.workers) return []
    return apiData.workers.map(w => {
      const wsUpdate = ws.workers[w.id]
      // Generate a simulated progress for busy workers
      const progress = w.status === 'busy' ? Math.min(95, 30 + w.tasksDone * 5) : w.status === 'error' ? Math.floor(Math.random() * 50) : 0
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
    if (ws.taskQueue.length > 0) {
      return ws.taskQueue.map(t => ({
        id: t.taskId,
        domain: t.domain,
        priority: t.priority,
        status: 'queued' as const,
        submittedBy: t.submittedBy,
      }))
    }
    return taskQueue
  }, [ws.taskQueue])

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

  const handleWorkerClick = (worker: Worker) => {
    setSelectedWorker(worker)
    setDialogOpen(true)
  }

  const handleTerminate = useCallback(async (workerId: string) => {
    try {
      const res = await fetch('/api/swarm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'terminate_worker', workerId }),
      })
      if (res.ok) {
        const data = await res.json()
        toast.success(`Worker terminated`, {
          description: data.message || `Worker removed from the swarm pool`,
        })
        refetch()
      } else {
        const err = await res.json()
        toast.error('Failed to terminate worker', { description: err.error || 'Unknown error' })
      }
    } catch {
      toast.error('Failed to terminate worker', { description: 'Network error' })
    }
  }, [refetch])

  const handleReassign = useCallback(async (workerId: string) => {
    try {
      const res = await fetch('/api/swarm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reassign_task', workerId }),
      })
      if (res.ok) {
        const data = await res.json()
        toast.success(`Task reassigned`, {
          description: data.message || `Next queued task will be assigned to this worker`,
        })
        refetch()
      } else {
        const err = await res.json()
        toast.error('Failed to reassign task', { description: err.error || 'Unknown error' })
      }
    } catch {
      toast.error('Failed to reassign task', { description: 'Network error' })
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
        try {
          const res = await fetch('/api/swarm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'reassign_task', workerId: idleWorker.id, taskId }),
          })
          if (res.ok) {
            toast.success(`Task ${taskId} assigned to ${idleWorker.name}`, {
              description: 'Worker will begin processing shortly',
            })
            refetch()
          } else {
            toast.error('Failed to assign task')
          }
        } catch {
          toast.error('Failed to assign task', { description: 'Network error' })
        }
      }
    } else {
      toast.error('No idle workers available', {
        description: 'All workers are busy or in error state',
      })
    }
  }, [apiWorkers, ws, refetch])

  return (
    <div className="space-y-6 p-6 grid-pattern">
      {/* Swarm Health Indicator with WebSocket status */}
      <div className="relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-r from-emerald-600/5 via-transparent to-blue-600/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-blue-600 shadow-lg shadow-emerald-600/10">
              <Cpu className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold">Swarm Health</h2>
              <p className="text-xs text-muted-foreground">{busyCount} busy · {idleCount} idle · {errorCount} error · {offlineCount} offline · {totalTokens.toLocaleString()} total tokens</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* WebSocket Connection Status */}
            <Badge className={`border-0 text-[10px] gap-1 ${ws.connected ? 'bg-emerald-600/15 text-emerald-400' : 'bg-red-600/15 text-red-400'}`}>
              {ws.connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {ws.connected ? 'LIVE' : 'Offline'}
            </Badge>
            <Badge className={`border-0 text-[10px] gap-1 ${errorCount > 0 ? 'bg-yellow-600/15 text-yellow-400' : 'bg-emerald-600/15 text-emerald-400'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${errorCount > 0 ? 'bg-yellow-400' : 'bg-emerald-400'} animate-pulse`} />
              {errorCount > 0 ? 'Attention Needed' : 'Healthy'}
            </Badge>
          </div>
        </div>
        {/* Live activity feed from WebSocket */}
        {ws.activities.length > 0 && (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-muted/30 px-3 py-2">
            <Radio className="h-3 w-3 text-emerald-400 animate-pulse shrink-0" />
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
        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Workers</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{apiWorkers.length}</p>
                <p className="text-[10px] text-muted-foreground">Foreman pool</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Users className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Busy</p>
                <p className="mt-1 text-3xl font-bold text-emerald-400 tabular-nums">{busyCount}</p>
                <p className="text-[10px] text-muted-foreground">executing tasks</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Activity className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-muted/30 via-transparent to-transparent" />
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
        <Card className="relative overflow-hidden border-red-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Error</p>
                <p className="mt-1 text-3xl font-bold text-red-400 tabular-nums">{errorCount}</p>
                <p className="text-[10px] text-muted-foreground">needs attention</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                <Bug className="h-5 w-5 text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Swarm Metrics Mini-Dashboard */}
      <div className="grid gap-3 md:grid-cols-4">
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-emerald-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600/15">
              <Gauge className="h-4 w-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Tasks/hour</p>
              <p className="text-lg font-bold text-emerald-400 tabular-nums">{liveMetrics.throughput.toFixed(1)}</p>
            </div>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-blue-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/15">
              <Timer className="h-4 w-4 text-blue-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Avg Duration</p>
              <p className="text-lg font-bold text-blue-400 tabular-nums">{liveMetrics.avgDuration.toFixed(1)}s</p>
            </div>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 via-orange-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-600/15">
              <TrendingUp className="h-4 w-4 text-orange-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Success Rate</p>
              <p className="text-lg font-bold text-orange-400 tabular-nums">{liveMetrics.successRate.toFixed(1)}%</p>
            </div>
          </div>
        </div>
        <div className="relative overflow-hidden rounded-lg border border-border/50 p-3 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 via-purple-600/3 to-transparent" />
          <div className="relative flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-600/15">
              <BarChart3 className="h-4 w-4 text-purple-400" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Utilization</p>
              <p className="text-lg font-bold text-purple-400 tabular-nums">{liveMetrics.utilization}%</p>
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
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-500"
            style={{ width: `${apiWorkers.length > 0 ? ((busyCount + errorCount) / apiWorkers.length) * 100 : 0}%` }}
          />
        </div>
        <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground">
          <span>{apiWorkers.length > 0 ? ((busyCount + errorCount) / apiWorkers.length * 100).toFixed(0) : 0}% capacity utilized</span>
          <span>{idleCount} workers available</span>
        </div>
      </div>

      {/* Throughput Chart */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Cpu className="h-4 w-4" /> Swarm Throughput
            </CardTitle>
            <Badge variant="outline" className="text-[9px]">last 10 intervals</Badge>
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

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Worker Grid */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Users className="h-4 w-4" /> Worker Status Grid
              </CardTitle>
              <ExportButton data={apiWorkers.map(w => ({ ...w }))} filename="swarm-worker-status" label="Export Workers" columnHeaders={workerStatusColumnHeaders} />
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {loading && !apiData ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 text-emerald-400 animate-spin" />
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
                      className={`relative rounded-lg border p-3.5 transition-all duration-200 cursor-pointer hover-lift ${getWorkerCardStyle(w.status)}`}
                    >
                      {/* Pulsing border for error workers */}
                      {w.status === 'error' && (
                        <div className="absolute inset-0 rounded-lg border-2 border-red-500/30 animate-pulse pointer-events-none" />
                      )}

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
                                  ? 'bg-gradient-to-r from-emerald-600 to-emerald-400 animate-pulse'
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
                      {/* Click hint */}
                      <div className="mt-1.5 flex items-center gap-1 text-[9px] text-muted-foreground/60">
                        <Zap className="h-2.5 w-2.5" />
                        Click for details
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
                No workers found. Seed the database to see workers.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Task Queue */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4" /> Task Queue
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {liveTaskQueue.map((t) => (
                <div key={t.id} className="flex items-center justify-between rounded-md bg-accent/30 px-3 py-2">
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-mono">{t.id}</span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <Badge variant="outline" className="text-[9px]">{t.domain}</Badge>
                      <Badge className={`text-[9px] border-0 ${t.priority === 'high' ? 'bg-red-600/15 text-red-400' : t.priority === 'medium' ? 'bg-yellow-600/15 text-yellow-400' : 'bg-muted text-muted-foreground'}`}>
                        {t.priority}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 gap-1 text-[9px] text-emerald-400 hover:text-emerald-300 hover:bg-emerald-600/10 shrink-0 ml-2"
                    onClick={() => handleAssignTask(t.id)}
                  >
                    <Play className="h-3 w-3" />
                    Assign
                  </Button>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-muted-foreground">{liveTaskQueue.length} tasks queued</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Completed */}
      <Card>
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
                  <tr key={r.id} className="border-b border-border/50 hover:bg-accent/50">
                    <td className="p-3 font-mono text-xs">{r.id}</td>
                    <td className="p-3 text-xs">{r.worker}</td>
                    <td className="p-3">
                      {r.result === 'success' ? (
                        <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[10px]"><CheckCircle2 className="mr-1 h-3 w-3" />PASS</Badge>
                      ) : (
                        <Badge className="bg-red-600/15 text-red-400 border-0 text-[10px]"><XCircle className="mr-1 h-3 w-3" />FAIL</Badge>
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
        onReassign={handleReassign}
      />
    </div>
  )
}
