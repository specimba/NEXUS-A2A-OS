'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Database, Search, FileText, Shield, TrendingUp, AlertTriangle, Settings } from 'lucide-react'

const tracks = [
  { id: 'EVENT', label: 'Event', icon: FileText, count: 847, color: 'emerald', desc: 'Operational events & state changes' },
  { id: 'TRUST', label: 'Trust', icon: Shield, count: 234, color: 'blue', desc: 'Trust score adjustments & evidence' },
  { id: 'CAP', label: 'Capability', icon: TrendingUp, count: 156, color: 'orange', desc: 'Skill registrations & capability proofs' },
  { id: 'FAIL', label: 'Failure', icon: AlertTriangle, count: 43, color: 'red', desc: 'Error logs & failure analysis' },
  { id: 'GOV', label: 'Governance', icon: Settings, count: 512, color: 'purple', desc: 'Policy decisions & audit trail' },
]

const entries = [
  { id: 'V-2047', track: 'TRUST', agent: 'worker-3', key: 'trust_score.update', value: '{"from": 0.78, "to": 0.82, "reason": "successful_stress_test"}', score: 0.82, time: '14:23:01' },
  { id: 'V-2046', track: 'EVENT', agent: 'coordinator', key: 'task.completed', value: '{"task": "T-0847", "result": "PASS"}', score: 0.95, time: '14:22:45' },
  { id: 'V-2045', track: 'GOV', agent: 'governor', key: 'decision.deny', value: '{"action": "delete_all", "agent": "worker-2", "scope": "SYSTEM"}', score: 0.0, time: '14:21:58' },
  { id: 'V-2044', track: 'FAIL', agent: 'worker-1', key: 'api.timeout', value: '{"provider": "opencode", "model": "trinity", "timeout_ms": 30000}', score: 0.3, time: '14:21:30' },
  { id: 'V-2043', track: 'CAP', agent: 'worker-3', key: 'skill.registered', value: '{"skill": "stresslab_runner", "domain": "cyber"}', score: 0.88, time: '14:20:55' },
  { id: 'V-2042', track: 'EVENT', agent: 'coordinator', key: 'agent.spawned', value: '{"agent": "research-agent", "type": "specialist"}', score: 0.7, time: '14:20:12' },
  { id: 'V-2041', track: 'TRUST', agent: 'worker-2', key: 'trust_score.decline', value: '{"from": 0.52, "to": 0.45, "reason": "denied_action_pattern"}', score: 0.45, time: '14:19:58' },
  { id: 'V-2040', track: 'GOV', agent: 'governor', key: 'constitution.check', value: '{"max_agents": 5, "current": 3, "within_limits": true}', score: 1.0, time: '14:19:30' },
]

export function VaultTab() {
  return (
    <div className="space-y-6 p-6">
      {/* Track Overview */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {tracks.map((t) => (
          <Card key={t.id} className="hover:border-emerald-600/20 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <div className={`flex h-8 w-8 items-center justify-center rounded-md bg-${t.color}-600/15`}>
                  <t.icon className={`h-4 w-4 text-${t.color}-400`} />
                </div>
                <div>
                  <p className="text-sm font-medium">{t.label}</p>
                  <p className="text-[10px] text-muted-foreground">{t.count} entries</p>
                </div>
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground">{t.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="browser" className="space-y-4">
        <TabsList>
          <TabsTrigger value="browser">Entry Browser</TabsTrigger>
          <TabsTrigger value="evidence">Evidence Chain</TabsTrigger>
        </TabsList>

        {/* Entry Browser */}
        <TabsContent value="browser">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input placeholder="Search vault entries..." className="h-9 pl-8 text-xs" />
                </div>
                <div className="flex gap-1">
                  {tracks.map((t) => (
                    <Badge key={t.id} variant="outline" className="cursor-pointer text-[10px] hover:bg-accent">
                      {t.label}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-[11px] text-muted-foreground">
                      <th className="p-3 font-medium">ID</th>
                      <th className="p-3 font-medium">Track</th>
                      <th className="p-3 font-medium">Agent</th>
                      <th className="p-3 font-medium">Key</th>
                      <th className="p-3 font-medium">Value</th>
                      <th className="p-3 font-medium">Score</th>
                      <th className="p-3 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((e) => (
                      <tr key={e.id} className="border-b border-border/50 hover:bg-accent/50">
                        <td className="p-3 font-mono text-xs">{e.id}</td>
                        <td className="p-3">
                          <Badge variant="outline" className="text-[9px]">{e.track}</Badge>
                        </td>
                        <td className="p-3 text-xs">{e.agent}</td>
                        <td className="p-3 text-xs font-mono max-w-[150px] truncate">{e.key}</td>
                        <td className="p-3 text-[11px] text-muted-foreground max-w-[250px] truncate font-mono">{e.value}</td>
                        <td className="p-3">
                          <span className={`text-xs font-medium ${e.score >= 0.7 ? 'text-emerald-400' : e.score >= 0.4 ? 'text-yellow-400' : 'text-red-400'}`}>
                            {e.score.toFixed(2)}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-[11px]">{e.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Evidence Chain */}
        <TabsContent value="evidence">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Database className="h-4 w-4" /> VAP Proof Chain (Immutable Audit Trail)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="max-h-96 space-y-2 overflow-y-auto">
                {[
                  { hash: '0xa3f7...8b2c', prev: '0x9e12...4d1a', type: 'GOV', summary: 'Governor DENY worker-2 delete_all', ts: '14:21:58' },
                  { hash: '0x7c91...2e4f', prev: '0xa3f7...8b2c', type: 'TRUST', summary: 'Trust update worker-3: 0.78→0.82', ts: '14:23:01' },
                  { hash: '0xb4d3...9a1e', prev: '0x7c91...2e4f', type: 'EVENT', summary: 'Task T-0847 completed PASS', ts: '14:22:45' },
                  { hash: '0xe8f2...3c5a', prev: '0xb4d3...9a1e', type: 'FAIL', summary: 'API timeout opencode/trinity', ts: '14:21:30' },
                  { hash: '0x1a6c...7d8b', prev: '0xe8f2...3c5a', type: 'CAP', summary: 'Skill registered: stresslab_runner', ts: '14:20:55' },
                ].map((block, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-md bg-accent/30 px-3 py-2">
                    <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-600/15 text-[10px] font-bold text-emerald-400">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[9px]">{block.type}</Badge>
                        <span className="text-xs">{block.summary}</span>
                      </div>
                      <div className="mt-1 flex gap-3 text-[10px] text-muted-foreground font-mono">
                        <span>hash: {block.hash}</span>
                        <span>prev: {block.prev}</span>
                      </div>
                    </div>
                    <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{block.ts}</span>
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
