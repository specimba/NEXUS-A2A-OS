'use client'

import { useState, useMemo } from 'react'
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
  status: 'busy' | 'error' | 'idle'
  task: string | null
  domain: string | null
  progress: number
  tokens: number
  uptime: string
}

interface TaskHistoryItem {
  id: string
  result: 'success' | 'failure'
  duration: string
  tokens: number
  completedAt: string
}

const workers: Worker[] = [
  { id: 'worker-1', status: 'busy', task: 'T-0848', domain: 'code', progress: 67, tokens: 12400, uptime: '2h 34m' },
  { id: 'worker-2', status: 'error', task: 'T-0846', domain: 'research', progress: 34, tokens: 8200, uptime: '1h 12m' },
  { id: 'worker-3', status: 'busy', task: 'T-0849', domain: 'cyber', progress: 89, tokens: 18600, uptime: '3h 01m' },
  { id: 'worker-4', status: 'idle', task: null, domain: null, progress: 0, tokens: 0, uptime: '0h 45m' },
  { id: 'worker-5', status: 'idle', task: null, domain: null, progress: 0, tokens: 0, uptime: '0h 22m' },
]

const workerHistory: Record<string, TaskHistoryItem[]> = {
  'worker-1': [
    { id: 'T-0847', result: 'success', duration: '14s', tokens: 3420, completedAt: '2m ago' },
    { id: 'T-0843', result: 'success', duration: '3s', tokens: 640, completedAt: '18m ago' },
    { id: 'T-0842', result: 'success', duration: '18s', tokens: 4200, completedAt: '32m ago' },
    { id: 'T-0840', result: 'failure', duration: '8s', tokens: 1280, completedAt: '1h ago' },
  ],
  'worker-2': [
    { id: 'T-0845', result: 'success', duration: '22s', tokens: 5100, completedAt: '15m ago' },
    { id: 'T-0841', result: 'success', duration: '11s', tokens: 2800, completedAt: '40m ago' },
    { id: 'T-0839', result: 'failure', duration: '6s', tokens: 920, completedAt: '1h 10m ago' },
    { id: 'T-0836', result: 'success', duration: '19s', tokens: 4600, completedAt: '1h 45m ago' },
  ],
  'worker-3': [
    { id: 'T-0844', result: 'failure', duration: '8s', tokens: 1280, completedAt: '5m ago' },
    { id: 'T-0841', result: 'success', duration: '11s', tokens: 2800, completedAt: '20m ago' },
    { id: 'T-0838', result: 'success', duration: '25s', tokens: 6100, completedAt: '45m ago' },
    { id: 'T-0835', result: 'success', duration: '16s', tokens: 3900, completedAt: '1h 15m ago' },
  ],
  'worker-4': [
    { id: 'T-0843', result: 'success', duration: '3s', tokens: 640, completedAt: '10m ago' },
    { id: 'T-0837', result: 'success', duration: '9s', tokens: 2100, completedAt: '35m ago' },
    { id: 'T-0834', result: 'success', duration: '7s', tokens: 1800, completedAt: '1h ago' },
  ],
  'worker-5': [
    { id: 'T-0839', result: 'success', duration: '5s', tokens: 1200, completedAt: '8m ago' },
    { id: 'T-0833', result: 'success', duration: '12s', tokens: 2900, completedAt: '50m ago' },
  ],
}

