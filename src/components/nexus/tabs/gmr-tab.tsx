'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Router, Activity, Clock, Zap, Wifi, WifiOff, TrendingUp } from 'lucide-react'

const models = [
  { name: 'qwen3-coder', provider: 'opencode', tier: 82, domain: 'code', health: 98, latency: 1200, free: true, active: true, calls: 347, successRate: 97.4 },
  { name: 'trinity-large-preview', provider: 'opencode', tier: 97, domain: 'reason, sec', health: 100, latency: 1350, free: true, active: true, calls: 512, successRate: 99.1 },
  { name: 'nemotron-3-super', provider: 'nvidia', tier: 60, domain: 'research, code', health: 96, latency: 890, free: true, active: true, calls: 234, successRate: 95.7 },
  { name: 'gemma-fast', provider: 'google', tier: 50, domain: 'fast', health: 100, latency: 340, free: true, active: true, calls: 1024, successRate: 99.8 },
  { name: 'minimax-m2.5', provider: 'opencode', tier: 99, domain: 'general', health: 94, latency: 1100, free: true, active: true, calls: 189, successRate: 98.2 },
  { name: 'dolphin-mistral-venice', provider: 'opencode', tier: 75, domain: 'heretic', health: 88, latency: 1450, free: true, active: false, calls: 67, successRate: 84.3 },
  { name: 'kimi-k2.5', provider: 'nvidia', tier: 85, domain: 'research', health: 92, latency: 980, free: true, active: true, calls: 156, successRate: 96.5 },
  { name: 'gpt-oss-120b', provider: 'nvidia', tier: 59, domain: 'reason', health: 100, latency: 760, free: true, active: true, calls: 298, successRate: 98.9 },
]

export function GmrTab() {
  const activeModels = models.filter(m => m.active)
  const avgHealth = Math.round(activeModels.reduce((s, m) => s + m.health, 0) / activeModels.length)
  const totalCalls = models.reduce((s, m) => s + m.calls, 0)

  return (
    <div className="space-y-6 p-6">
      {/* Stats Row */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-emerald-600/20 bg-emerald-600/5">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Models Online</p>
            <p className="text-2xl font-bold text-emerald-400">{activeModels.length}</p>
            <p className="text-[10px] text-muted-foreground">of {models.length} total</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Avg Health</p>
            <p className="text-2xl font-bold">{avgHealth}%</p>
            <p className="text-[10px] text-muted-foreground">across active models</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total API Calls</p>
            <p className="text-2xl font-bold">{totalCalls.toLocaleString()}</p>
            <p className="text-[10px] text-muted-foreground">this session</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">FREE_RESEARCH Pool</p>
            <p className="text-2xl font-bold text-emerald-400">7</p>
            <p className="text-[10px] text-muted-foreground">free-tier models active</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="models" className="space-y-4">
        <TabsList>
          <TabsTrigger value="models">Model Registry</TabsTrigger>
          <TabsTrigger value="pools">Pool Status</TabsTrigger>
          <TabsTrigger value="rotation">Rotation Log</TabsTrigger>
        </TabsList>

        {/* Model Registry */}
        <TabsContent value="models">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {models.map((m) => (
              <Card key={m.name} className={`group transition-colors ${m.active ? 'hover:border-emerald-600/20' : 'opacity-60'}`}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">{m.name}</p>
                        {m.free && (
                          <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px] px-1">FREE</Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground">{m.provider} · {m.domain}</p>
                    </div>
                    <div className="shrink-0">
                      {m.active ? (
                        <Wifi className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <WifiOff className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-[10px] text-muted-foreground">Tier</p>
                      <p className="text-sm font-bold">{m.tier}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Health</p>
                      <p className={`text-sm font-bold ${m.health >= 95 ? 'text-emerald-400' : m.health >= 85 ? 'text-yellow-400' : 'text-red-400'}`}>{m.health}%</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Latency</p>
                      <p className="text-sm font-bold">{m.latency}ms</p>
                    </div>
                  </div>

                  <div className="mt-3">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>Success Rate</span>
                      <span>{m.successRate}%</span>
                    </div>
                    <Progress value={m.successRate} className="mt-1 h-1" />
                  </div>

                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{m.calls} calls</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Pool Status */}
        <TabsContent value="pools">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              {
                name: 'PREMIUM',
                desc: 'Tier 90+ · Complex reasoning & security',
                models: ['trinity-large-preview', 'minimax-m2.5'],
                color: 'emerald',
                totalCalls: 701,
              },
              {
                name: 'MID',
                desc: 'Tier 60-89 · Code & research',
                models: ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'],
                color: 'blue',
                totalCalls: 801,
              },
              {
                name: 'FAST',
                desc: 'Tier <60 · Quick responses',
                models: ['gemma-fast', 'nemotron-3-super'],
                color: 'orange',
                totalCalls: 1258,
              },
              {
                name: 'FREE_RESEARCH',
                desc: 'StressLab + heretic control',
                models: ['dolphin-mistral-venice', 'qwen3-coder', 'trinity-large-preview'],
                color: 'purple',
                totalCalls: 67,
              },
            ].map((pool) => (
              <Card key={pool.name}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">{pool.name} Pool</CardTitle>
                    <Badge variant="outline" className="text-[10px]">{pool.models.length} models</Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground">{pool.desc}</p>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <div className="space-y-1.5">
                    {pool.models.map((m) => (
                      <div key={m} className="flex items-center gap-2 text-xs">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        <span>{m}</span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-3 text-[11px] text-muted-foreground">{pool.totalCalls} calls this session</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Rotation Log */}
        <TabsContent value="rotation">
          <Card>
            <CardContent className="p-4">
              <div className="max-h-96 space-y-2 overflow-y-auto">
                {[
                  { time: '14:23:01', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Domain: reason', tokens: 0 },
                  { time: '14:22:45', from: 'gemma-fast', to: 'qwen3-coder', reason: 'Domain: code', tokens: 0 },
                  { time: '14:22:12', from: '-', to: 'gemma-fast', reason: 'New request: fast', tokens: 340 },
                  { time: '14:21:58', from: 'trinity-large-preview', to: 'nemotron-3-super', reason: 'Domain: research', tokens: 1280 },
                  { time: '14:21:30', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Escalation: sec domain', tokens: 890 },
                  { time: '14:20:55', from: 'gemma-fast', to: 'kimi-k2.5', reason: 'Health fallback: gemma 88%', tokens: 450 },
                ].map((r, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-md bg-accent/30 px-3 py-2 text-xs">
                    <span className="font-mono text-[10px] text-muted-foreground shrink-0">{r.time}</span>
                    <span className="text-muted-foreground">{r.from}</span>
                    <span className="text-emerald-400">→</span>
                    <span className="font-medium">{r.to}</span>
                    <span className="ml-auto text-muted-foreground shrink-0">{r.reason}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
