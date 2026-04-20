'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { MiniAreaChart, NexusBarChart, NexusGauge, COLORS } from '@/components/nexus/charts'
import {
  Zap,
  Shield,
  Router,
  Database,
  FlaskConical,
  Bug,
  Activity,
  Settings,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  MemoryStick,
  Radio,
} from 'lucide-react'
import { useEffect, useState, useCallback } from 'react'

const pillars = [
  { name: 'Bridge', icon: Zap, status: 'operational', health: 100, desc: 'HMAC auth · JSON-RPC', uptime: '99.99%' },
  { name: 'Engine', icon: Router, status: 'operational', health: 98, desc: 'Hermes intent routing', uptime: '99.94%' },
  { name: 'Governor', icon: Shield, status: 'operational', health: 95, desc: 'Kaiju + TrustScorer', uptime: '99.87%' },
  { name: 'Vault', icon: Database, status: 'operational', health: 100, desc: '5-Track memory', uptime: '100%' },
  { name: 'GMR', icon: Router, status: 'operational', health: 92, desc: 'Model rotation', uptime: '99.71%' },
  { name: 'Swarm', icon: Bug, status: 'degraded', health: 88, desc: 'Worker pool', uptime: '98.44%' },
  { name: 'Monitor', icon: Activity, status: 'operational', health: 96, desc: 'Token budget + audit', uptime: '99.92%' },
  { name: 'Config', icon: Settings, status: 'operational', health: 100, desc: 'Constitution', uptime: '100%' },
]

const tokenHistory = [
  { name: '10m', value: 89000 },
  { name: '8m', value: 86500 },
  { name: '6m', value: 84200 },
  { name: '4m', value: 80100 },
  { name: '2m', value: 77300 },
  { name: 'now', value: 73450 },
]

const agentActivity = [
  { name: 'Mon', tasks: 45, errors: 3 },
  { name: 'Tue', tasks: 52, errors: 5 },
  { name: 'Wed', tasks: 38, errors: 2 },
  { name: 'Thu', tasks: 61, errors: 4 },
  { name: 'Fri', tasks: 49, errors: 1 },
  { name: 'Sat', tasks: 33, errors: 0 },
  { name: 'Sun', tasks: 28, errors: 1 },
]

const modelDistribution = [
  { name: 'qwen3-coder', value: 34 },
  { name: 'trinity', value: 28 },
  { name: 'gemma-fast', value: 18 },
  { name: 'nemotron', value: 12 },
  { name: 'others', value: 8 },
]

const initialActivities = [
  { time: '0s ago', event: 'Agent worker-3 completed task T-0847', type: 'success' },
  { time: '3s ago', event: 'GMR rotated to trinity-large-preview', type: 'info' },
  { time: '8s ago', event: 'Governor ALLOWED read file (scope: SELF)', type: 'info' },
  { time: '15s ago', event: 'Vault stored TRUST entry for agent-alpha', type: 'success' },
  { time: '22s ago', event: 'StressLab test ISC-023 completed: PASS', type: 'success' },
  { time: '34s ago', event: 'TokenGuard budget check: 73,450 remaining', type: 'info' },
  { time: '1m ago', event: 'Swarm worker-1 status: ERROR → recovering', type: 'warning' },
  { time: '2m ago', event: 'Bridge verified HMAC signature for agent-beta', type: 'info' },
  { time: '3m ago', event: 'Model gemma-fast health check: 100%', type: 'info' },
  { time: '4m ago', event: 'Vault stored GOV entry: constitution.check', type: 'success' },
  { time: '5m ago', event: 'Swarm foreman reassigned task T-0844', type: 'info' },
  { time: '6m ago', event: 'Governor DENIED worker-2: delete_all (CRIT)', type: 'warning' },
]

const newActivities = [
  { event: 'Model kimi-k2.5 health check: 92%', type: 'info' as const },
  { event: 'Agent worker-3 started task T-0850', type: 'info' as const },
  { event: 'GMR pool FAST: all models healthy', type: 'success' as const },
  { event: 'Vault stored CAP entry: skill.registered', type: 'success' as const },
  { event: 'Governor HELD research-agent: API call (CROSS)', type: 'warning' as const },
  { event: 'TokenTracker: 1,240 tokens consumed by qwen3-coder', type: 'info' as const },
  { event: 'Swarm worker-4 now idle, ready for assignment', type: 'success' as const },
  { event: 'Bridge: new HMAC session established', type: 'info' as const },
]