const workerSparklines: Record<string, { name: string; value: number }[]> = {
  'worker-1': [
    { name: '0', value: 800 }, { name: '1', value: 1200 }, { name: '2', value: 1600 },
    { name: '3', value: 1400 }, { name: '4', value: 1800 }, { name: '5', value: 2400 },
    { name: '6', value: 2200 }, { name: '7', value: 2800 },
  ],
  'worker-2': [
    { name: '0', value: 600 }, { name: '1', value: 900 }, { name: '2', value: 1400 },
    { name: '3', value: 1800 }, { name: '4', value: 1200 }, { name: '5', value: 800 },
    { name: '6', value: 600 }, { name: '7', value: 400 },
  ],
  'worker-3': [
    { name: '0', value: 2000 }, { name: '1', value: 2400 }, { name: '2', value: 2800 },
    { name: '3', value: 3200 }, { name: '4', value: 3000 }, { name: '5', value: 3600 },
    { name: '6', value: 3400 }, { name: '7', value: 3800 },
  ],
  'worker-4': [
    { name: '0', value: 0 }, { name: '1', value: 0 }, { name: '2', value: 200 },
    { name: '3', value: 400 }, { name: '4', value: 0 }, { name: '5', value: 0 },
    { name: '6', value: 0 }, { name: '7', value: 0 },
  ],
  'worker-5': [
    { name: '0', value: 0 }, { name: '1', value: 0 }, { name: '2', value: 0 },
    { name: '3', value: 100 }, { name: '4', value: 300 }, { name: '5', value: 0 },
    { name: '6', value: 0 }, { name: '7', value: 0 },
  ],
}

const taskQueue = [
  { id: 'T-0850', domain: 'ai_safety', priority: 'high', status: 'queued', submittedBy: 'coordinator' },
  { id: 'T-0851', domain: 'compbio', priority: 'medium', status: 'queued', submittedBy: 'coordinator' },
  { id: 'T-0852', domain: 'pharmacology', priority: 'low', status: 'queued', submittedBy: 'research-agent' },
  { id: 'T-0853', domain: 'code', priority: 'high', status: 'queued', submittedBy: 'coordinator' },
]

const recentCompleted = [
  { id: 'T-0847', worker: 'worker-3', result: 'success', duration: '14s', tokens: 3420 },
  { id: 'T-0845', worker: 'worker-1', result: 'success', duration: '22s', tokens: 5100 },
  { id: 'T-0844', worker: 'worker-3', result: 'failure', duration: '8s', tokens: 1280 },
  { id: 'T-0843', worker: 'worker-4', result: 'success', duration: '3s', tokens: 640 },
  { id: 'T-0842', worker: 'worker-1', result: 'success', duration: '18s', tokens: 4200 },
]

