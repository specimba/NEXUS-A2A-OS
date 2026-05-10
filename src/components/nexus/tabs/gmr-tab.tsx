'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Router,
  ArrowRightLeft,
  Heart,
  Gauge,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Activity,
} from 'lucide-react'

const pools = [
  {
    name: 'PREMIUM',
    color: 'emerald',
    colorClass: 'text-emerald-600 dark:text-emerald-400',
    bgClass: 'bg-emerald-600/20',
    health: 97,
    models: [
      { name: 'trinity-large-preview', health: 98, latency: 142, successRate: 99.2, calls: 1247, status: 'active' },
      { name: 'minimax-m2.5', health: 95, latency: 189, successRate: 97.8, calls: 834, status: 'active' },
    ],
  },
  {
    name: 'MID',
    color: 'blue',
    colorClass: 'text-blue-600 dark:text-blue-400',
    bgClass: 'bg-blue-600/20',
    health: 89,
    models: [
      { name: 'qwen3-coder', health: 82, latency: 234, successRate: 91.4, calls: 2156, status: 'degraded' },
      { name: 'kimi-k2.5', health: 91, latency: 198, successRate: 95.2, calls: 1567, status: 'active' },
      { name: 'gpt-oss-120b', health: 94, latency: 156, successRate: 96.7, calls: 982, status: 'active' },
    ],
  },
  {
    name: 'FAST',
    color: 'orange',
    colorClass: 'text-orange-600 dark:text-orange-400',
    bgClass: 'bg-orange-600/20',
    health: 94,
    models: [
      { name: 'gemma-fast', health: 100, latency: 67, successRate: 99.8, calls: 3421, status: 'active' },
      { name: 'nemotron-3-super', health: 96, latency: 89, successRate: 98.1, calls: 1876, status: 'active' },
    ],
  },
]

const failoverLog = [
  { time: '35m ago', from: 'dolphin-mistral', to: 'trinity-large', reason: 'Health below 70% threshold', duration: '1.2s' },
  { time: '2h ago', from: 'qwen3-coder', to: 'gpt-oss-120b', reason: 'Latency spike (>500ms)', duration: '0.8s' },
  { time: '4h ago', from: 'kimi-k2.5', to: 'minimax-m2.5', reason: 'Error rate exceeded 5%', duration: '2.1s' },
]

const routingRules = [
  { pattern: 'code.*', pool: 'MID', priority: 1, description: 'Code tasks routed to MID pool' },
  { pattern: 'chat.*', pool: 'FAST', priority: 2, description: 'Chat tasks routed to FAST pool' },
  { pattern: 'analysis.*', pool: 'PREMIUM', priority: 1, description: 'Analysis routed to PREMIUM pool' },
  { pattern: 'research.*', pool: 'PREMIUM', priority: 1, description: 'Research tasks use premium models' },
  { pattern: 'default', pool: 'FAST', priority: 10, description: 'Fallback to FAST pool' },
]

export function GmrTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Router className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">GMR Router Panel</h2>
        <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">Active</Badge>
      </div>

      {/* Pool Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {pools.map((pool) => (
          <Card key={pool.name} className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${pool.bgClass}`} />
                  <span className="text-sm font-bold">{pool.name}</span>
                </div>
                <Badge className={`text-[10px] border-0 ${pool.bgClass} ${pool.colorClass}`}>
                  <Heart className="h-3 w-3 mr-1" />
                  {pool.health}%
                </Badge>
              </div>
              <Progress value={pool.health} className="h-1.5 mb-2" />
              <div className="text-[10px] text-muted-foreground">
                {pool.models.length} model{pool.models.length !== 1 ? 's' : ''} &middot; {pool.models.reduce((sum, m) => sum + m.calls, 0).toLocaleString()} calls
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Model Details by Pool */}
      {pools.map((pool) => (
        <Card key={`detail-${pool.name}`} className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${pool.bgClass}`} />
              {pool.name} Pool — Model Details
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {pool.models.map((model) => (
                <div key={model.name} className="p-3 rounded-lg bg-muted/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{model.name}</span>
                    {model.status === 'active' ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400" />
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="flex items-center gap-1">
                      <Heart className="h-3 w-3 text-muted-foreground" />
                      <span>Health: <span className="font-mono font-medium">{model.health}%</span></span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Gauge className="h-3 w-3 text-muted-foreground" />
                      <span>Latency: <span className="font-mono font-medium">{model.latency}ms</span></span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Zap className="h-3 w-3 text-muted-foreground" />
                      <span>Success: <span className="font-mono font-medium">{model.successRate}%</span></span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Activity className="h-3 w-3 text-muted-foreground" />
                      <span>Calls: <span className="font-mono font-medium">{model.calls.toLocaleString()}</span></span>
                    </div>
                  </div>
                  <Progress value={model.health} className="h-1" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Routing Rules */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Routing Rules
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {routingRules.map((rule, i) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-muted/30">
                  <code className="text-xs font-mono text-emerald-600 dark:text-emerald-400 min-w-[80px]">{rule.pattern}</code>
                  <ArrowRightLeft className="h-3 w-3 text-muted-foreground shrink-0" />
                  <Badge variant="outline" className="text-[10px] h-4">{rule.pool}</Badge>
                  <span className="text-[11px] text-muted-foreground flex-1">{rule.description}</span>
                  <span className="text-[10px] text-muted-foreground">P{rule.priority}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Failover Log */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Failover Log
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2">
              {failoverLog.map((entry, i) => (
                <div key={i} className="p-2 rounded-lg bg-muted/30 space-y-1">
                  <div className="flex items-center gap-2">
                    <code className="text-xs font-mono text-red-600 dark:text-red-400">{entry.from}</code>
                    <span className="text-muted-foreground">&rarr;</span>
                    <code className="text-xs font-mono text-emerald-600 dark:text-emerald-400">{entry.to}</code>
                    <span className="flex-1" />
                    <span className="text-[10px] text-muted-foreground">{entry.time}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>{entry.reason}</span>
                    <span className="text-border">|</span>
                    <span>Failover: {entry.duration}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
