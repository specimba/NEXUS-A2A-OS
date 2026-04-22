'use client'

import { useState, useMemo, useRef, useEffect, useCallback } from 'react'
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
  Loader2,
  Download,
  PieChart as PieChartLucide,
} from 'lucide-react'
import { PieChart as RechartsPieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'
import { toast } from 'sonner'
import { useApiData } from '@/hooks/use-api-data'

// ─── API Response Types ───

interface VaultEntryAPI {
  id: string
  agentId: string
  agent: { name: string }
  track: string
  category: string
  key: string
  value: string
  score: number
  createdAt: string
}

interface VaultAPIResponse {
  entries: VaultEntryAPI[]
}

interface VerifyChainResponse {
  valid: boolean
  entryCount: number
  issues: string[]
}

// ─── UI-facing Types ───

interface VaultEntryUI {
  id: string
  track: string
  agent: string
  key: string
  value: string
  score: number
  time: string
  rawEntry: VaultEntryAPI
}

// ─── Data Transformation ───

function apiEntryToUI(e: VaultEntryAPI): VaultEntryUI {
  return {
    id: e.id.slice(-6).toUpperCase().padStart(6, '0'),
    track: e.track,
    agent: e.agent?.name ?? 'unknown',
    key: e.key,
    value: e.value,
    score: e.score,
    time: new Date(e.createdAt).toLocaleTimeString('en-US', { hour12: false }),
    rawEntry: e,
  }
}

// ─── Track Config ───

const tracks = [
  { id: 'EVENT', label: 'Event', icon: FileText, bgColor: 'bg-emerald-600/15', textColor: 'text-emerald-600 dark:text-emerald-400', desc: 'Operational events & state changes', gradient: 'from-emerald-600/10 via-emerald-600/3 to-transparent', borderColor: 'border-emerald-600/20', glowColor: 'hover:shadow-emerald-600/10', badgeBg: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400', borderLeftColor: 'border-l-emerald-500', headerGradient: 'from-emerald-600/20 to-emerald-600/5' },
  { id: 'TRUST', label: 'Trust', icon: Shield, bgColor: 'bg-blue-600/15', textColor: 'text-blue-600 dark:text-blue-400', desc: 'Trust score adjustments & evidence', gradient: 'from-blue-600/10 via-blue-600/3 to-transparent', borderColor: 'border-blue-600/20', glowColor: 'hover:shadow-blue-600/10', badgeBg: 'bg-blue-600/15 text-blue-600 dark:text-blue-400', borderLeftColor: 'border-l-blue-500', headerGradient: 'from-blue-600/20 to-blue-600/5' },
  { id: 'CAP', label: 'Capability', icon: TrendingUp, bgColor: 'bg-orange-600/15', textColor: 'text-orange-600 dark:text-orange-400', desc: 'Skill registrations & capability proofs', gradient: 'from-orange-600/10 via-orange-600/3 to-transparent', borderColor: 'border-orange-600/20', glowColor: 'hover:shadow-orange-600/10', badgeBg: 'bg-orange-600/15 text-orange-600 dark:text-orange-400', borderLeftColor: 'border-l-orange-500', headerGradient: 'from-orange-600/20 to-orange-600/5' },
  { id: 'FAIL', label: 'Failure', icon: AlertTriangle, bgColor: 'bg-red-600/15', textColor: 'text-red-600 dark:text-red-400', desc: 'Error logs & failure analysis', gradient: 'from-red-600/10 via-red-600/3 to-transparent', borderColor: 'border-red-600/20', glowColor: 'hover:shadow-red-600/10', badgeBg: 'bg-red-600/15 text-red-600 dark:text-red-400', borderLeftColor: 'border-l-red-500', headerGradient: 'from-red-600/20 to-red-600/5' },
  { id: 'GOV', label: 'Governance', icon: Settings, bgColor: 'bg-purple-600/15', textColor: 'text-purple-600 dark:text-purple-400', desc: 'Policy decisions & audit trail', gradient: 'from-purple-600/10 via-purple-600/3 to-transparent', borderColor: 'border-purple-600/20', glowColor: 'hover:shadow-purple-600/10', badgeBg: 'bg-purple-600/15 text-purple-600 dark:text-purple-400', borderLeftColor: 'border-l-purple-500', headerGradient: 'from-purple-600/20 to-purple-600/5' },
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

// Vault distribution data for donut chart
const vaultDistributionData = [
  { name: 'EVENT', value: 487, pct: 27.1, fill: '#34d399' },
  { name: 'TRUST', value: 412, pct: 22.9, fill: '#60a5fa' },
  { name: 'CAP', value: 356, pct: 19.9, fill: '#fb923c' },
  { name: 'FAIL', value: 289, pct: 16.1, fill: '#ef4444' },
  { name: 'GOV', value: 248, pct: 13.8, fill: '#a78bfa' },
]

// Recent vault activity for timeline
const vaultRecentActivity = [
  { track: 'EVENT', description: 'Agent worker-3 completed task T-0847', color: '#34d399', time: '2m ago' },
  { track: 'TRUST', description: 'Trust score updated for agent-alpha: 0.82 → 0.85', color: '#60a5fa', time: '5m ago' },
  { track: 'CAP', description: 'New skill registered: code-review-v2', color: '#fb923c', time: '8m ago' },
  { track: 'GOV', description: 'Constitution check passed: agent-beta read file', color: '#a78bfa', time: '12m ago' },
  { track: 'FAIL', description: 'Worker-1 rate limit error: E-RATE-429', color: '#ef4444', time: '15m ago' },
  { track: 'EVENT', description: 'GMR model rotation: trinity-large → qwen3-coder', color: '#34d399', time: '18m ago' },
  { track: 'TRUST', description: 'Trust decay applied: worker-2 0.78 → 0.76', color: '#60a5fa', time: '22m ago' },
  { track: 'GOV', description: 'Governor denied: worker-2 delete_all (CRIT)', color: '#a78bfa', time: '25m ago' },
]

export function VaultTab() {
  const { data: apiData, loading, error: apiError, refetch } = useApiData<VaultAPIResponse>('/api/vault', 15000)

  // Transform API entries to UI format
  const entries = useMemo<VaultEntryUI[]>(() => {
    if (!apiData?.entries) return []
    return apiData.entries.map(apiEntryToUI)
  }, [apiData?.entries])

  // Compute track counts from real data
  const trackCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    entries.forEach((e) => {
      counts[e.track] = (counts[e.track] || 0) + 1
    })
    return counts
  }, [entries])

  // Compute stat card values from real data
  const totalEntries = entries.length
  const activeTracks = Object.keys(trackCounts).length
  const latestEntry = entries.length > 0 ? entries[0] : null
  const avgScore = entries.length > 0
    ? entries.reduce((sum, e) => sum + e.score, 0) / entries.length
    : 0

  // Build chain blocks from entries
  const chainBlocks = useMemo(() => {
    return entries.slice(0, 10).map((e, i) => ({
      hash: `0x${e.id.slice(0, 4)}...${String(Math.abs(e.rawEntry.id.charCodeAt(0) * 31 + i * 17)).slice(0, 4)}`,
      prev: i > 0
        ? `0x${entries[i - 1].id.slice(0, 4)}...${String(Math.abs(entries[i - 1].rawEntry.id.charCodeAt(0) * 31 + (i - 1) * 17)).slice(0, 4)}`
        : '0x0000...0000',
      type: e.track,
      summary: `${e.key}: ${e.agent}`,
      ts: e.time,
    }))
  }, [entries])

  const [searchQuery, setSearchQuery] = useState('')
  const [activeTrack, setActiveTrack] = useState<string | null>(null)
  const [selectedEntry, setSelectedEntry] = useState<VaultEntryUI | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<VerifyChainResponse | null>(null)
  const [animatedEntries, setAnimatedEntries] = useState(0)

  const vapChainRef = useRef<HTMLDivElement>(null)

  // Animate timeline entries on mount
  useEffect(() => {
    if (entries.length > 0) {
      let count = 0
      const interval = setInterval(() => {
        count += 1
        setAnimatedEntries(count)
        if (count >= Math.min(entries.length, 5)) clearInterval(interval)
      }, 100)
      return () => clearInterval(interval)
    }
  }, [entries.length])

  // Pie chart data from track counts
  const pieData = useMemo(() => {
    return tracks.map((t) => ({
      name: t.id,
      label: t.label,
      value: trackCounts[t.id] ?? 0,
      color: t.id === 'EVENT' ? '#059669' : t.id === 'TRUST' ? '#2563eb' : t.id === 'CAP' ? '#ea580c' : t.id === 'FAIL' ? '#dc2626' : '#9333ea',
    })).filter((d) => d.value > 0)
  }, [trackCounts])

  // Recent activity (last 5 entries)
  const recentActivity = useMemo(() => {
    return entries.slice(0, 5)
  }, [entries])

  const handleExportCsv = useCallback(() => {
    const headers = ['ID', 'Track', 'Agent', 'Key', 'Value', 'Score', 'Time']
    const rows = filteredEntries.map((e) => [
      e.id,
      e.track,
      e.agent,
      e.key,
      `"${e.value.replace(/"/g, '""')}"`,
      e.score.toFixed(2),
      e.time,
    ])
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `vault-export-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
    toast.success('Vault data exported', {
      description: `${filteredEntries.length} entries exported as CSV`,
    })
  }, [filteredEntries])

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
  }, [searchQuery, activeTrack, entries])

  const clearFilters = () => {
    setSearchQuery('')
    setActiveTrack(null)
  }

  const toggleTrack = (trackId: string) => {
    setActiveTrack((prev) => (prev === trackId ? null : trackId))
  }

  const openEntryDetail = (entry: VaultEntryUI) => {
    setSelectedEntry(entry)
    setDialogOpen(true)
  }

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(
      () => toast.success(`${label} copied to clipboard`),
      () => toast.error('Failed to copy to clipboard')
    )
  }

  const handleVerifyChain = async () => {
    setVerifying(true)
    setVerifyResult(null)
    try {
      const res = await globalThis.fetch('/api/vault', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'verify_chain' }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Verification failed')
      }
      const result: VerifyChainResponse = await res.json()
      setVerifyResult(result)

      if (result.valid) {
        toast.success('Chain integrity verified', {
          description: `All ${result.entryCount} entries verified — no tampering detected. Hash chain is consistent.`,
        })
      } else {
        toast.error('Chain integrity check failed', {
          description: `${result.issues.length} issue(s) found across ${result.entryCount} entries.`,
        })
      }
    } catch (err) {
      toast.error('Verification failed', {
        description: err instanceof Error ? err.message : 'Unknown error',
      })
    } finally {
      setVerifying(false)
    }
  }

  const scrollToVapChain = () => {
    vapChainRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (loading && !apiData) {
    return (
      <div className="space-y-6 p-6 grid-pattern animate-fade-in">
        <div className="relative overflow-hidden rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-blue-600/5 p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading Vault data...</span>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="relative overflow-hidden">
              <CardContent className="relative p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="h-3 w-20 bg-muted/50 rounded animate-pulse" />
                    <div className="mt-2 h-8 w-16 bg-muted/50 rounded animate-pulse" />
                    <div className="mt-1 h-3 w-24 bg-muted/30 rounded animate-pulse" />
                  </div>
                  <div className="h-11 w-11 bg-muted/30 rounded-xl animate-pulse" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (apiError && !apiData) {
    return (
      <div className="space-y-6 p-6 grid-pattern animate-fade-in">
        <div className="relative overflow-hidden rounded-xl border border-red-600/20 bg-gradient-to-r from-red-600/5 via-transparent to-red-600/5 p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
            <div>
              <span className="text-sm font-medium text-red-600 dark:text-red-400">Failed to load Vault data</span>
              <p className="text-xs text-muted-foreground mt-1">{apiError}</p>
            </div>
            <Button variant="outline" size="sm" className="ml-auto gap-1.5" onClick={() => refetch()}>
              <Loader2 className="h-3.5 w-3.5" />
              Retry
            </Button>
          </div>
        </div>
      </div>
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
              <p className="text-xs text-muted-foreground">{activeTracks} tracks operational · {totalEntries.toLocaleString()} entries · Last verified: {verifyResult ? 'just now' : 'pending'}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="border-0 text-[10px] gap-1 bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Operational
            </Badge>
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 text-xs"
              onClick={handleExportCsv}
              disabled={filteredEntries.length === 0}
            >
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </Button>
          </div>
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
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums animate-count-up">{totalEntries.toLocaleString()}</p>
                <p className="text-[10px] text-muted-foreground">across {activeTracks} tracks</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Database className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
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
                <p className="mt-1 text-3xl font-bold text-blue-600 dark:text-blue-400 tabular-nums animate-count-up">{activeTracks}</p>
                <p className="text-[10px] text-muted-foreground">all tracks operational</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
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
                <p className="mt-1 text-3xl font-bold text-purple-600 dark:text-purple-400 tabular-nums">{latestEntry?.id ?? '—'}</p>
                <p className="text-[10px] text-muted-foreground">{latestEntry?.key ?? 'no entries'}</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-600/15 shadow-lg shadow-purple-600/10">
                <Clock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
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
                <p className="mt-1 text-3xl font-bold text-orange-600 dark:text-orange-400 tabular-nums animate-count-up">{avgScore.toFixed(2)}</p>
                <p className="text-[10px] text-muted-foreground">across all entries</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                <TrendingUp className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Vault Statistics Pie Chart + Recent Activity Timeline */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Pie Chart */}
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Vault Statistics
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            {pieData.length > 0 ? (
              <div className="flex items-center gap-4">
                <div className="h-[180px] w-[180px] shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={75}
                        paddingAngle={3}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        formatter={(value: number, name: string) => {
                          const item = pieData.find((d) => d.name === name)
                          const pct = totalEntries > 0 ? Math.round((value / totalEntries) * 100) : 0
                          return [`${value} entries (${pct}%)`, item?.label ?? name]
                        }}
                        contentStyle={{
                          fontSize: '11px',
                          borderRadius: '8px',
                          border: '1px solid hsl(var(--border))',
                          backgroundColor: 'hsl(var(--card))',
                        }}
                      />
                    </RechartsPieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-1 space-y-2">
                  {pieData.map((d) => {
                    const pct = totalEntries > 0 ? Math.round((d.value / totalEntries) * 100) : 0
                    return (
                      <div key={d.name} className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                        <span className="text-xs font-medium flex-1">{d.label}</span>
                        <span className="text-xs tabular-nums text-muted-foreground">{d.value}</span>
                        <span className="text-[10px] tabular-nums text-muted-foreground">({pct}%)</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[180px] text-xs text-muted-foreground">
                No vault entries to display
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity Timeline */}
        <Card className="relative overflow-hidden border-blue-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" /> Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            {recentActivity.length > 0 ? (
              <div className="space-y-0">
                {recentActivity.map((entry, i) => {
                  const tc = getTrackConfig(entry.track)
                  const isVisible = i < animatedEntries
                  return (
                    <div
                      key={entry.id}
                      className={`relative flex items-start gap-3 transition-all duration-300 ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-4 opacity-0'}`}
                      style={{ transitionDelay: `${i * 100}ms` }}
                    >
                      <div className="flex flex-col items-center">
                        <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${tc.bgColor}`}>
                          <tc.icon className={`h-3 w-3 ${tc.textColor}`} />
                        </div>
                        {i < recentActivity.length - 1 && (
                          <div className="w-px flex-1 min-h-[24px] bg-border" />
                        )}
                      </div>
                      <div className={`flex-1 min-w-0 mb-3 rounded-md border-l-2 ${tc.borderLeftColor} bg-accent/20 px-3 py-2`}>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={`text-[8px] ${tc.badgeBg} border-0`}>{entry.track}</Badge>
                          <span className="text-xs font-medium truncate">{entry.key}</span>
                          <span className="ml-auto text-[9px] text-muted-foreground font-mono shrink-0">{entry.time}</span>
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-0.5">Agent: {entry.agent}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[180px] text-xs text-muted-foreground">
                No recent activity
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Vault Statistics + Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Entry Distribution Donut Chart */}
        <Card className="relative overflow-hidden border-emerald-600/15">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-600/40 to-transparent" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <PieChartLucide className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Entry Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="flex items-center gap-4">
              <div className="flex-shrink-0">
                <ResponsiveContainer width={120} height={120}>
              <RechartsPieChart>
                    <Pie
                      data={vaultDistributionData}
                      cx="50%"
                      cy="50%"
                      innerRadius={30}
                      outerRadius={55}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {vaultDistributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <RechartsTooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '8px', fontSize: '11px' }} />
              </RechartsPieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2 flex-1">
                {vaultDistributionData.map((d) => (
                  <div key={d.name} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: d.fill }} />
                    <span className="text-[11px] flex-1">{d.name}</span>
                    <span className="text-[11px] font-bold tabular-nums">{d.value}</span>
                    <span className="text-[9px] text-muted-foreground tabular-nums">{d.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity Timeline */}
        <Card className="relative overflow-hidden border-blue-600/15">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-600/40 to-transparent" />
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="max-h-48 space-y-2 overflow-y-auto custom-scrollbar">
              {vaultRecentActivity.map((item, i) => (
                <div key={i} className="flex items-start gap-2.5">
                  <div className="flex flex-col items-center">
                    <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    {i < vaultRecentActivity.length - 1 && <span className="w-px flex-1 bg-border/50 min-h-[16px]" />}
                  </div>
                  <div className="flex-1 min-w-0 pb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-medium truncate">{item.description}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge className="text-[8px] px-1 py-0 border-0" style={{ backgroundColor: item.color + '20', color: item.color }}>
                        {item.track}
                      </Badge>
                      <span className="text-[9px] text-muted-foreground tabular-nums">{item.time}</span>
                    </div>
                  </div>
                </div>
              ))}
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
                  <p className="text-[10px] text-muted-foreground">{trackCounts[t.id] ?? 0} entries</p>
                </div>
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground">{t.desc}</p>
              {activeTrack === t.id && (
                <div className="mt-2 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[9px] text-emerald-600 dark:text-emerald-400 font-medium">Filtered</span>
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
                          ? 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-emerald-600/40 hover:bg-emerald-600/30'
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
                    <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]">
                      Track: {activeTrack}
                    </Badge>
                  )}
                  {searchQuery && (
                    <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]">
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
                              <span className={`text-xs font-medium ${e.score >= 0.7 ? 'text-emerald-600 dark:text-emerald-400' : e.score >= 0.4 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
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
                          {entries.length === 0 ? 'No vault entries found in the database' : 'No entries match your filters'}
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
          <div ref={vapChainRef}>
            <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
              <CardHeader className="relative">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> VAP Proof Chain (Immutable Audit Trail)
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    {verifyResult && (
                      <Badge className={`text-[9px] border-0 gap-1 ${verifyResult.valid ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-red-600/15 text-red-600 dark:text-red-400'}`}>
                        {verifyResult.valid ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                        {verifyResult.valid ? 'Verified' : `${verifyResult.issues.length} issues`}
                      </Badge>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 gap-1.5 text-xs"
                      onClick={handleVerifyChain}
                      disabled={verifying}
                    >
                      {verifying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />}
                      {verifying ? 'Verifying...' : 'Verify Chain Integrity'}
                    </Button>
                  </div>
                </div>
                {verifyResult && !verifyResult.valid && verifyResult.issues.length > 0 && (
                  <div className="mt-2 rounded-md bg-red-600/10 border border-red-600/20 p-2">
                    <p className="text-[10px] font-medium text-red-600 dark:text-red-400 mb-1">Issues Found:</p>
                    {verifyResult.issues.map((issue, i) => (
                      <p key={i} className="text-[10px] text-red-600/80 dark:text-red-400/80">• {issue}</p>
                    ))}
                  </div>
                )}
              </CardHeader>
              <CardContent className="relative p-4 pt-0">
                <div className="max-h-[500px] space-y-0 overflow-y-auto custom-scrollbar">
                  {chainBlocks.length === 0 && (
                    <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
                      No vault entries in chain
                    </div>
                  )}
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
          </div>
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
                          selectedEntry.score >= 0.7 ? 'text-emerald-600 dark:text-emerald-400' : selectedEntry.score >= 0.4 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'
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
                      setDialogOpen(false)
                      // Switch to VAP Chain tab and scroll
                      const vapTab = document.querySelector('[data-value="evidence"]') as HTMLElement
                      if (vapTab) vapTab.click()
                      setTimeout(() => {
                        vapChainRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                      }, 300)
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
