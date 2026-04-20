'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Database, Search, FileText, Shield, TrendingUp, AlertTriangle, Settings, X, Filter } from 'lucide-react'

const tracks = [
  { id: 'EVENT', label: 'Event', icon: FileText, count: 847, bgColor: 'bg-emerald-600/15', textColor: 'text-emerald-400', desc: 'Operational events & state changes' },
  { id: 'TRUST', label: 'Trust', icon: Shield, count: 234, bgColor: 'bg-blue-600/15', textColor: 'text-blue-400', desc: 'Trust score adjustments & evidence' },
  { id: 'CAP', label: 'Capability', icon: TrendingUp, count: 156, bgColor: 'bg-orange-600/15', textColor: 'text-orange-400', desc: 'Skill registrations & capability proofs' },
  { id: 'FAIL', label: 'Failure', icon: AlertTriangle, count: 43, bgColor: 'bg-red-600/15', textColor: 'text-red-400', desc: 'Error logs & failure analysis' },
  { id: 'GOV', label: 'Governance', icon: Settings, count: 512, bgColor: 'bg-purple-600/15', textColor: 'text-purple-400', desc: 'Policy decisions & audit trail' },
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
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTrack, setActiveTrack] = useState<string | null>(null)

  const hasFilters = searchQuery !== '' || activeTrack !== null

  const filteredEntries = useMemo(() => {
    return entries.filter((e) => {
      // Track filter
      if (activeTrack && e.track !== activeTrack) return false

      // Search filter — match against key, agent, value
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        const matchesKey = e.key.toLowerCase().includes(q)
        const matchesAgent = e.agent.toLowerCase().includes(q)
        const matchesValue = e.value.toLowerCase().includes(q)
        const matchesId = e.id.toLowerCase().includes(q)
        if (!matchesKey && !matchesAgent && !matchesValue && !matchesId) return false
      }

      return true
    })
  }, [searchQuery, activeTrack])

  const clearFilters = () => {
    setSearchQuery('')
    setActiveTrack(null)
  }

  const toggleTrack = (trackId: string) => {
    setActiveTrack((prev) => (prev === trackId ? null : trackId))
  }

  return (
    <div className="space-y-6 p-6">
      {/* Track Overview */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {tracks.map((t) => (
          <Card
            key={t.id}
            className={`cursor-pointer transition-colors ${
              activeTrack === t.id
                ? 'border-emerald-600/40 bg-emerald-600/5'
                : 'hover:border-emerald-600/20'
            }`}
            onClick={() => toggleTrack(t.id)}
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <div className={`flex h-8 w-8 items-center justify-center rounded-md ${t.bgColor}`}>
                  <t.icon className={`h-4 w-4 ${t.textColor}`} />
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
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Search entries by key, agent, value..."
                    className="h-9 pl-8 pr-8 text-xs rounded-lg"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {tracks.map((t) => (
                    <Badge
                      key={t.id}
                      variant="outline"
                      className={`cursor-pointer text-[10px] transition-colors ${
                        activeTrack === t.id
                          ? 'bg-emerald-600/20 text-emerald-400 border-emerald-600/40 hover:bg-emerald-600/30'
                          : 'hover:bg-accent'
                      }`}
                      onClick={() => toggleTrack(t.id)}
                    >
                      {t.label}
                    </Badge>
                  ))}
                  {hasFilters && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 gap-1 text-[10px] text-muted-foreground hover:text-foreground px-2"
                      onClick={clearFilters}
                    >
                      <Filter className="h-3 w-3" />
                      Clear
                    </Button>
                  )}
                </div>
              </div>
              {hasFilters && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {filteredEntries.length} of {entries.length} entries
                  </span>
                  {activeTrack && (
                    <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px]">
                      Track: {activeTrack}
                    </Badge>
                  )}
                  {searchQuery && (
                    <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px]">
                      Search: &quot;{searchQuery}&quot;
                    </Badge>
                  )}
                </div>
              )}
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
                    {filteredEntries.length > 0 ? (
                      filteredEntries.map((e) => (
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
                      ))
                    ) : (
                      <tr>
                        <td colSpan={7} className="p-8 text-center text-sm text-muted-foreground">
                          No entries match your filters
                        </td>
                      </tr>
                    )}
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
