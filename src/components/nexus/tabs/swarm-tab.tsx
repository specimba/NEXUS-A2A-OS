'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Bug,
  Users,
  ListTodo,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Cpu,
  Zap,
} from 'lucide-react'

const workers = [
  { id: 'worker-1', status: 'active', trust: 0.92, cpu: 34, tasks: 47, failed: 2, domain: 'Research', currentTask: 'Vetting OR-Bench paper' },
  { id: 'worker-2', status: 'warning', trust: 0.78, cpu: 87, tasks: 31, failed: 5, domain: 'Coding', currentTask: 'Deploy pipeline v2' },
  { id: 'worker-3', status: 'active', trust: 0.85, cpu: 56, tasks: 38, failed: 3, domain: 'Analysis', currentTask: 'ISC-047 post-mortem' },
  { id: 'coordinator', status: 'active', trust: 0.95, cpu: 22, tasks: 12, failed: 0, domain: 'Governance', currentTask: 'Constitution monitoring' },
]

const taskQueue = [
  { id: 'T-142', task: 'Run ISC-048 stress test', assigned: 'worker-1', priority: 'high', status: 'in_progress' },
  { id: 'T-143', task: 'Vetting: Self-RAG paper', assigned: 'worker-3', priority: 'medium', status: 'in_progress' },
  { id: 'T-144', task: 'Deploy model pool update', assigned: 'worker-2', priority: 'high', status: 'queued' },
  { id: 'T-145', task: 'Export weekly snapshot', assigned: 'coordinator', priority: 'low', status: 'queued' },
  { id: 'T-146', task: 'Check rate limit status', assigned: 'unassigned', priority: 'low', status: 'pending' },
  { id: 'T-147', task: 'Validate GMR failover', assigned: 'unassigned', priority: 'medium', status: 'pending' },
]

const activityFeed = [
  { time: '1m ago', event: 'worker-1 completed vetting of OR-Bench paper', type: 'success' },
  { time: '3m ago', event: 'worker-2 error rate elevated to 34%', type: 'warning' },
  { time: '5m ago', event: 'coordinator initiated constitution check', type: 'info' },
  { time: '8m ago', event: 'worker-3 trust score increased to 0.85', type: 'success' },
  { time: '12m ago', event: 'T-140 completed: ISC-047 post-mortem', type: 'success' },
  { time: '15m ago', event: 'worker-2 auto-recovery initiated', type: 'warning' },
  { time: '20m ago', event: 'New task T-146 queued: Check rate limits', type: 'info' },
  { time: '25m ago', event: 'Swarm coordinator heartbeat OK', type: 'success' },
]

const statusStyles = {
  active: { color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500', label: 'Active' },
  warning: { color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-500', label: 'Warning' },
  inactive: { color: 'text-red-600 dark:text-red-400', bg: 'bg-red-500', label: 'Inactive' },
}

const taskStatusStyles = {
  in_progress: { icon: Zap, color: 'text-blue-600 dark:text-blue-400', label: 'In Progress' },
  queued: { icon: Clock, color: 'text-yellow-600 dark:text-yellow-400', label: 'Queued' },
  pending: { icon: ListTodo, color: 'text-muted-foreground', label: 'Pending' },
}

export function SwarmTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Bug className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">Swarm Monitor</h2>
        <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">4 workers</Badge>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">3</div>
            <div className="text-xs text-muted-foreground">Active Workers</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">1</div>
            <div className="text-xs text-muted-foreground">Warning</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">6</div>
            <div className="text-xs text-muted-foreground">Tasks in Queue</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">4h 23m</div>
            <div className="text-xs text-muted-foreground">Uptime</div>
          </CardContent>
        </Card>
      </div>

      {/* Worker Grid */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Users className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Worker Grid
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workers.map((worker) => {
              const style = statusStyles[worker.status as keyof typeof statusStyles]
              return (
                <div key={worker.id} className="p-4 rounded-lg bg-muted/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`h-2.5 w-2.5 rounded-full ${style.bg}`} />
                      <span className="text-sm font-bold">{worker.id}</span>
                      <Badge variant="outline" className="text-[10px] h-4">{worker.domain}</Badge>
                    </div>
                    <span className={`text-xs font-medium ${style.color}`}>{style.label}</span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div>
                      <div className="text-[10px] text-muted-foreground">Trust</div>
                      <div className="text-sm font-mono font-bold">{worker.trust.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-muted-foreground">Tasks</div>
                      <div className="text-sm font-mono">{worker.tasks}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-muted-foreground">Failed</div>
                      <div className={`text-sm font-mono ${worker.failed > 3 ? 'text-red-600 dark:text-red-400' : ''}`}>{worker.failed}</div>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground flex items-center gap-1"><Cpu className="h-3 w-3" /> CPU</span>
                      <span className="font-mono">{worker.cpu}%</span>
                    </div>
                    <Progress value={worker.cpu} className="h-1" />
                  </div>

                  <div className="text-[11px] text-muted-foreground truncate">
                    <span className="font-medium text-foreground">Current:</span> {worker.currentTask}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Task Queue */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ListTodo className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Task Queue
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {taskQueue.map((task) => {
                const taskStyle = taskStatusStyles[task.status as keyof typeof taskStatusStyles]
                const TaskIcon = taskStyle.icon
                return (
                  <div key={task.id} className="flex items-center gap-3 p-2 rounded-lg bg-muted/30">
                    <TaskIcon className={`h-3.5 w-3.5 shrink-0 ${taskStyle.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm truncate">{task.task}</div>
                      <div className="text-[10px] text-muted-foreground">{task.id} &middot; {task.assigned}</div>
                    </div>
                    <Badge
                      className={`text-[9px] h-4 border-0 ${
                        task.priority === 'high'
                          ? 'bg-red-600/20 text-red-600 dark:text-red-400'
                          : task.priority === 'medium'
                          ? 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400'
                          : 'bg-blue-600/20 text-blue-600 dark:text-blue-400'
                      }`}
                    >
                      {task.priority}
                    </Badge>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Activity Feed */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Activity Feed
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {activityFeed.map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                  {item.type === 'success' ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  ) : item.type === 'warning' ? (
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400 shrink-0" />
                  ) : (
                    <Activity className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                  )}
                  <span className="text-sm flex-1">{item.event}</span>
                  <span className="text-[10px] text-muted-foreground shrink-0">{item.time}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
