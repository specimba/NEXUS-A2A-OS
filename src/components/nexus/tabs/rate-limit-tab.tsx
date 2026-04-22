'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Gauge, Key, Clock, AlertTriangle, CheckCircle2, XCircle, Activity,
  Database, RefreshCw, Loader2, ShieldAlert, Zap, Timer, Layers, Hash,
  TrendingUp, Server, Wifi, WifiOff,
} from 'lucide-react'
import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { toast } from 'sonner'
import { NexusBarChart } from '@/components/nexus/charts'

// ── Types ──────────────────────────────────────────────────────────

interface ProviderStatus {
  provider: string
  config: { rpm: number; rpd: number; description: string; color: string; baseUrl: string }
  rpm: { used: number; limit: number; remaining: number; percentUsed: number }
  rpd: { used: number; limit: number; remaining: number; percentUsed: number }
  isCooldown: boolean
  cooldownUntil: number
  cooldownRemainingMs: number
  consecutive429s: number
  lastError: string | null
  totalRequests: number
  totalRejected: number
  queue: { pending: number; processing: number; completed: number }
  dedup: { size: number; hitRate: number }
  cache: { size: number; hitRate: number; hits: number; misses: number }
  keyHealth: { hasKey: boolean; keyMasked: string; lastUsed: number | null }
}

interface KeyInfo {
  id: string
  provider: string
  masked: string
  isActive: boolean
  health: string
  requestsMade: number
  requestsRemaining: number
  lastError: string | null
  cooldownUntil: number
  lastUsed: number | null
  totalRequests: number
  total429s: number
  successRate: number
}

interface SummaryData {
  totalProviders: number
  healthyProviders: number
  rateLimitedProviders: number
  totalRequests: number
  rateLimitedCount: number
  cachedCount: number
  dedupedCount: number
  errorCount: number
  totalQueueSize: number
  cacheHitRate: number
  dedupSize: number
}

interface StatusResponse {
  timestamp: string
  summary: SummaryData
  providers: ProviderStatus[]
  keys: Record<string, { provider: string; keys: KeyInfo[]; totalKeys: number; healthyKeys: number; hasAvailableKey: boolean }>
  cache: { size: number; maxSize: number; hits: number; misses: number; hitRate: number; evictions: number }
  providerStats: Record<string, { total: number; rateLimited: number; cached: number; errors: number; avgResponseTime: number }>
}

// ── Provider Icons & Colors ────────────────────────────────────────

const PROVIDER_META: Record<string, { icon: React.ReactNode; gradient: string; borderColor: string }> = {
  openrouter: { icon: <Zap className="h-4 w-4" />, gradient: 'from-emerald-600/10 via-emerald-600/5 to-transparent', borderColor: 'border-emerald-600/20' },
  jina: { icon: <Database className="h-4 w-4" />, gradient: 'from-blue-600/10 via-blue-600/5 to-transparent', borderColor: 'border-blue-600/20' },
  kilocode: { icon: <Layers className="h-4 w-4" />, gradient: 'from-purple-600/10 via-purple-600/5 to-transparent', borderColor: 'border-purple-600/20' },
  cerebras: { icon: <Activity className="h-4 w-4" />, gradient: 'from-amber-600/10 via-amber-600/5 to-transparent', borderColor: 'border-amber-600/20' },
  openai: { icon: <Server className="h-4 w-4" />, gradient: 'from-red-600/10 via-red-600/5 to-transparent', borderColor: 'border-red-600/20' },
}

function getProviderColor(provider: string): string {
  const colors: Record<string, string> = { openrouter: '#10b981', jina: '#3b82f6', kilocode: '#8b5cf6', cerebras: '#f59e0b', openai: '#ef4444' }
  return colors[provider] ?? '#6b7280'
}

