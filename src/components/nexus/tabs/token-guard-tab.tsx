'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import {
  Coins,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Activity,
  Clock,
  TrendingUp,
  DollarSign,
  Zap,
  ArrowUpDown,
  ChevronUp,
  ChevronDown,
  Wallet,
  Timer,
} from 'lucide-react'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { NexusBarChart, COLORS } from '@/components/nexus/charts'

// ─── API Response Types ───

interface EconomyData {
  totalTokensConsumed: number
  totalTokensRemaining: number
  utilizationPct: number
  totalBudget: number
  usedBudget: number
}

interface PoolData {
  name: string
  tier: string
  models: string[]
  budget: number
  used: number
  rateLimitRemaining: number
  available: boolean
}

interface AgentBudget {
  id: string
  name: string
  tier: string
  totalBudget: number
  used: number
  remaining: number
  usagePct: number
  timeUntilReset: string
  trustScore: number
}

interface BudgetAllocation {
  name: string
  value: number
  used: number
  remaining: number
}

interface TokenGuardAPIResponse {
  economy: EconomyData
  pools: PoolData[]
  agentBudgets: AgentBudget[]
  budgetAllocation: BudgetAllocation[]
}

// ─── Tier Badge ───

function getTierBadge(tier: string) {
  switch (tier) {
    case 'PREMIUM':
      return <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px] font-bold">PREMIUM</Badge>
    case 'MID':
      return <Badge className="bg-blue-600/15 text-blue-600 dark:text-blue-400 border-0 text-[9px] font-bold">MID</Badge>
    case 'FAST':
      return <Badge className="bg-orange-600/15 text-orange-600 dark:text-orange-400 border-0 text-[9px] font-bold">FAST</Badge>
    case 'HERETIC':
      return <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px] font-bold">HERETIC</Badge>
    case 'ECO':
      return <Badge className="bg-cyan-600/15 text-cyan-600 dark:text-cyan-400 border-0 text-[9px] font-bold">ECO</Badge>
    default:
      return <Badge variant="outline" className="text-[9px]">{tier}</Badge>
  }
}

function getPoolAccent(tier: string) {
  switch (tier) {
    case 'PREMIUM': return { border: 'border-emerald-600/20', bg: 'from-emerald-600/5', text: 'text-emerald-600 dark:text-emerald-400', iconBg: 'bg-emerald-600/15' }
    case 'FAST': return { border: 'border-orange-600/20', bg: 'from-orange-600/5', text: 'text-orange-600 dark:text-orange-400', iconBg: 'bg-orange-600/15' }
    default: return { border: 'border-cyan-600/20', bg: 'from-cyan-600/5', text: 'text-cyan-600 dark:text-cyan-400', iconBg: 'bg-cyan-600/15' }
  }
}

function formatTokens(n: number | undefined | null): string {
  if (n == null || isNaN(n)) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString()
}

// ─── Sortable Agent Budget Table ───

type SortField = 'name' | 'tier' | 'totalBudget' | 'used' | 'remaining' | 'usagePct'
type SortDir = 'asc' | 'desc'