function LiveActivityFeed() {
  const [activities, setActivities] = useState(initialActivities)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setTick((t) => t + 1)
      const newItem = newActivities[tick % newActivities.length]
      setActivities((prev) => [
        { ...newItem, time: '0s ago' },
        ...prev.slice(0, -1).map((a) => ({
          ...a,
          time: a.time === '0s ago' ? '1s ago' : a.time,
        })),
      ])
    }, 3000)
    return () => clearInterval(interval)
  }, [tick])

  return (
    <div className="max-h-72 space-y-1.5 overflow-y-auto pr-1 custom-scrollbar">
      {activities.map((item, i) => (
        <div
          key={`${item.event}-${i}`}
          className={`flex items-start gap-2 rounded-md px-2 py-1.5 text-xs transition-colors ${
            i === 0 ? 'bg-emerald-600/5' : ''
          }`}
        >
          {item.type === 'success' && <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-emerald-400" />}
          {item.type === 'info' && <Radio className="mt-0.5 h-3 w-3 shrink-0 text-blue-400" />}
          {item.type === 'warning' && <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-orange-400" />}
          <span className="flex-1 text-muted-foreground">{item.event}</span>
          <span className="shrink-0 text-[10px] text-muted-foreground/50 tabular-nums">{item.time}</span>
        </div>
      ))}
    </div>
  )
}

export function OverviewTab() {
  const [systemPulse, setSystemPulse] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setSystemPulse((p) => p + 1)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6 p-6">
      {/* Top Stats with Gradient Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="relative overflow-hidden border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Token Budget</p>
                <p className="mt-1 text-3xl font-bold text-emerald-400 tabular-nums">73,450</p>
                <p className="text-[10px] text-muted-foreground">of 100,000 remaining</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Activity className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
            <div className="mt-3">
              <Progress value={73.45} className="h-2 bg-emerald-900/20" />
            </div>
            <div className="mt-2">
              <MiniAreaChart data={tokenHistory} dataKey="value" color={COLORS.emerald} height={32} />
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Active Agents</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">3</p>
                <p className="text-[10px] text-muted-foreground">of 5 max concurrent</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Bug className="h-5 w-5 text-blue-400" />
              </div>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2">
              <div className="rounded-md bg-emerald-600/10 px-2 py-1 text-center">
                <p className="text-xs font-bold text-emerald-400">2</p>
                <p className="text-[9px] text-muted-foreground">busy</p>
              </div>
              <div className="rounded-md bg-muted px-2 py-1 text-center">
                <p className="text-xs font-bold">1</p>
                <p className="text-[9px] text-muted-foreground">idle</p>
              </div>
              <div className="rounded-md bg-red-600/10 px-2 py-1 text-center">
                <p className="text-xs font-bold text-red-400">1</p>
                <p className="text-[9px] text-muted-foreground">error</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">StressLab Runs</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">47</p>
                <p className="text-[10px] text-muted-foreground">12 templates tested</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                <FlaskConical className="h-5 w-5 text-orange-400" />
              </div>
            </div>
            <div className="mt-3">
              <MiniAreaChart
                data={[
                  { name: '1', value: 3 },
                  { name: '2', value: 7 },
                  { name: '3', value: 5 },
                  { name: '4', value: 12 },
                  { name: '5', value: 8 },
                  { name: '6', value: 12 },
                ]}
                dataKey="value"
                color={COLORS.orange}
                height={32}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Collapse Rate</p>
                <p className="mt-1 text-3xl font-bold text-red-400 tabular-nums">23.4%</p>
                <p className="text-[10px] text-muted-foreground">↓ from 95.3% baseline</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                <AlertTriangle className="h-5 w-5 text-red-400" />
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Progress value={23.4} className="h-2 flex-1 bg-red-900/20" />
              <span className="text-[10px] text-emerald-400 font-medium">-72pp</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 8-Pillar Health Grid */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">System Pillars</h2>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] text-muted-foreground">All systems nominal</span>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {pillars.map((p) => (
            <Card key={p.name} className="group relative overflow-hidden hover:border-emerald-600/30 transition-all duration-200 hover:shadow-md hover:shadow-emerald-600/5">
              <div className={`absolute inset-0 bg-gradient-to-br ${
                p.health === 100 ? 'from-emerald-600/5 via-transparent to-transparent' :
                p.health >= 95 ? 'from-emerald-600/3 via-transparent to-transparent' :
                'from-yellow-600/5 via-transparent to-transparent'
              }`} />
              <CardContent className="relative p-4">
                <div className="flex items-start gap-3">
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                    p.health === 100 ? 'bg-emerald-600/10' :
                    p.health >= 95 ? 'bg-emerald-600/8' :
                    'bg-yellow-600/10'
                  }`}>
                    <p.icon className={`h-4 w-4 ${
                      p.health === 100 ? 'text-emerald-400' :
                      p.health >= 95 ? 'text-emerald-500' :
                      'text-yellow-400'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{p.name}</span>
                      <Badge
                        variant="secondary"
                        className={`h-5 text-[10px] border-0 ${
                          p.health === 100 ? 'bg-emerald-600/15 text-emerald-400' :
                          p.health >= 95 ? 'bg-emerald-600/10 text-emerald-500' :
                          'bg-yellow-600/15 text-yellow-400'
                        }`}
                      >
                        {p.health}%
                      </Badge>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{p.desc}</p>
                    <div className="flex items-center justify-between mt-1">
                      <Progress value={p.health} className="h-1 flex-1" />
                      <span className="text-[9px] text-muted-foreground ml-2">{p.uptime}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Middle Row: Charts */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Weekly Activity Chart */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Weekly Agent Activity</CardTitle>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-400" /> Tasks</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-red-400" /> Errors</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <NexusBarChart
              data={agentActivity}
              dataKey="tasks"
              nameKey="name"
              color={COLORS.emerald}
              height={140}
            />
          </CardContent>
        </Card>

        {/* Token Budget Gauge */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Budget Utilization</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <NexusGauge value={73450} max={100000} color={COLORS.emerald} label="tokens used" height={140} />
          </CardContent>
        </Card>
      </div>

      {/* Bottom Row: Activity Feed + Quick Stats */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Activity Feed */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Radio className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
                Live Activity Feed
              </CardTitle>
              <Badge variant="outline" className="text-[9px]">real-time</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-3 pt-0">
            <LiveActivityFeed />
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Governance Stats</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Governor Decisions (24h)</span>
                <div className="flex gap-1.5">
                  <Badge className="bg-emerald-600/15 text-emerald-400 border-0 hover:bg-emerald-600/20 text-[10px]">ALLOW 847</Badge>
                  <Badge className="bg-red-600/15 text-red-400 border-0 hover:bg-red-600/20 text-[10px]">DENY 23</Badge>
                  <Badge className="bg-yellow-600/15 text-yellow-400 border-0 hover:bg-yellow-600/20 text-[10px]">HOLD 5</Badge>
                </div>
              </div>
              <Separator className="bg-border/50" />
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-accent/30 p-2.5">
                  <div className="flex items-center gap-1.5">
                    <TrendingUp className="h-3 w-3 text-emerald-400" />
                    <span className="text-[10px] text-muted-foreground">Trust Avg</span>
                  </div>
                  <p className="mt-1 text-sm font-bold text-emerald-400">0.73</p>
                </div>
                <div className="rounded-lg bg-accent/30 p-2.5">
                  <div className="flex items-center gap-1.5">
                    <Database className="h-3 w-3 text-blue-400" />
                    <span className="text-[10px] text-muted-foreground">VAP Chain</span>
                  </div>
                  <p className="mt-1 text-sm font-bold">1,247</p>
                </div>
                <div className="rounded-lg bg-accent/30 p-2.5">
                  <div className="flex items-center gap-1.5">
                    <Cpu className="h-3 w-3 text-orange-400" />
                    <span className="text-[10px] text-muted-foreground">API Calls</span>
                  </div>
                  <p className="mt-1 text-sm font-bold">12 <span className="text-[10px] text-muted-foreground font-normal">/ 20</span></p>
                </div>
                <div className="rounded-lg bg-accent/30 p-2.5">
                  <div className="flex items-center gap-1.5">
                    <MemoryStick className="h-3 w-3 text-purple-400" />
                    <span className="text-[10px] text-muted-foreground">Writes</span>
                  </div>
                  <p className="mt-1 text-sm font-bold">8 <span className="text-[10px] text-muted-foreground font-normal">/ 30</span></p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Separator({ className }: { className?: string }) {
  return <div className={`h-px ${className || 'bg-border'}`} />
}