function formatCooldown(ms: number): string {
  if (ms <= 0) return '0s'
  const seconds = Math.ceil(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

function getHealthColor(percentUsed: number): string {
  if (percentUsed < 50) return 'text-emerald-600 dark:text-emerald-400'
  if (percentUsed < 80) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}

function getProgressColor(percentUsed: number): string {
  if (percentUsed < 50) return 'bg-emerald-500'
  if (percentUsed < 80) return 'bg-yellow-500'
  return 'bg-red-500'
}

function getKeyHealthBadge(health: string): { label: string; className: string } {
  switch (health) {
    case 'healthy': return { label: 'HEALTHY', className: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0' }
    case 'degraded': return { label: 'DEGRADED', className: 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0' }
    case 'rate_limited': return { label: 'RATE LIMITED', className: 'bg-red-600/15 text-red-600 dark:text-red-400 border-0' }
    case 'error': return { label: 'ERROR', className: 'bg-red-600/15 text-red-600 dark:text-red-400 border-0' }
    case 'no_key': return { label: 'NO KEY', className: 'bg-gray-600/15 text-gray-500 dark:text-gray-400 border-0' }
    default: return { label: 'UNKNOWN', className: 'bg-gray-600/15 text-gray-500 border-0' }
  }
}

// ── Usage Bar ──────────────────────────────────────────────────────

function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
  const percent = limit > 0 ? Math.min(100, (used / limit) * 100) : 0
  const remaining = Math.max(0, limit - used)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-muted-foreground">{label}</span>
        <span className="text-[10px] tabular-nums">
          <span className={getHealthColor(percent)}>{used}</span>
          <span className="text-muted-foreground">/{limit}</span>
          <span className="ml-1.5 text-muted-foreground/70">({remaining} left)</span>
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted/50 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${getProgressColor(percent)}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

// ── Cooldown Timer ─────────────────────────────────────────────────

function CooldownTimer({ endTime }: { endTime: number }) {
  const [remaining, setRemaining] = useState(Math.max(0, endTime - Date.now()))
  useEffect(() => {
    const interval = setInterval(() => {
      const r = Math.max(0, endTime - Date.now())
      setRemaining(r)
      if (r <= 0) clearInterval(interval)
    }, 1000)
    return () => clearInterval(interval)
  }, [endTime])
  if (remaining <= 0) return null
  return (
    <div className="flex items-center gap-1.5 rounded-md bg-red-600/10 px-2 py-1">
      <Timer className="h-3 w-3 text-red-600 dark:text-red-400" />
      <span className="text-[10px] font-medium text-red-600 dark:text-red-400 tabular-nums">Cooldown: {formatCooldown(remaining)}</span>
    </div>
  )
}

// ── Provider Card ──────────────────────────────────────────────────

function ProviderCard({ status, keyInfo }: { status: ProviderStatus; keyInfo?: KeyInfo }) {
  const meta = PROVIDER_META[status.provider] ?? PROVIDER_META.openrouter
  const color = getProviderColor(status.provider)
  return (
    <Card className={`relative overflow-hidden ${meta.borderColor} shadow-lg hover-lift`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${meta.gradient}`} />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <span style={{ color }}>{meta.icon}</span>
            <span className="capitalize">{status.provider}</span>
            {status.isCooldown && <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">COOLDOWN</Badge>}
            {!status.keyHealth.hasKey && <Badge className="bg-gray-600/15 text-gray-500 border-0 text-[9px]">NO KEY</Badge>}
          </CardTitle>
          <div className="flex items-center gap-2">
            {keyInfo && <Badge className={getKeyHealthBadge(keyInfo.health).className}>{getKeyHealthBadge(keyInfo.health).label}</Badge>}
            {status.queue.pending > 0 && <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[9px]">{status.queue.pending} QUEUED</Badge>}
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground">{status.config.description}</p>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-3">
        <UsageBar used={status.rpm.used} limit={status.rpm.limit} label="RPM" />
        <UsageBar used={status.rpd.used} limit={status.rpd.limit} label="RPD" />
        {status.isCooldown && <CooldownTimer endTime={status.cooldownUntil} />}
        {status.lastError && (
          <div className="flex items-start gap-1.5 rounded-md bg-red-600/5 px-2 py-1.5">
            <AlertTriangle className="h-3 w-3 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
            <span className="text-[10px] text-red-600 dark:text-red-400 break-all">{status.lastError}</span>
          </div>
        )}
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Total', value: status.totalRequests },
            { label: 'Rejected', value: status.totalRejected, color: 'text-red-600 dark:text-red-400' },
            { label: '429s', value: status.consecutive429s, color: 'text-orange-600 dark:text-orange-400' },
            { label: 'Queue', value: status.queue.pending },
          ].map((stat) => (
            <TooltipProvider key={stat.label}>
              <Tooltip><TooltipTrigger asChild><div className="text-center rounded-md bg-accent/20 px-1.5 py-1.5">
                <p className="text-[10px] text-muted-foreground">{stat.label}</p>
                <p className={`text-sm font-bold tabular-nums ${stat.color ?? ''}`}>{stat.value}</p>
              </div></TooltipTrigger><TooltipContent>{stat.label}</TooltipContent></Tooltip>
            </TooltipProvider>
          ))}
        </div>
        <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1 border-t border-border/50">
          <div className="flex items-center gap-1.5"><Key className="h-3 w-3" /><span className="font-mono">{status.keyHealth.keyMasked}</span></div>
          {keyInfo && <div className="flex items-center gap-1.5"><span>Success: {keyInfo.successRate}%</span></div>}
        </div>
      </CardContent>
    </Card>
  )
}

// ── Main Rate Limit Tab ────────────────────────────────────────────

export function RateLimitTab() {
  const [data, setData] = useState<StatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const tickRef = useRef(0)

  const fetchData = useCallback(async () => {
    try {
      const res = await globalThis.fetch('/api/rate-limit/status')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  useEffect(() => {
    const interval = setInterval(() => {
      tickRef.current++
      if (document.visibilityState === 'visible') fetchData()
    }, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handleRefresh = useCallback(() => {
    setRefreshing(true)
    toast.promise(fetchData(), { loading: 'Refreshing...', success: 'Data refreshed', error: 'Failed' })
  }, [fetchData])

  const summary = useMemo(() => data?.summary ?? null, [data])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-600 dark:text-emerald-400" />
          <p className="text-sm text-muted-foreground">Loading rate limit data...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <ShieldAlert className="h-8 w-8 text-red-600 dark:text-red-400" />
          <p className="text-sm text-red-600 dark:text-red-400">Failed to load rate limit data</p>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={handleRefresh}><RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Retry</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-6 grid-pattern">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Gauge className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            API Rate Limit Control Center
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">Monitor and manage API rate limits across all providers · Auto-refreshes every 10s</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing} className="gap-1.5">
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {/* Summary Stat Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: 'Providers', value: `${summary.healthyProviders}/${summary.totalProviders}`, icon: Activity, border: 'border-emerald-600/20', gradient: 'from-emerald-600/10 via-emerald-600/5 to-transparent', iconBg: 'bg-emerald-600/15', iconText: 'text-emerald-600 dark:text-emerald-400' },
            { label: 'Total Requests', value: summary.totalRequests, icon: Hash, border: 'border-blue-600/20', gradient: 'from-blue-600/10 via-blue-600/5 to-transparent', iconBg: 'bg-blue-600/15', iconText: 'text-blue-600 dark:text-blue-400' },
            { label: 'Rate Limited', value: summary.rateLimitedCount, icon: AlertTriangle, border: 'border-red-600/20', gradient: 'from-red-600/10 via-red-600/5 to-transparent', iconBg: 'bg-red-600/15', iconText: 'text-red-600 dark:text-red-400' },
            { label: 'Cached', value: summary.cachedCount, icon: Database, border: 'border-emerald-600/20', gradient: 'from-emerald-600/10 via-emerald-600/5 to-transparent', iconBg: 'bg-emerald-600/15', iconText: 'text-emerald-600 dark:text-emerald-400' },
            { label: 'Queue', value: summary.totalQueueSize, icon: Clock, border: 'border-yellow-600/20', gradient: 'from-yellow-600/10 via-yellow-600/5 to-transparent', iconBg: 'bg-yellow-600/15', iconText: 'text-yellow-600 dark:text-yellow-400' },
            { label: 'Hit Rate', value: `${(summary.cacheHitRate * 100).toFixed(0)}%`, icon: Zap, border: 'border-purple-600/20', gradient: 'from-purple-600/10 via-purple-600/5 to-transparent', iconBg: 'bg-purple-600/15', iconText: 'text-purple-600 dark:text-purple-400' },
          ].map((card) => (
            <Card key={card.label} className={`relative overflow-hidden ${card.border} hover-lift`}>
              <div className={`absolute inset-0 bg-gradient-to-br ${card.gradient}`} />
              <CardContent className="relative p-3">
                <div className="flex items-center gap-2">
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${card.iconBg}`}>
                    <card.icon className={`h-4 w-4 ${card.iconText}`} />
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground">{card.label}</p>
                    <p className="text-lg font-bold tabular-nums">{card.value}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Alert Banner */}
      {summary && summary.rateLimitedProviders > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-red-600/30 bg-red-600/5 px-4 py-3">
          <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-600 dark:text-red-400">{summary.rateLimitedProviders} provider(s) currently rate-limited</p>
            <p className="text-xs text-muted-foreground">Requests queued until cooldown expires.</p>
          </div>
        </div>
      )}

      {/* Provider Cards Grid */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {data.providers.map((provider) => (
            <ProviderCard key={provider.provider} status={provider} keyInfo={data.keys[provider.provider]?.keys[0]} />
          ))}
        </div>
      )}

      {/* Cache Stats + Key Health */}
      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <CardTitle className="text-sm flex items-center gap-2"><Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> API Response Cache</CardTitle>
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Hit Rate', value: `${(data.cache.hitRate * 100).toFixed(0)}%`, highlight: true },
                  { label: 'Cache Size', value: `${data.cache.size}/${data.cache.maxSize}` },
                  { label: 'Hits', value: data.cache.hits, highlight: true },
                  { label: 'Misses', value: data.cache.misses },
                ].map((item) => (
                  <div key={item.label} className="rounded-lg bg-accent/20 px-3 py-2.5">
                    <p className="text-[10px] text-muted-foreground">{item.label}</p>
                    <p className={`text-lg font-bold tabular-nums ${item.highlight ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>{item.value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-muted-foreground">Cache Efficiency</span>
                  <span className="text-[10px] tabular-nums text-emerald-600 dark:text-emerald-400">{(data.cache.hitRate * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted/50 overflow-hidden">
                  <div className="h-full rounded-full bg-emerald-500 transition-all duration-500" style={{ width: `${data.cache.hitRate * 100}%` }} />
                </div>
                <span className="text-[9px] text-muted-foreground">Evictions: {data.cache.evictions}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-blue-600/20 shadow-lg">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <CardTitle className="text-sm flex items-center gap-2"><Key className="h-4 w-4 text-blue-600 dark:text-blue-400" /> API Key Health</CardTitle>
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              <div className="space-y-2">
                {Object.entries(data.keys).map(([provider, keyData]) => (
                  <div key={provider} className="flex items-center gap-3 rounded-lg border bg-accent/20 px-3 py-2 transition-colors hover:bg-accent/30">
                    <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: getProviderColor(provider) }} />
                    <span className="text-xs font-medium capitalize min-w-[80px]">{provider}</span>
                    <span className="text-[10px] text-muted-foreground w-16 text-center tabular-nums">{keyData.totalKeys} key{keyData.totalKeys !== 1 ? 's' : ''}</span>
                    <div className="flex items-center gap-1 flex-1">
                      {keyData.keys.map((key) => {
                        const badge = getKeyHealthBadge(key.health)
                        return (
                          <TooltipProvider key={key.id}>
                            <Tooltip><TooltipTrigger asChild><div className={`flex items-center gap-1 rounded-md px-1.5 py-0.5 ${badge.className}`}>
                              {key.health === 'healthy' && <CheckCircle2 className="h-2.5 w-2.5" />}
                              {key.health === 'rate_limited' && <XCircle className="h-2.5 w-2.5" />}
                              {key.health === 'no_key' && <WifiOff className="h-2.5 w-2.5" />}
                              <span className="text-[8px] font-mono">{key.masked}</span>
                            </div></TooltipTrigger>
                            <TooltipContent><div className="text-[10px] space-y-0.5"><p>Key: {key.masked}</p><p>Health: {key.health}</p><p>Success: {key.successRate}%</p><p>429s: {key.total429s}</p></div></TooltipContent></Tooltip>
                          </TooltipProvider>
                        )
                      })}
                    </div>
                    {keyData.hasAvailableKey ? <Wifi className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" /> : <WifiOff className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Provider Usage Chart */}
      {data?.providerStats && (
        <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2"><TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Provider Usage</CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            <NexusBarChart
              data={Object.entries(data.providerStats).map(([provider, stats]) => ({
                name: provider.charAt(0).toUpperCase() + provider.slice(1),
                value: stats.total,
              }))}
              dataKey="value"
              color="#10b981"
              height={200}
            />
          </CardContent>
        </Card>
      )}

      {/* Info Footer */}
      <div className="flex items-center justify-center gap-4 text-[10px] text-muted-foreground/50 pt-2">
        <span>Token bucket rate limiting</span><span>·</span>
        <span>LRU response cache</span><span>·</span>
        <span>Request deduplication</span><span>·</span>
        <span>Automatic key rotation</span><span>·</span>
        <span>Exponential backoff</span>
      </div>
    </div>
  )
}