function AgentBudgetTable({ agents }: { agents: AgentBudget[] }) {
  const [sortField, setSortField] = useState<SortField>('usagePct')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const sorted = useMemo(() => {
    return [...agents].sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'name': cmp = a.name.localeCompare(b.name); break
        case 'tier': cmp = a.tier.localeCompare(b.tier); break
        case 'totalBudget': cmp = a.totalBudget - b.totalBudget; break
        case 'used': cmp = a.used - b.used; break
        case 'remaining': cmp = a.remaining - b.remaining; break
        case 'usagePct': cmp = a.usagePct - b.usagePct; break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [agents, sortField, sortDir])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 text-muted-foreground/30" />
    return sortDir === 'asc' ? <ChevronUp className="h-3 w-3 text-emerald-600" /> : <ChevronDown className="h-3 w-3 text-emerald-600" />
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-[10px] text-muted-foreground uppercase tracking-wider">
            <th className="p-2 font-medium">
              <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort('name')}>
                Agent {renderSortIcon('name')}
              </button>
            </th>
            <th className="p-2 font-medium">
              <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort('tier')}>
                Tier {renderSortIcon('tier')}
              </button>
            </th>
            <th className="p-2 font-medium">
              <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort('totalBudget')}>
                Budget {renderSortIcon('totalBudget')}
              </button>
            </th>
            <th className="p-2 font-medium">
              <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort('used')}>
                Used {renderSortIcon('used')}
              </button>
            </th>
            <th className="p-2 font-medium">
              <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort('remaining')}>
                Remaining {renderSortIcon('remaining')}
              </button>
            </th>
            <th className="p-2 font-medium">
              <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort('usagePct')}>
                Usage % {renderSortIcon('usagePct')}
              </button>
            </th>
            <th className="p-2 font-medium">Reset</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((a) => (
            <tr key={a.id} className="border-b border-border/30 hover:bg-accent/30 transition-colors">
              <td className="p-2 text-xs font-medium">{a.name}</td>
              <td className="p-2">{getTierBadge(a.tier)}</td>
              <td className="p-2 text-xs tabular-nums">{formatTokens(a.totalBudget)}</td>
              <td className="p-2">
                <div className="flex items-center gap-2">
                  <Progress value={a.usagePct} className="h-1.5 w-12" />
                  <span className="text-[10px] tabular-nums text-muted-foreground">{formatTokens(a.used)}</span>
                </div>
              </td>
              <td className="p-2 text-xs tabular-nums text-muted-foreground">{formatTokens(a.remaining)}</td>
              <td className="p-2">
                <span className={`text-xs font-bold tabular-nums ${
                  (a.usagePct ?? 0) >= 90 ? 'text-red-600 dark:text-red-400' :
                  (a.usagePct ?? 0) >= 70 ? 'text-orange-600 dark:text-orange-400' :
                  'text-emerald-600 dark:text-emerald-400'
                }`}>
                  {(a.usagePct ?? 0).toFixed(1)}%
                </span>
              </td>
              <td className="p-2">
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Timer className="h-3 w-3" />
                  {a.timeUntilReset}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Main Component ───

export function TokenGuardTab() {
  const { data: apiData, loading, error: apiError, refetch } = useApiData<TokenGuardAPIResponse>('/api/token-guard', 15000)

  const economy = useMemo(() => apiData?.economy ?? { totalTokensConsumed: 0, totalTokensRemaining: 0, utilizationPct: 0, totalBudget: 0, usedBudget: 0 }, [apiData?.economy])
  const pools = useMemo(() => apiData?.pools ?? [], [apiData?.pools])
  const agentBudgets = useMemo(() => apiData?.agentBudgets ?? [], [apiData?.agentBudgets])
  const budgetAllocation = useMemo(() => apiData?.budgetAllocation ?? [], [apiData?.budgetAllocation])

  // Bar chart for budget allocation
  const allocationChartData = useMemo(() => {
    return budgetAllocation.map((b) => ({
      name: b.name,
      value: b.value,
      used: b.used,
      remaining: b.remaining,
    }))
  }, [budgetAllocation])

  if (loading && !apiData) {
    return (
      <div className="space-y-6 p-6 grid-pattern animate-fade-in">
        <div className="relative overflow-hidden rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-emerald-600/5 p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading TokenGuard Economy data...</span>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="relative overflow-hidden">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="h-3 w-20 bg-muted/50 rounded animate-pulse" />
                    <div className="mt-2 h-8 w-16 bg-muted/50 rounded animate-pulse" />
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
              <span className="text-sm font-medium text-red-600 dark:text-red-400">Failed to load TokenGuard data</span>
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
      {/* TokenGuard Header Banner */}
      <div className="relative overflow-hidden rounded-xl border border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-cyan-600/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-md">
              <Coins className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold">TokenGuard Economy</h2>
              <p className="text-xs text-muted-foreground">Token budget management · {economy.utilizationPct}% utilized</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <DataSourceBadge source="api" />
            <Badge className={`border-0 text-[10px] gap-1 ${
              economy.utilizationPct < 70
                ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                : economy.utilizationPct < 90
                  ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
                  : 'bg-red-600/15 text-red-600 dark:text-red-400'
            }`}>
              <Coins className="h-2.5 w-2.5" />
              {economy.utilizationPct < 70 ? 'HEALTHY' : economy.utilizationPct < 90 ? 'CAUTION' : 'CRITICAL'}
            </Badge>
          </div>
        </div>
      </div>

      {/* Total Economy Overview - Big Number Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-emerald-600/20 hover-lift">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Tokens Consumed</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{formatTokens(economy.totalTokensConsumed)}</p>
                <p className="text-[10px] text-muted-foreground">across all agents</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15">
                <TrendingUp className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-cyan-600/20 hover-lift">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Tokens Remaining</p>
                <p className="mt-1 text-3xl font-bold text-cyan-600 dark:text-cyan-400 tabular-nums">{formatTokens(economy.totalTokensRemaining)}</p>
                <p className="text-[10px] text-muted-foreground">of {formatTokens(economy.totalBudget)} budget</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-600/15">
                <Wallet className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className={`${economy.utilizationPct >= 90 ? 'border-red-600/20' : economy.utilizationPct >= 70 ? 'border-yellow-600/20' : 'border-emerald-600/20'} hover-lift`}>
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Overall Utilization</p>
                <p className={`mt-1 text-3xl font-bold tabular-nums ${
                  economy.utilizationPct >= 90 ? 'text-red-600 dark:text-red-400' :
                  economy.utilizationPct >= 70 ? 'text-yellow-600 dark:text-yellow-400' :
                  'text-emerald-600 dark:text-emerald-400'
                }`}>
                  {economy.utilizationPct}%
                </p>
                <Progress value={economy.utilizationPct} className="h-1.5 mt-2" />
              </div>
              <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${
                economy.utilizationPct >= 90 ? 'bg-red-600/15' :
                economy.utilizationPct >= 70 ? 'bg-yellow-600/15' :
                'bg-emerald-600/15'
              }`}>
                <DollarSign className={`h-5 w-5 ${
                  economy.utilizationPct >= 90 ? 'text-red-600 dark:text-red-400' :
                  economy.utilizationPct >= 70 ? 'text-yellow-600 dark:text-yellow-400' :
                  'text-emerald-600 dark:text-emerald-400'
                }`} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Model Pools - 3 Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {pools.map((pool) => {
          const accent = getPoolAccent(pool.tier)
          const usagePct = pool.budget > 0 ? Math.round((pool.used / pool.budget) * 100) : 0

          return (
            <Card key={pool.tier} className={`relative overflow-hidden ${accent.border} hover-lift`}>
              <div className={`absolute inset-0 bg-gradient-to-br ${accent.bg} via-transparent to-transparent`} />
              <CardHeader className="relative pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Zap className={`h-4 w-4 ${accent.text}`} />
                    {pool.name}
                  </CardTitle>
                  {getTierBadge(pool.tier)}
                </div>
              </CardHeader>
              <CardContent className="relative p-4 pt-0 space-y-3">
                {/* Models List */}
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground mb-1">Available Models</p>
                  <div className="flex flex-wrap gap-1">
                    {pool.models.length > 0 ? pool.models.map((m) => (
                      <Badge key={m} variant="outline" className="text-[8px] h-5">{m}</Badge>
                    )) : (
                      <span className="text-[10px] text-muted-foreground">No models assigned</span>
                    )}
                  </div>
                </div>

                {/* Budget Bar */}
                <div>
                  <div className="flex items-center justify-between text-[10px] mb-1">
                    <span className="text-muted-foreground">Budget</span>
                    <span className="font-medium tabular-nums">{formatTokens(pool.used)} / {formatTokens(pool.budget)}</span>
                  </div>
                  <Progress value={usagePct} className="h-2" />
                  <p className="text-[9px] text-muted-foreground mt-0.5">{usagePct}% used</p>
                </div>

                {/* Rate Limit */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">Rate Limit Remaining</span>
                  <span className={`text-xs font-bold tabular-nums ${pool.rateLimitRemaining > 20 ? 'text-emerald-600 dark:text-emerald-400' : pool.rateLimitRemaining > 5 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                    {pool.rateLimitRemaining}
                  </span>
                </div>

                {/* Availability */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground">Availability</span>
                  <Badge className={`border-0 text-[9px] gap-1 ${pool.available ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-red-600/15 text-red-600 dark:text-red-400'}`}>
                    {pool.available ? <CheckCircle2 className="h-2.5 w-2.5" /> : <XCircle className="h-2.5 w-2.5" />}
                    {pool.available ? 'Available' : 'Unavailable'}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Agent Budget Table + Budget Allocation Chart */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Agent Budget Table */}
        <Card className="lg:col-span-2 border-emerald-600/15">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Agent Budget Table
              <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]">{agentBudgets.length} agents</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {agentBudgets.length > 0 ? (
              <div className="max-h-80 overflow-y-auto custom-scrollbar">
                <AgentBudgetTable agents={agentBudgets} />
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-xs text-muted-foreground">
                No agent budgets to display
              </div>
            )}
          </CardContent>
        </Card>

        {/* Budget Allocation Chart */}
        <Card className="border-emerald-600/15">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Budget Allocation
              <DataSourceBadge source="computed" />
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {allocationChartData.length > 0 ? (
              <>
                <NexusBarChart
                  data={allocationChartData}
                  dataKey="value"
                  nameKey="name"
                  color={COLORS.emerald}
                  height={140}
                />
                <div className="mt-3 space-y-2">
                  {allocationChartData.map((d) => {
                    const pct = d.value > 0 ? Math.round((d.used / d.value) * 100) : 0
                    return (
                      <div key={d.name} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium">{d.name}</span>
                          <span className="text-muted-foreground tabular-nums">{formatTokens(d.used)} / {formatTokens(d.value)}</span>
                        </div>
                        <Progress value={pct} className="h-1.5" />
                      </div>
                    )
                  })}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-32 text-xs text-muted-foreground">
                No budget allocation data
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
