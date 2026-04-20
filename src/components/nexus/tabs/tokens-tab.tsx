'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Coins, TrendingDown, TrendingUp, AlertTriangle, PieChart } from 'lucide-react'

const agentUsage = [
  { name: 'worker-3', tokens: 18600, pct: 25.3, trend: 'up', model: 'qwen3-coder' },
  { name: 'worker-1', tokens: 12400, pct: 16.9, trend: 'up', model: 'trinity-large' },
  { name: 'coordinator', tokens: 8200, pct: 11.2, trend: 'down', model: 'gemma-fast' },
  { name: 'worker-2', tokens: 8200, pct: 11.2, trend: 'up', model: 'nemotron-3' },
  { name: 'research-agent', tokens: 5100, pct: 6.9, trend: 'down', model: 'kimi-k2.5' },
]

const modelUsage = [
  { model: 'gemma-fast', tokens: 22400, calls: 1024, avgLatency: '340ms', cost: 0 },
  { model: 'trinity-large-preview', tokens: 18200, calls: 512, avgLatency: '1350ms', cost: 0 },
  { model: 'qwen3-coder', tokens: 15800, calls: 347, avgLatency: '1200ms', cost: 0 },
  { model: 'nemotron-3-super', tokens: 8900, calls: 234, avgLatency: '890ms', cost: 0 },
  { model: 'kimi-k2.5', tokens: 5400, calls: 156, avgLatency: '980ms', cost: 0 },
  { model: 'gpt-oss-120b', tokens: 3200, calls: 298, avgLatency: '760ms', cost: 0 },
]

const budgetAlerts = [
  { level: 'warning', msg: 'worker-2 approaching rate limit (85% of hourly budget)', time: '5m ago' },
  { level: 'info', msg: 'Session budget 73.4% consumed — 26,550 remaining', time: '1m ago' },
  { level: 'info', msg: 'FREE_RESEARCH pool: all models within limits', time: '3m ago' },
]

export function TokensTab() {
  const totalUsed = 73500
  const totalBudget = 100000
  const remaining = totalBudget - totalUsed
  const pct = (totalUsed / totalBudget) * 100

  return (
    <div className="space-y-6 p-6">
      {/* Main Budget Card */}
      <Card className="border-emerald-600/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Session Token Budget</h2>
              <p className="text-sm text-muted-foreground">Current active session monitoring</p>
            </div>
            <Coins className="h-8 w-8 text-emerald-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-bold">{totalUsed.toLocaleString()}</span>
            <span className="text-lg text-muted-foreground mb-1">/ {totalBudget.toLocaleString()}</span>
          </div>
          <Progress value={pct} className="mt-4 h-3" />
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>{pct.toFixed(1)}% used</span>
            <span className="text-emerald-400">{remaining.toLocaleString()} remaining</span>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Per-Agent Breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <PieChart className="h-4 w-4" /> Per-Agent Token Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {agentUsage.map((a) => (
                <div key={a.name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{a.name}</span>
                      <Badge variant="outline" className="text-[9px]">{a.model}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{a.tokens.toLocaleString()}</span>
                      {a.trend === 'up' ? (
                        <TrendingUp className="h-3 w-3 text-red-400" />
                      ) : (
                        <TrendingDown className="h-3 w-3 text-emerald-400" />
                      )}
                    </div>
                  </div>
                  <Progress value={a.pct * (100 / 30)} className="h-1.5" />
                  <span className="text-[10px] text-muted-foreground">{a.pct}% of total</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Budget Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Budget Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2.5">
              {budgetAlerts.map((alert, i) => (
                <div
                  key={i}
                  className={`rounded-md px-3 py-2 ${
                    alert.level === 'warning'
                      ? 'bg-yellow-600/10 border border-yellow-600/20'
                      : 'bg-accent/30'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {alert.level === 'warning' && <AlertTriangle className="h-3 w-3 text-yellow-400" />}
                    {alert.level === 'info' && <Coins className="h-3 w-3 text-blue-400" />}
                    <span className="text-[11px]">{alert.msg}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground">{alert.time}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Per-Model Usage */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Per-Model Token Consumption</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] text-muted-foreground">
                  <th className="p-3 font-medium">Model</th>
                  <th className="p-3 font-medium">Tokens</th>
                  <th className="p-3 font-medium">API Calls</th>
                  <th className="p-3 font-medium">Avg Latency</th>
                  <th className="p-3 font-medium">Cost</th>
                  <th className="p-3 font-medium">Share</th>
                </tr>
              </thead>
              <tbody>
                {modelUsage.map((m) => (
                  <tr key={m.model} className="border-b border-border/50 hover:bg-accent/50">
                    <td className="p-3 text-xs font-medium">{m.model}</td>
                    <td className="p-3 text-xs">{m.tokens.toLocaleString()}</td>
                    <td className="p-3 text-xs">{m.calls.toLocaleString()}</td>
                    <td className="p-3 text-xs">{m.avgLatency}</td>
                    <td className="p-3 text-xs text-emerald-400">${m.cost.toFixed(4)}</td>
                    <td className="p-3 w-32">
                      <div className="flex items-center gap-2">
                        <Progress value={(m.tokens / totalUsed) * 100} className="h-1.5 flex-1" />
                        <span className="text-[10px] text-muted-foreground w-8">{((m.tokens / totalUsed) * 100).toFixed(0)}%</span>
                      </div>
                    </td>
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
