'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
  Network,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useNexusStore } from '@/store/nexus-store'

const pools = [
  {
    name: 'PREMIUM',
    color: 'emerald',
    colorClass: 'text-emerald-600 dark:text-emerald-400',
    bgClass: 'bg-emerald-600/20',
    health: 97,
    models: [
      { name: 'trinity-large-preview', health: 98, latency: 142, successRate: 99.2, calls: 1247, status: 'active', provider: 'OpenRouter' },
      { name: 'glm-4.7 (z-ai)', health: 95, latency: 189, successRate: 97.8, calls: 834, status: 'active', provider: 'Z-AI' },
    ],
  },
  {
    name: 'MID',
    color: 'blue',
    colorClass: 'text-blue-600 dark:text-blue-400',
    bgClass: 'bg-blue-600/20',
    health: 89,
    models: [
      { name: 'qwen3-coder', health: 82, latency: 234, successRate: 91.4, calls: 2156, status: 'degraded', provider: 'OpenRouter' },
      { name: 'DeepSeek V3', health: 91, latency: 198, successRate: 95.2, calls: 1567, status: 'active', provider: 'SambaNova' },
      { name: 'Nemotron Super 128K', health: 94, latency: 156, successRate: 96.7, calls: 982, status: 'active', provider: 'OpenRouter' },
    ],
  },
  {
    name: 'FAST',
    color: 'orange',
    colorClass: 'text-orange-600 dark:text-orange-400',
    bgClass: 'bg-orange-600/20',
    health: 94,
    models: [
      { name: 'gemma-fast (Groq)', health: 100, latency: 67, successRate: 99.8, calls: 3421, status: 'active', provider: 'Groq' },
      { name: 'llama-3.3-70b (Cerebras)', health: 96, latency: 40, successRate: 98.1, calls: 1876, status: 'active', provider: 'Cerebras' },
    ],
  },
]

const failoverLog = [
  { time: '35m ago', from: 'dolphin-mistral', to: 'trinity-large', reason: 'Health below 70% threshold', duration: '1.2s' },
  { time: '2h ago', from: 'qwen3-coder', to: 'Nemotron Super 128K', reason: 'Latency spike (>500ms)', duration: '0.8s' },
  { time: '4h ago', from: 'kimi-k2.5', to: 'glm-4.7', reason: 'Error rate exceeded 5%', duration: '2.1s' },
]

const routingRules = [
  { pattern: 'code.*', pool: 'MID', priority: 1, description: 'Code tasks routed to MID pool', modelRelay: 'zai/glm-4-7 → nvidia/llama-3.3-70b' },
  { pattern: 'chat.*', pool: 'FAST', priority: 2, description: 'Chat tasks routed to FAST pool', modelRelay: 'groq/llama-3.3-70b → cerebras/llama-3.3-70b' },
  { pattern: 'analysis.*', pool: 'PREMIUM', priority: 1, description: 'Analysis routed to PREMIUM pool', modelRelay: 'zai/glm-4-7 → nvidia/nemotron-4-340b' },
  { pattern: 'research.*', pool: 'PREMIUM', priority: 1, description: 'Research tasks use premium models', modelRelay: 'zai/glm-4-7 → openrouter/gemini-2.5-pro' },
  { pattern: 'default', pool: 'FAST', priority: 10, description: 'Fallback to FAST pool', modelRelay: 'groq/mixtral-8x7b → cerebras/llama-3.1-8b' },
]

export function GmrTab() {
  const setActiveTab = useNexusStore(s => s.setActiveTab)
  // Client-side data — no API call needed
  const relayHealth: { status: string; providersAvailable: number } = {
    status: 'operational',
    providersAvailable: 13,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Router className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold">GMR Router Panel</h2>
          <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">Active</Badge>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5 h-8"
          onClick={() => setActiveTab('modelrelay')}
        >
          <Network className="h-3 w-3" />
          Open ModelRelay
        </Button>
      </div>

      {/* ModelRelay Integration Banner */}
      <Card className="bg-gradient-to-r from-emerald-600/10 to-emerald-600/5 border-emerald-600/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600/20">
                <Network className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">ModelRelay Gateway Connected</span>
                  <Badge className={cn(
                    'text-[9px] border-0',
                    relayHealth?.status === 'operational' ? 'bg-emerald-600/20 text-emerald-600' : 'bg-yellow-600/20 text-yellow-600'
                  )}>
                    {relayHealth?.status === 'operational' ? 'OPERATIONAL' : 'CHECKING...'}
                  </Badge>
                </div>
                <span className="text-[11px] text-muted-foreground">
                  {relayHealth?.providersAvailable || 0} providers available &middot; Intent classification &middot; Fallback cascade &middot; Quota-aware routing
                </span>
              </div>
            </div>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1.5 h-7 text-emerald-600 hover:text-emerald-700"
              onClick={() => setActiveTab('modelrelay')}
            >
              View Gateway →
            </Button>
          </div>
        </CardContent>
      </Card>

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
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{model.name}</span>
                    </div>
                    {model.status === 'active' ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400" />
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="outline" className="text-[9px] h-3.5">{model.provider}</Badge>
                    <Badge variant={model.status === 'active' ? 'secondary' : 'outline'} className={cn(
                      'text-[9px] h-3.5',
                      model.status === 'active' ? 'bg-emerald-600/10 text-emerald-600 border-0' : ''
                    )}>
                      {model.status}
                    </Badge>
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
        {/* Routing Rules with ModelRelay fallback chains */}
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
                <div key={i} className="p-2 rounded-lg bg-muted/30 space-y-1">
                  <div className="flex items-center gap-3">
                    <code className="text-xs font-mono text-emerald-600 dark:text-emerald-400 min-w-[80px]">{rule.pattern}</code>
                    <ArrowRightLeft className="h-3 w-3 text-muted-foreground shrink-0" />
                    <Badge variant="outline" className="text-[10px] h-4">{rule.pool}</Badge>
                    <span className="text-[11px] text-muted-foreground flex-1">{rule.description}</span>
                    <span className="text-[10px] text-muted-foreground">P{rule.priority}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground ml-2">
                    <Network className="h-3 w-3 text-violet-500" />
                    <span className="font-mono">ModelRelay: {rule.modelRelay}</span>
                  </div>
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
