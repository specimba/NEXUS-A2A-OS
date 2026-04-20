'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'
import { Coins, TrendingDown, TrendingUp, AlertTriangle, PieChart, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

const hourlyUsage = [
  { hour: '08:00', tokens: 1200 },
  { hour: '09:00', tokens: 3400 },
  { hour: '10:00', tokens: 5600 },
  { hour: '11:00', tokens: 4800 },
  { hour: '12:00', tokens: 2100 },
  { hour: '13:00', tokens: 3800 },
  { hour: '14:00', tokens: 6200 },
  { hour: '15:00', tokens: 4500 },
  { hour: '16:00', tokens: 5100 },
  { hour: '17:00', tokens: 3200 },
]

const agentUsage = [
  { name: 'worker-3', tokens: 18600, pct: 25.3, trend: 'up' as const, model: 'qwen3-coder', color: COLORS.emerald },
  { name: 'worker-1', tokens: 12400, pct: 16.9, trend: 'up' as const, model: 'trinity-large', color: COLORS.blue },
  { name: 'coordinator', tokens: 8200, pct: 11.2, trend: 'down' as const, model: 'gemma-fast', color: COLORS.purple },
  { name: 'worker-2', tokens: 8200, pct: 11.2, trend: 'up' as const, model: 'nemotron-3', color: COLORS.orange },
  { name: 'research-agent', tokens: 5100, pct: 6.9, trend: 'down' as const, model: 'kimi-k2.5', color: COLORS.pink },
]

const modelUsage = [
  { model: 'gemma-fast', tokens: 22400, calls: 1024, avgLatency: 340, cost: 0 },
  { model: 'trinity-large', tokens: 18200, calls: 512, avgLatency: 1350, cost: 0 },
  { model: 'qwen3-coder', tokens: 15800, calls: 347, avgLatency: 1200, cost: 0 },
  { model: 'nemotron-3', tokens: 8900, calls: 234, avgLatency: 890, cost: 0 },
  { model: 'kimi-k2.5', tokens: 5400, calls: 156, avgLatency: 980, cost: 0 },
  { model: 'gpt-oss-120b', tokens: 3200, calls: 298, avgLatency: 760, cost: 0 },
]

const budgetAlerts = [
  { level: 'warning' as const, msg: 'worker-2 approaching rate limit (85% of hourly budget)', time: '5m ago' },
  { level: 'info' as const, msg: 'Session budget 73.4% consumed — 26,550 remaining', time: '1m ago' },
  { level: 'info' as const, msg: 'FREE_RESEARCH pool: all models within limits', time: '3m ago' },
]

export function TokensTab() {
  const totalUsed = 73500
  const totalBudget = 100000
  const remaining = totalBudget - totalUsed
  const pct = (totalUsed / totalBudget) * 100
  const burnRate = 142 // tokens/min simulated

  return (
    <div className="space-y-6 p-6">
      {/* Main Budget Card with Chart */}
      <Card className="relative overflow-hidden border-emerald-600/20">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
        <CardContent className="relative p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Session Token Budget</h2>
              <p className="text-sm text-muted-foreground">Current active session monitoring</p>
            </div>
            <Coins className="h-8 w-8 text-emerald-400" />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-bold tabular-nums">{totalUsed.toLocaleString()}</span>
            <span className="text-lg text-muted-foreground mb-1">/ {totalBudget.toLocaleString()}</span>
          </div>
          {/* Burn rate indicator */}
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] gap-1">
              <TrendingUp className="h-3 w-3 text-red-400" />
              {burnRate.toLocaleString()} tok/min
            </Badge>
            <span className="text-[10px] text-muted-foreground">
              ~{Math.round(remaining / burnRate)} min remaining at current rate
            </span>
          </div>
          <Progress value={pct} className="mt-3 h-3" />
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            <span>{pct.toFixed(1)}% used</span>
            <span className="text-emerald-400 font-medium">{remaining.toLocaleString()} remaining</span>
          </div>
          {/* Hourly usage chart */}
          <div className="mt-6">
            <p className="text-xs text-muted-foreground mb-2">Hourly Token Consumption</p>
            <ResponsiveContainer width="100%" height={120}>
              <AreaChart data={hourlyUsage} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hour" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} width={40} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '11px',
                  }}
                />
                <defs>
                  <linearGradient id="hourlyGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.emerald} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS.emerald} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="tokens" stroke={COLORS.emerald} fill="url(#hourlyGrad)" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
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
                <div key={a.name} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: a.color }} />
                      <span className="text-sm font-medium">{a.name}</span>
                      <Badge variant="outline" className="text-[9px]">{a.model}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold tabular-nums">{a.tokens.toLocaleString()}</span>
                      {a.trend === 'up' ? (
                        <TrendingUp className="h-3 w-3 text-red-400" />
                      ) : (
                        <TrendingDown className="h-3 w-3 text-emerald-400" />
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Progress value={a.pct * 3.3} className="h-2 flex-1" />
                    <span className="text-[10px] text-muted-foreground w-8 tabular-nums">{a.pct}%</span>
                  </div>
                </div>
              ))}
            </div>
            {/* Agent usage bar chart */}
            <div className="mt-6">
              <NexusBarChart
                data={agentUsage.map(a => ({ name: a.name.split('-')[0], value: a.tokens }))}
                height={100}
              />
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
                  className={`rounded-lg px-3 py-2.5 ${
                    alert.level === 'warning'
                      ? 'bg-yellow-600/10 border border-yellow-600/15'
                      : 'bg-accent/30 border border-border/50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {alert.level === 'warning' && <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-yellow-400" />}
                    {alert.level === 'info' && <Activity className="h-3.5 w-3.5 shrink-0 text-blue-400" />}
                    <span className="text-[11px] leading-snug">{alert.msg}</span>
                  </div>
                  <p className="mt-1.5 text-[10px] text-muted-foreground">{alert.time}</p>
                </div>
              ))}
            </div>

            {/* Constitution Limits */}
            <div className="mt-4 rounded-lg border border-border/50 p-3">
              <p className="text-[11px] font-medium mb-2">Constitution Limits</p>
              <div className="space-y-2">
                {[
                  { label: 'API Calls', used: 12, max: 20 },
                  { label: 'File Writes', used: 8, max: 30 },
                  { label: 'Concurrent', used: 2, max: 2 },
                ].map((l) => (
                  <div key={l.label}>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>{l.label}</span>
                      <span className={l.used >= l.max ? 'text-red-400 font-medium' : ''}>{l.used} / {l.max}</span>
                    </div>
                    <Progress value={(l.used / l.max) * 100} className={`mt-0.5 h-1.5 ${l.used >= l.max ? '[&>div]:bg-red-400' : ''}`} />
                  </div>
                ))}
              </div>
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
                  <tr key={m.model} className="border-b border-border/50 hover:bg-accent/30 transition-colors">
                    <td className="p-3 text-xs font-medium">{m.model}</td>
                    <td className="p-3 text-xs tabular-nums">{m.tokens.toLocaleString()}</td>
                    <td className="p-3 text-xs tabular-nums">{m.calls.toLocaleString()}</td>
                    <td className="p-3 text-xs">{m.avgLatency}ms</td>
                    <td className="p-3 text-xs text-emerald-400">${m.cost.toFixed(4)}</td>
                    <td className="p-3 w-36">
                      <div className="flex items-center gap-2">
                        <Progress value={(m.tokens / totalUsed) * 100} className="h-1.5 flex-1" />
                        <span className="text-[10px] text-muted-foreground w-8 tabular-nums">{((m.tokens / totalUsed) * 100).toFixed(0)}%</span>
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
