'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Database,
  Search,
  FileText,
  Shield,
  TrendingUp,
  AlertTriangle,
  Settings,
  X,
  Filter,
  Activity,
  Clock,
  Copy,
  CheckCircle2,
  Link2,
  ShieldCheck,
} from 'lucide-react'
import { toast } from 'sonner'

const tracks = [
  { id: 'EVENT', label: 'Event', icon: FileText, count: 847, bgColor: 'bg-emerald-600/15', textColor: 'text-emerald-400', desc: 'Operational events & state changes', gradient: 'from-emerald-600/10 via-emerald-600/3 to-transparent', borderColor: 'border-emerald-600/20', glowColor: 'hover:shadow-emerald-600/10', badgeBg: 'bg-emerald-600/15 text-emerald-400', borderLeftColor: 'border-l-emerald-500', headerGradient: 'from-emerald-600/20 to-emerald-600/5' },
  { id: 'TRUST', label: 'Trust', icon: Shield, count: 234, bgColor: 'bg-blue-600/15', textColor: 'text-blue-400', desc: 'Trust score adjustments & evidence', gradient: 'from-blue-600/10 via-blue-600/3 to-transparent', borderColor: 'border-blue-600/20', glowColor: 'hover:shadow-blue-600/10', badgeBg: 'bg-blue-600/15 text-blue-400', borderLeftColor: 'border-l-blue-500', headerGradient: 'from-blue-600/20 to-blue-600/5' },
  { id: 'CAP', label: 'Capability', icon: TrendingUp, count: 156, bgColor: 'bg-orange-600/15', textColor: 'text-orange-400', desc: 'Skill registrations & capability proofs', gradient: 'from-orange-600/10 via-orange-600/3 to-transparent', borderColor: 'border-orange-600/20', glowColor: 'hover:shadow-orange-600/10', badgeBg: 'bg-orange-600/15 text-orange-400', borderLeftColor: 'border-l-orange-500', headerGradient: 'from-orange-600/20 to-orange-600/5' },
  { id: 'FAIL', label: 'Failure', icon: AlertTriangle, count: 43, bgColor: 'bg-red-600/15', textColor: 'text-red-400', desc: 'Error logs & failure analysis', gradient: 'from-red-600/10 via-red-600/3 to-transparent', borderColor: 'border-red-600/20', glowColor: 'hover:shadow-red-600/10', badgeBg: 'bg-red-600/15 text-red-400', borderLeftColor: 'border-l-red-500', headerGradient: 'from-red-600/20 to-red-600/5' },
  { id: 'GOV', label: 'Governance', icon: Settings, count: 512, bgColor: 'bg-purple-600/15', textColor: 'text-purple-400', desc: 'Policy decisions & audit trail', gradient: 'from-purple-600/10 via-purple-600/3 to-transparent', borderColor: 'border-purple-600/20', glowColor: 'hover:shadow-purple-600/10', badgeBg: 'bg-purple-600/15 text-purple-400', borderLeftColor: 'border-l-purple-500', headerGradient: 'from-purple-600/20 to-purple-600/5' },
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

const chainBlocks = [
  { hash: '0xa3f7...8b2c', prev: '0x9e12...4d1a', type: 'GOV', summary: 'Governor DENY worker-2 delete_all', ts: '14:21:58' },
  { hash: '0x7c91...2e4f', prev: '0xa3f7...8b2c', type: 'TRUST', summary: 'Trust update worker-3: 0.78→0.82', ts: '14:23:01' },
  { hash: '0xb4d3...9a1e', prev: '0x7c91...2e4f', type: 'EVENT', summary: 'Task T-0847 completed PASS', ts: '14:22:45' },
  { hash: '0xe8f2...3c5a', prev: '0xb4d3...9a1e', type: 'FAIL', summary: 'API timeout opencode/trinity', ts: '14:21:30' },
  { hash: '0x1a6c...7d8b', prev: '0xe8f2...3c5a', type: 'CAP', summary: 'Skill registered: stresslab_runner', ts: '14:20:55' },
]

function getTrackConfig(trackId: string) {
  return tracks.find((t) => t.id === trackId) ?? tracks[0]
}

function formatJsonValue(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}

export function VaultTab() {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTrack, setActiveTrack] = useState<string | null>(null)
  const [selectedEntry, setSelectedEntry] = useState<(typeof entries)[0] | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  const hasFilters = searchQuery !== '' || activeTrack !== null

  const filteredEntries = useMemo(() => {
    return entries.filter((e) => {
      if (activeTrack && e.track !== activeTrack) return false
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

  const openEntryDetail = (entry: (typeof entries)[0]) => {
    setSelectedEntry(entry)
    setDialogOpen(true)
  }

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(
      () => toast.success(`${label} copied to clipboard`),
      () => toast.error('Failed to copy to clipboard')
    )
  }

  return (
    <div className="space-y-6 p-6 grid-pattern animate-fade-in">
      {/* Vault Integrity Status Banner */}
      <div className="relative overflow-hidden rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-blue-600/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-blue-600 shadow-lg shadow-emerald-600/10">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold">Vault Integrity</h2>
              <p className="text-xs text-muted-foreground">All 5 tracks operational · 1,792 entries · Last verified: 2 min ago</p>
            </div>
          </div>
          <Badge className="border-0 text-[10px] gap-1 bg-emerald-600/15 text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Operational
          </Badge>
        </div>
      </div>

      {/* Gradient Stat Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-emerald-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Entries</p>
                <p className="mt-1 text-3xl font-bold text-emerald-400 tabular-nums animate-count-up">1,792</p>
                <p className="text-[10px] text-muted-foreground">across 5 tracks</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Database className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-blue-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-blue-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Active Tracks</p>
                <p className="mt-1 text-3xl font-bold text-blue-400 tabular-nums animate-count-up">5</p>
                <p className="text-[10px] text-muted-foreground">all tracks operational</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Activity className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-purple-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 via-purple-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Latest Entry</p>
                <p className="mt-1 text-3xl font-bold text-purple-400 tabular-nums">V-2047</p>
                <p className="text-[10px] text-muted-foreground">trust_score.update</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-600/15 shadow-lg shadow-purple-600/10">
                <Clock className="h-5 w-5 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-orange-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 via-orange-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Avg Score</p>
                <p className="mt-1 text-3xl font-bold text-orange-400 tabular-nums animate-count-up">0.73</p>
                <p className="text-[10px] text-muted-foreground">across all entries</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                <TrendingUp className="h-5 w-5 text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Track Overview with Gradient Cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {tracks.map((t) => (
          <Card
            key={t.id}
            className={`cursor-pointer transition-all duration-200 hover-lift ${
              activeTrack === t.id
                ? `${t.borderColor} shadow-md ${t.glowColor}`
                : 'hover:border-emerald-600/20'
            }`}
            onClick={() => toggleTrack(t.id)}
          >
            <div className={`absolute inset-0 bg-gradient-to-br ${t.gradient} rounded-lg`} />
            <CardContent className="relative p-4">
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
              {activeTrack === t.id && (
                <div className="mt-2 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[9px] text-emerald-400 font-medium">Filtered</span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="browser" className="space-y-4">
        <TabsList>
          <TabsTrigger value="browser">Entry Browser</TabsTrigger>
          <TabsTrigger value="evidence">VAP Proof Chain</TabsTrigger>
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
                      filteredEntries.map((e) => {
                        const tc = getTrackConfig(e.track)
                        return (
                          <tr
                            key={e.id}
                            className="border-b border-border/50 hover:bg-accent/50 cursor-pointer transition-colors"
                            onClick={() => openEntryDetail(e)}
                          >
                            <td className="p-3 font-mono text-xs">{e.id}</td>
                            <td className="p-3">
                              <Badge variant="outline" className={`text-[9px] ${tc.badgeBg} border-0`}>{e.track}</Badge>
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
                        )
                      })
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

        {/* VAP Proof Chain */}
        <TabsContent value="evidence">
          <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
            <CardHeader className="relative">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Database className="h-4 w-4 text-emerald-400" /> VAP Proof Chain (Immutable Audit Trail)
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1.5 text-xs"
                  onClick={() => {
                    toast.success('Chain integrity verified', {
                      description: 'All 5 blocks verified — no tampering detected. Hash chain is consistent.',
                    })
                  }}
                >
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  Verify Chain Integrity
                </Button>
              </div>
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              <div className="max-h-[500px] space-y-0 overflow-y-auto custom-scrollbar">
                {chainBlocks.map((block, i) => {
                  const tc = getTrackConfig(block.type)
                  return (
                    <div key={i} className="relative flex items-start gap-3">
                      {/* Timeline connector */}
                      <div className="flex flex-col items-center">
                        <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${tc.bgColor} text-[10px] font-bold ${tc.textColor} border ${tc.borderColor}`}>
                          {i + 1}
                        </div>
                        {i < chainBlocks.length - 1 && (
                          <div className="w-px flex-1 min-h-[32px] bg-gradient-to-b from-border to-transparent" />
                        )}
                      </div>
                      {/* Block content */}
                      <div className={`flex-1 min-w-0 mb-4 rounded-md border-l-4 ${tc.borderLeftColor} bg-accent/30 px-3 py-2.5`}>
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className={`text-[9px] ${tc.badgeBg} border-0`}>{block.type}</Badge>
                            <span className="text-xs">{block.summary}</span>
                          </div>
                          <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{block.ts}</span>
                        </div>
                        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                          <span className="flex items-center gap-1">
                            hash: {block.hash}
                            <button
                              className="inline-flex h-4 w-4 items-center justify-center rounded hover:bg-accent transition-colors"
                              onClick={() => copyToClipboard(block.hash, 'Hash')}
                              title="Copy hash"
                            >
                              <Copy className="h-2.5 w-2.5" />
                            </button>
                          </span>
                          <span>prev: {block.prev}</span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Vault Entry Detail Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          {selectedEntry && (() => {
            const tc = getTrackConfig(selectedEntry.track)
            return (
              <>
                <DialogHeader>
                  <div className={`-mx-6 -mt-6 mb-4 rounded-t-lg bg-gradient-to-r ${tc.headerGradient} px-6 py-4`}>
                    <DialogTitle className="flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Entry {selectedEntry.id}
                    </DialogTitle>
                    <DialogDescription className="mt-1">
                      Full vault entry details and metadata
                    </DialogDescription>
                  </div>
                </DialogHeader>

                <div className="space-y-4">
                  {/* ID + Track */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Entry ID</p>
                      <p className="mt-0.5 text-sm font-mono font-medium">{selectedEntry.id}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Track</p>
                      <div className="mt-0.5">
                        <Badge className={`${tc.badgeBg} border-0 text-[10px] gap-1`}>
                          <tc.icon className="h-3 w-3" />
                          {selectedEntry.track}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  {/* Agent + Key */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Agent</p>
                      <p className="mt-0.5 text-sm">{selectedEntry.agent}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Key</p>
                      <p className="mt-0.5 text-sm font-mono">{selectedEntry.key}</p>
                    </div>
                  </div>

                  {/* Value (formatted JSON) */}
                  <div>
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Value</p>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 gap-1 text-[10px] px-2"
                        onClick={() => copyToClipboard(selectedEntry.value, 'Value')}
                      >
                        <Copy className="h-3 w-3" />
                        Copy Value
                      </Button>
                    </div>
                    <div className="mt-1 rounded-lg bg-muted/50 border border-border/50 p-3 max-h-40 overflow-y-auto custom-scrollbar">
                      <pre className="text-xs font-mono text-foreground whitespace-pre-wrap break-all">
                        {formatJsonValue(selectedEntry.value)}
                      </pre>
                    </div>
                  </div>

                  {/* Score + Timestamp */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Score</p>
                      <div className="mt-1 flex items-center gap-2">
                        <Progress
                          value={selectedEntry.score * 100}
                          className={`h-2 flex-1 ${
                            selectedEntry.score >= 0.7 ? 'bg-emerald-900/20' : selectedEntry.score >= 0.4 ? 'bg-yellow-900/20' : 'bg-red-900/20'
                          }`}
                        />
                        <span className={`text-sm font-bold tabular-nums ${
                          selectedEntry.score >= 0.7 ? 'text-emerald-400' : selectedEntry.score >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                        }`}>
                          {selectedEntry.score.toFixed(2)}
                        </span>
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Timestamp</p>
                      <p className="mt-0.5 text-sm font-mono tabular-nums">{selectedEntry.time}</p>
                    </div>
                  </div>
                </div>

                <DialogFooter className="gap-2 sm:gap-0 mt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => {
                      toast.info('Viewing entry in VAP Chain', {
                        description: `Navigating to proof chain block for ${selectedEntry.id}`,
                      })
                    }}
                  >
                    <Link2 className="h-3.5 w-3.5" />
                    View in VAP Chain
                  </Button>
                  <Button
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                    onClick={() => copyToClipboard(selectedEntry.value, 'Entry value')}
                  >
                    <Copy className="h-3.5 w-3.5" />
                    Copy to Clipboard
                  </Button>
                </DialogFooter>
              </>
            )
          })()}
        </DialogContent>
      </Dialog>
    </div>
  )
}
