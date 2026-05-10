'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Coins,
  TrendingUp,
  TrendingDown,
  Flame,
  Clock,
  BarChart3,
  Wallet,
  ArrowUpRight,
} from 'lucide-react'

const budgetSummary = {
  total: 100000,
  used: 26550,
  remaining: 73450,
  burnRate: 142,
  estimatedTimeLeft: '8h 35m',
  percentUsed: 26.55,
}

const usageByModel = [
  { model: 'trinity-large-preview', tokens: 8420, cost: 12.63, percent: 31.7, trend: 'up' },
  { model: 'qwen3-coder', tokens: 6230, cost: 3.12, percent: 23.5, trend: 'up' },
  { model: 'gemma-fast', tokens: 4580, cost: 0.46, percent: 17.2, trend: 'down' },
  { model: 'kimi-k2.5', tokens: 3420, cost: 1.71, percent: 12.9, trend: 'down' },
  { model: 'nemotron-3-super', tokens: 2190, cost: 0.44, percent: 8.2, trend: 'up' },
  { model: 'gpt-oss-120b', tokens: 1710, cost: 1.28, percent: 6.5, trend: 'down' },
]

const usageByAgent = [
  { agent: 'worker-1', model: 'trinity-large', tokens: 9870, percent: 37.2, tasks: 47 },
  { agent: 'worker-2', model: 'qwen3-coder', tokens: 7230, percent: 27.2, tasks: 31 },
  { agent: 'worker-3', model: 'gemma-fast', tokens: 5680, percent: 21.4, tasks: 38 },
  { agent: 'coordinator', model: 'glm-4.7', tokens: 3770, percent: 14.2, tasks: 12 },
]

const recentUsage = [
  { time: '1m ago', model: 'trinity-large', agent: 'worker-1', tokens: 2450, type: 'completion' },
  { time: '3m ago', model: 'qwen3-coder', agent: 'worker-2', tokens: 1820, type: 'prompt' },
  { time: '5m ago', model: 'gemma-fast', agent: 'worker-3', tokens: 980, type: 'completion' },
  { time: '8m ago', model: 'trinity-large', agent: 'coordinator', tokens: 3200, type: 'prompt' },
  { time: '12m ago', model: 'kimi-k2.5', agent: 'worker-1', tokens: 1560, type: 'completion' },
  { time: '15m ago', model: 'nemotron-3', agent: 'worker-3', tokens: 720, type: 'prompt' },
]

// Simple bar chart using CSS
function MiniBarChart({ data, maxValue }: { data: number[]; maxValue: number }) {
  return (
    <div className="flex items-end gap-1 h-12">
      {data.map((value, i) => (
        <div
          key={i}
          className="flex-1 bg-emerald-600/60 dark:bg-emerald-400/60 rounded-t transition-all duration-300 min-w-[4px]"
          style={{ height: `${Math.max((value / maxValue) * 100, 4)}%` }}
        />
      ))}
    </div>
  )
}

export function TokensTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Coins className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">Token Budget</h2>
      </div>

      {/* Budget Overview */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-2">
                <Wallet className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Total Budget</span>
              </div>
              <div className="text-3xl font-bold">{budgetSummary.total.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-2">Used</div>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">{budgetSummary.used.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-2">Remaining</div>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{budgetSummary.remaining.toLocaleString()}</div>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Flame className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                <span className="text-xs text-muted-foreground">Burn Rate</span>
              </div>
              <div className="text-2xl font-bold">{budgetSummary.burnRate} <span className="text-sm font-normal text-muted-foreground">tok/min</span></div>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Est. Time Left</span>
              </div>
              <div className="text-2xl font-bold">{budgetSummary.estimatedTimeLeft}</div>
            </div>
          </div>

          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span>Budget Usage</span>
              <span className="font-mono">{budgetSummary.percentUsed.toFixed(1)}%</span>
            </div>
            <Progress value={budgetSummary.percentUsed} className="h-2" />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Usage by Model */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Usage by Model
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {usageByModel.map((model) => (
                <div key={model.model} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{model.model}</span>
                      {model.trend === 'up' ? (
                        <TrendingUp className="h-3 w-3 text-red-600 dark:text-red-400" />
                      ) : (
                        <TrendingDown className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{model.tokens.toLocaleString()} tok</span>
                      <span>${model.cost.toFixed(2)}</span>
                      <span className="font-mono">{model.percent}%</span>
                    </div>
                  </div>
                  <Progress value={model.percent} className="h-1.5" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Usage by Agent */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ArrowUpRight className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Usage by Agent
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {usageByAgent.map((agent) => (
                <div key={agent.agent} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{agent.agent}</span>
                      <Badge variant="secondary" className="text-[9px] h-4 font-mono">{agent.model}</Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{agent.tokens.toLocaleString()} tok</span>
                      <span>{agent.tasks} tasks</span>
                      <span className="font-mono">{agent.percent}%</span>
                    </div>
                  </div>
                  <Progress value={agent.percent} className="h-1.5" />
                </div>
              ))}
            </div>

            {/* Mini Chart */}
            <div className="mt-4 pt-3 border-t border-border/50">
              <div className="text-[10px] text-muted-foreground mb-2">Hourly usage (last 12h)</div>
              <MiniBarChart
                data={[1200, 1800, 2400, 1600, 3200, 2800, 1900, 2200, 1500, 2100, 1800, 2600]}
                maxValue={3200}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Usage Log */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Usage
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2">
            {recentUsage.map((entry, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                <Coins className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="text-sm">{entry.model}</span>
                <Badge variant="outline" className="text-[9px] h-4">{entry.agent}</Badge>
                <Badge variant="secondary" className="text-[9px] h-4">{entry.type}</Badge>
                <span className="flex-1" />
                <span className="text-xs font-mono">{entry.tokens.toLocaleString()} tok</span>
                <span className="text-[10px] text-muted-foreground">{entry.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
