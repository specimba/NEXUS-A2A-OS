'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  Users,
  Shield,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'

const healthCards = [
  { label: 'CPU Load', value: 34, unit: '%', icon: Cpu, trend: 'down', color: 'emerald' },
  { label: 'Memory', value: 62, unit: '%', icon: HardDrive, trend: 'up', color: 'yellow' },
  { label: 'API Latency', value: 142, unit: 'ms', icon: Zap, trend: 'down', color: 'emerald' },
  { label: 'Uptime', value: 99.7, unit: '%', icon: Activity, trend: 'up', color: 'emerald' },
]

const agents = [
  { name: 'worker-1', status: 'active', trust: 0.92, tasks: 47, domain: 'Research', model: 'trinity-large' },
  { name: 'worker-2', status: 'warning', trust: 0.78, tasks: 31, domain: 'Coding', model: 'qwen3-coder' },
  { name: 'worker-3', status: 'active', trust: 0.85, tasks: 38, domain: 'Analysis', model: 'gemma-fast' },
  { name: 'coordinator', status: 'active', trust: 0.95, tasks: 12, domain: 'Governance', model: 'glm-4.7' },
]

const recentModelUsage = [
  { model: 'trinity-large', agent: 'worker-1', type: 'completion', tokens: 2450, time: '1m ago' },
  { model: 'qwen3-coder', agent: 'worker-2', type: 'prompt', tokens: 1820, time: '3m ago' },
  { model: 'gemma-fast', agent: 'worker-3', type: 'completion', tokens: 980, time: '5m ago' },
  { model: 'glm-4.7', agent: 'coordinator', type: 'prompt', tokens: 3200, time: '8m ago' },
  { model: 'trinity-large', agent: 'worker-1', type: 'prompt', tokens: 1560, time: '12m ago' },
  { model: 'gemma-fast', agent: 'worker-3', type: 'completion', tokens: 720, time: '15m ago' },
]

const modelPools = [
  { name: 'PREMIUM', models: ['trinity-large-preview', 'minimax-m2.5'], health: 97, color: 'emerald' },
  { name: 'MID', models: ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'], health: 89, color: 'blue' },
  { name: 'FAST', models: ['gemma-fast', 'nemotron-3-super'], health: 94, color: 'orange' },
]

const recentActivity = [
  { time: '2m ago', event: 'Governor blocked CRITICAL action', type: 'warning' as const, source: 'Governor' },
  { time: '5m ago', event: 'StressLab test ISC-001 completed', type: 'success' as const, source: 'StressLab' },
  { time: '10m ago', event: 'Token budget at 73.4%', type: 'info' as const, source: 'Tokens' },
  { time: '15m ago', event: 'New research paper vetted: OR-Bench', type: 'success' as const, source: 'Research' },
  { time: '20m ago', event: 'GMR pool FAST: all models healthy', type: 'success' as const, source: 'GMR' },
  { time: '25m ago', event: 'Agent worker-3 trust score increased', type: 'info' as const, source: 'Governor' },
  { time: '30m ago', event: 'Constitution check passed', type: 'success' as const, source: 'Vault' },
]

const typeStyles = {
  success: 'text-emerald-600 dark:text-emerald-400',
  warning: 'text-yellow-600 dark:text-yellow-400',
  info: 'text-blue-600 dark:text-blue-400',
}

const statusStyles = {
  active: 'bg-emerald-500',
  warning: 'bg-yellow-500',
  inactive: 'bg-red-500',
}

export function OverviewTab() {
  return (
    <div className="space-y-6">
      {/* Health Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {healthCards.map((card) => (
          <Card key={card.label} className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <card.icon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">{card.label}</span>
                </div>
                <Badge variant="outline" className={`text-[10px] ${card.trend === 'down' ? 'text-emerald-600 dark:text-emerald-400' : 'text-yellow-600 dark:text-yellow-400'}`}>
                  {card.trend === 'down' ? <ArrowDownRight className="h-3 w-3 mr-0.5" /> : <ArrowUpRight className="h-3 w-3 mr-0.5" />}
                  {card.trend === 'down' ? 'Good' : 'Watch'}
                </Badge>
              </div>
              <div className="mt-2">
                <span className="text-2xl font-bold">{card.value}</span>
                <span className="text-sm text-muted-foreground ml-1">{card.unit}</span>
              </div>
              {card.label !== 'Uptime' && (
                <Progress value={card.label === 'API Latency' ? Math.min(card.value / 3, 100) : card.value} className="mt-2 h-1" />
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Agent Status */}
        <Card className="bg-card/50 border-border/50 lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Users className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Agent Status
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {agents.map((agent) => (
                <div key={agent.name} className="flex items-center gap-3 p-2 rounded-lg bg-muted/30">
                  <span className={`h-2 w-2 rounded-full ${statusStyles[agent.status as keyof typeof statusStyles]}`} />
                  <span className="text-sm font-medium">{agent.name}</span>
                  <span className="text-[10px] font-mono text-muted-foreground">{agent.model}</span>
                  <span className="flex-1" />
                  <Badge variant="outline" className="text-[10px]">{agent.domain}</Badge>
                  <div className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-muted-foreground" />
                    <span className="text-xs font-mono">{agent.trust.toFixed(2)}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{agent.tasks} tasks</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Model Pool Status */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Model Pools
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {modelPools.map((pool) => (
                <div key={pool.name} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{pool.name}</span>
                    <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400">{pool.health}%</span>
                  </div>
                  <Progress value={pool.health} className="h-1.5" />
                  <div className="flex flex-wrap gap-1">
                    {pool.models.map((model) => (
                      <Badge key={model} variant="secondary" className="text-[9px] h-4">{model}</Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Model Usage */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Usage
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {recentModelUsage.map((entry, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                <Zap className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="text-sm font-mono">{entry.model}</span>
                <Badge variant="outline" className="text-[9px] h-4">{entry.agent}</Badge>
                <Badge variant="secondary" className="text-[9px] h-4">{entry.type}</Badge>
                <span className="flex-1" />
                <span className="text-xs font-mono text-muted-foreground">{entry.tokens.toLocaleString()} tok</span>
                <span className="text-[10px] text-muted-foreground">{entry.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {recentActivity.map((item, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                {item.type === 'success' ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                ) : item.type === 'warning' ? (
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 shrink-0" />
                ) : (
                  <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" />
                )}
                <span className="text-sm flex-1">{item.event}</span>
                <Badge variant="outline" className="text-[10px] shrink-0">{item.source}</Badge>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">{item.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