function WorkerDetailDialog({
  worker,
  open,
  onOpenChange,
}: {
  worker: Worker | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  if (!worker) return null

  const history = workerHistory[worker.id] || []
  const sparkline = workerSparklines[worker.id] || []
  const isIdle = worker.status === 'idle'
  const isError = worker.status === 'error'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg bg-card border-border/60">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${
              worker.status === 'busy'
                ? 'bg-emerald-600/15 shadow-lg shadow-emerald-600/10'
                : worker.status === 'error'
                ? 'bg-red-600/15 shadow-lg shadow-red-600/10'
                : 'bg-muted'
            }`}>
              {worker.status === 'busy' ? (
                <Loader2 className="h-5 w-5 text-emerald-400 animate-spin" />
              ) : worker.status === 'error' ? (
                <Bug className="h-5 w-5 text-red-400" />
              ) : (
                <Clock className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
            <div>
              <DialogTitle className="text-base">{worker.id}</DialogTitle>
              <DialogDescription className="text-xs">
                Worker detail and task history
              </DialogDescription>
            </div>
            <Badge
              className={`ml-auto text-[10px] border-0 ${
                worker.status === 'busy'
                  ? 'bg-emerald-600/15 text-emerald-400'
                  : worker.status === 'error'
                  ? 'bg-red-600/15 text-red-400'
                  : 'bg-muted text-muted-foreground'
              }`}
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
              <p className={`mt-0.5 text-sm font-medium ${
                worker.status === 'busy' ? 'text-emerald-400' :
                worker.status === 'error' ? 'text-red-400' :
                'text-muted-foreground'
              }`}>
                {worker.status === 'busy' ? 'Executing task' :
                 worker.status === 'error' ? 'Error state' :
                 'Available for assignment'}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Current Task</p>
              <p className="mt-0.5 text-sm font-mono font-medium">
                {worker.task || '—'}
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
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Tokens Consumed</p>
              <p className="mt-0.5 text-sm font-bold tabular-nums">
                {worker.tokens > 0 ? worker.tokens.toLocaleString() : '0'}
              </p>
            </div>
            <div className="rounded-lg border border-border/50 p-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Uptime</p>
              <p className="mt-0.5 text-sm font-medium tabular-nums">{worker.uptime}</p>
            </div>
          </div>

          {/* Progress for busy workers */}
          {worker.status === 'busy' && (
            <div className="rounded-lg border border-emerald-600/20 bg-emerald-600/5 p-3">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] uppercase tracking-wider text-emerald-400">Task Progress</p>
                <span className="text-sm font-bold tabular-nums text-emerald-400">{worker.progress}%</span>
              </div>
              <Progress value={worker.progress} className="h-2.5" />
              <p className="mt-1.5 text-[10px] text-muted-foreground">
                Executing {worker.task} in {worker.domain} domain
              </p>
            </div>
          )}

          {/* Error details for error workers */}
          {isError && (
            <div className="rounded-lg border border-red-600/20 bg-red-600/5 p-3">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-red-400" />
                <p className="text-[10px] uppercase tracking-wider text-red-400">Error Details</p>
              </div>
              <p className="text-xs text-red-300 leading-relaxed">
                Task {worker.task} failed at {worker.progress}% completion in {worker.domain} domain.
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

          {/* Token consumption sparkline */}
          <div className="rounded-lg border border-border/50 p-3">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Token Consumption Trend</p>
            <MiniAreaChart
              data={sparkline}
              dataKey="value"
              color={worker.status === 'error' ? COLORS.red : worker.status === 'busy' ? COLORS.emerald : '#6b7280'}
              height={60}
            />
          </div>

          {/* Task History */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Recent Task History</p>
            <div className="rounded-lg border border-border/50 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[10px] h-8">Task</TableHead>
                    <TableHead className="text-[10px] h-8">Result</TableHead>
                    <TableHead className="text-[10px] h-8">Duration</TableHead>
                    <TableHead className="text-[10px] h-8">Tokens</TableHead>
                    <TableHead className="text-[10px] h-8">Completed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((h) => (
                    <TableRow key={h.id}>
                      <TableCell className="text-xs font-mono py-1.5">{h.id}</TableCell>
                      <TableCell className="py-1.5">
                        {h.result === 'success' ? (
                          <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px]">
                            <CheckCircle2 className="mr-1 h-3 w-3" />PASS
                          </Badge>
                        ) : (
                          <Badge className="bg-red-600/15 text-red-400 border-0 text-[9px]">
                            <XCircle className="mr-1 h-3 w-3" />FAIL
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs py-1.5">{h.duration}</TableCell>
                      <TableCell className="text-xs tabular-nums py-1.5">{h.tokens.toLocaleString()}</TableCell>
                      <TableCell className="text-[10px] text-muted-foreground py-1.5">{h.completedAt}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2">
          {isIdle && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => {
                toast.success(`Task reassigned to ${worker.id}`, {
                  description: 'Next queued task will be assigned to this worker',
                })
                onOpenChange(false)
              }}
            >
              <ArrowRightLeft className="h-3.5 w-3.5" />
              Reassign Task
            </Button>
          )}
          <Button
            variant="destructive"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              toast.success(`${worker.id} terminated`, {
                description: 'Worker removed from the swarm pool',
              })
              onOpenChange(false)
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Terminate Worker
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function SwarmTab() {
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const ws = useSwarmWS()

  // Merge static base workers with live WebSocket updates
  const liveWorkers = useMemo(() => {
    return workers.map(base => {
      const wsUpdate = ws.workers[base.id]
      if (wsUpdate) {
        return {
          ...base,
          status: wsUpdate.status,
          task: wsUpdate.task,
          progress: wsUpdate.progress,
          tokens: wsUpdate.tokens,
          domain: wsUpdate.domain ?? base.domain,
        }
      }
      return base
    })
  }, [ws.workers])

  // Merge static task queue with live WebSocket queue
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

  // Merge recent completions with live data
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

  const busyCount = liveWorkers.filter(w => w.status === 'busy').length
  const idleCount = liveWorkers.filter(w => w.status === 'idle').length
  const errorCount = liveWorkers.filter(w => w.status === 'error').length
  const totalTokens = liveWorkers.reduce((s, w) => s + w.tokens, 0)

  // Live metrics from WebSocket
  const liveMetrics = ws.metrics ?? { throughput: 11.2, avgDuration: 12.4, successRate: 87.3, utilization: 60, totalTokens }

  const handleWorkerClick = (worker: Worker) => {
    setSelectedWorker(worker)
    setDialogOpen(true)
  }

  const handleAssignTask = (taskId: string) => {
    const idleWorker = liveWorkers.find(w => w.status === 'idle')
    if (idleWorker) {
      // Send via WebSocket
      const sent = ws.assignTask(taskId, idleWorker.id)
      if (sent) {
        toast.success(`Task ${taskId} assigned to ${idleWorker.id}`, {
          description: 'Worker will begin processing shortly via WebSocket',
        })
      } else {
        toast.success(`Task ${taskId} assigned to ${idleWorker.id}`, {
          description: 'Worker will begin processing shortly',
        })
      }
    } else {
      toast.error('No idle workers available', {
        description: 'All workers are busy or in error state',
      })
    }
  }

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
              <p className="text-xs text-muted-foreground">{busyCount} busy · {idleCount} idle · {errorCount} error · {totalTokens.toLocaleString()} total tokens</p>
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
                <p className="mt-1 text-3xl font-bold tabular-nums">{liveWorkers.length}</p>
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
          <span className="text-xs text-muted-foreground tabular-nums">{busyCount + errorCount}/{liveWorkers.length} workers occupied</span>
        </div>
        <div className="relative h-3 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-500"
            style={{ width: `${((busyCount + errorCount) / liveWorkers.length) * 100}%` }}
          />
        </div>
        <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground">
          <span>{((busyCount + errorCount) / liveWorkers.length * 100).toFixed(0)}% capacity utilized</span>
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
              <ExportButton data={liveWorkers.map(w => ({ ...w }))} filename="swarm-worker-status" label="Export Workers" columnHeaders={workerStatusColumnHeaders} />
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid gap-3 sm:grid-cols-2">
              {liveWorkers.map((w) => {
                const sparkline = workerSparklines[w.id] || []
                return (
                  <div
                    key={w.id}
                    onClick={() => handleWorkerClick(w)}
                    className={`relative rounded-lg border p-3.5 transition-all duration-200 cursor-pointer hover-lift ${
                      w.status === 'busy'
                        ? 'border-emerald-600/20 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent hover:border-emerald-600/40'
                        : w.status === 'error'
                        ? 'border-red-600/30 bg-gradient-to-br from-red-600/10 via-red-600/5 to-transparent hover:border-red-600/50 pulse-border'
                        : 'border-border bg-gradient-to-br from-muted/20 via-transparent to-transparent hover:border-border/80'
                    }`}
                  >
                    {/* Pulsing border for error workers */}
                    {w.status === 'error' && (
                      <div className="absolute inset-0 rounded-lg border-2 border-red-500/30 animate-pulse pointer-events-none" />
                    )}

                    {/* Status dot indicator */}
                    <div className={`absolute top-2 right-2 h-2 w-2 rounded-full ${
                      w.status === 'busy' ? 'bg-emerald-400 animate-pulse' :
                      w.status === 'error' ? 'bg-red-400 animate-pulse' :
                      'bg-muted-foreground/40'
                    }`} />
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{w.id}</span>
                        <Badge
                          className={`text-[9px] border-0 ${
                            w.status === 'busy'
                              ? 'bg-emerald-600/15 text-emerald-400'
                              : w.status === 'error'
                              ? 'bg-red-600/15 text-red-400'
                              : 'bg-muted text-muted-foreground'
                          }`}
                        >
                          {w.status === 'busy' && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
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
                    {/* Mini sparkline for token consumption */}
                    <div className="mt-2 h-8">
                      <MiniAreaChart
                        data={sparkline}
                        dataKey="value"
                        color={
                          w.status === 'error' ? COLORS.red :
                          w.status === 'busy' ? COLORS.emerald :
                          '#6b7280'
                        }
                        height={32}
                      />
                    </div>
                    <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
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
                    <td className="p-3 text-xs">{r.tokens.toLocaleString()}</td>
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
      />
    </div>
  )
}
