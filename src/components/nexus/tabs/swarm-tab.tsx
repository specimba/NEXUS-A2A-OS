'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Bug, Activity, CheckCircle2, XCircle, Clock, Loader2, Users, Cpu } from 'lucide-react'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'

const workers = [
  { id: 'worker-1', status: 'busy', task: 'T-0848', domain: 'code', progress: 67, tokens: 12400, uptime: '2h 34m' },
  { id: 'worker-2', status: 'error', task: 'T-0846', domain: 'research', progress: 34, tokens: 8200, uptime: '1h 12m' },
  { id: 'worker-3', status: 'busy', task: 'T-0849', domain: 'cyber', progress: 89, tokens: 18600, uptime: '3h 01m' },
  { id: 'worker-4', status: 'idle', task: null, domain: null, progress: 0, tokens: 0, uptime: '0h 45m' },
  { id: 'worker-5', status: 'idle', task: null, domain: null, progress: 0, tokens: 0, uptime: '0h 22m' },
]

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

export function SwarmTab() {
  const busyCount = workers.filter(w => w.status === 'busy').length
  const idleCount = workers.filter(w => w.status === 'idle').length
  const errorCount = workers.filter(w => w.status === 'error').length
  const totalTokens = workers.reduce((s, w) => s + w.tokens, 0)

  return (
    <div className="space-y-6 p-6">
      {/* Swarm Health Indicator */}
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
          <Badge className={`border-0 text-[10px] gap-1 ${errorCount > 0 ? 'bg-yellow-600/15 text-yellow-400' : 'bg-emerald-600/15 text-emerald-400'}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${errorCount > 0 ? 'bg-yellow-400' : 'bg-emerald-400'} animate-pulse`} />
            {errorCount > 0 ? 'Attention Needed' : 'Healthy'}
          </Badge>
        </div>
      </div>
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Workers</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{workers.length}</p>
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
            <CardTitle className="text-sm flex items-center gap-2">
              <Users className="h-4 w-4" /> Worker Status Grid
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid gap-3 sm:grid-cols-2">
              {workers.map((w) => (
                <div
                  key={w.id}
                  className={`rounded-md border p-3 ${
                    w.status === 'busy'
                      ? 'border-emerald-600/20 bg-emerald-600/5'
                      : w.status === 'error'
                      ? 'border-red-600/20 bg-red-600/5'
                      : 'border-border bg-card'
                  }`}
                >
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
                      <Progress value={w.progress} className="mt-1 h-1" />
                    </div>
                  )}
                  <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                    <span>{w.tokens > 0 ? `${w.tokens.toLocaleString()} tokens` : 'No task'}</span>
                    <span>↑ {w.uptime}</span>
                  </div>
                </div>
              ))}
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
              {taskQueue.map((t) => (
                <div key={t.id} className="flex items-center justify-between rounded-md bg-accent/30 px-3 py-2">
                  <div>
                    <span className="text-xs font-mono">{t.id}</span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <Badge variant="outline" className="text-[9px]">{t.domain}</Badge>
                      <Badge className={`text-[9px] border-0 ${t.priority === 'high' ? 'bg-red-600/15 text-red-400' : t.priority === 'medium' ? 'bg-yellow-600/15 text-yellow-400' : 'bg-muted text-muted-foreground'}`}>
                        {t.priority}
                      </Badge>
                    </div>
                  </div>
                  <span className="text-[10px] text-muted-foreground">{t.submittedBy}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-muted-foreground">{taskQueue.length} tasks queued</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Completed */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="h-4 w-4" /> Recent Completed
          </CardTitle>
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
                {recentCompleted.map((r) => (
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
    </div>
  )
}
