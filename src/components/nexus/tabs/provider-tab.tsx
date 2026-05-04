'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { Checkbox } from '@/components/ui/checkbox'
import { ApiKeyEntry } from '@/components/nexus/api-key-entry'
import {
  Server,
  Activity,
  Zap,
  Gauge,
  Wifi,
  WifiOff,
  RefreshCw,
  TestTube2,
  ChevronDown,
  ChevronUp,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  Timer,
  ArrowRight,
  Key,
  Hash,
  Cpu,
  Globe,
  BarChart3,
  Info,
  CircleDot,
  Flame,
  Sparkles,
  Trophy,
  Swords,
  Plus,
  Trash2,
  Lock,
  Eye,
  EyeOff,
  Shield,
} from 'lucide-react'
import { useState, useMemo, useCallback, useRef } from 'react'
import { toast } from 'sonner'

// ── Types matching API response ──────────────────────────────────

type HealthStatus = 'healthy' | 'degraded' | 'down' | 'unknown'
type ModelTier = 'reasoning' | 'balanced' | 'fast' | 'free'

interface ProviderModel {
  id: string
  tier: ModelTier
  displayName: string
  actualModel: string
  health: HealthStatus
  latencyMs: number
  totalCalls: number
  successRate: number
  capabilities: string[]
  contextWindow: number
  rateLimitPerMin: number
  isFree: boolean
}

interface KeyStatus {
  totalKeys: number
  healthyKeys: number
  hasAvailableKey: boolean
  activeKeyMasked: string | null
}

interface RateLimitInfo {
  rpm: number
  rpd: number
  remaining: { rpm: number; rpd: number }
  isCooldown: boolean
  cooldownRemainingMs: number
  description: string
}

interface ProviderDetail {
  provider: string
  label: string
  isAvailable: boolean
  activeModels: number
  totalModels: number
  health: HealthStatus
  rateLimitRemaining: number
  avgLatencyMs: number
  models: ProviderModel[]
  keyStatus: KeyStatus
  rateLimits: RateLimitInfo
}

interface ProvidersListResponse {
  providers: ProviderDetail[]
  modelRoutes: Array<{
    id: string
    tier: ModelTier
    displayName: string
    actualModel: string
    provider: string
    providerLabel: string
    isFree: boolean
    health: HealthStatus
  }>
  tiers: Record<ModelTier, string[]>
  summary: {
    totalProviders: number
    availableProviders: number
    totalModels: number
    healthyModels: number
  }
}

interface TestResultModel {
  id: string
  displayName: string
  actualModel: string
  tier: ModelTier
}

interface ProviderTestResultItem {
  provider: string
  model: TestResultModel
  success: boolean
  latencyMs: number
  tokenCount: number
  response: string | null
  error: string | null
  rateLimitRemaining: { rpm: number; rpd: number }
  keyAvailable: boolean
}

interface ProviderQuotaModel {
  id: string
  displayName: string
  tier: ModelTier
  rateLimitPerMin: number
}

interface ProviderQuotaInfo {
  provider: string
  description: string
  rateLimits: {
    rpm: { limit: number; used: number; remaining: number; percentUsed: number }
    rpd: { limit: number; used: number; remaining: number; percentUsed: number }
  }
  cooldown: {
    isActive: boolean
    until: number | null
    remainingMs: number
    reason: string | null
  }
  requestStats: {
    totalRequests: number
    totalRejected: number
    consecutive429s: number
  }
  keyHealth: {
    totalKeys: number
    healthyKeys: number
    hasAvailableKey: boolean
    primaryMasked: string | null
  }
  models: ProviderQuotaModel[]
  queue: {
    pending: number
    processing: number
    completed: number
  }
  cache: {
    size: number
    hitRate: number
    hits: number
    misses: number
  }
}

interface QuotasResponse {
  providers: ProviderQuotaInfo[]
  summary: {
    totalProviders: number
    providersInCooldown: number
    totalRequestsToday: number
    totalKeysAvailable: number
    overallHealth: 'healthy' | 'degraded' | 'critical'
  }
}

// ── Constants ─────────────────────────────────────────────────────

const HEALTH_CONFIG: Record<string, { color: string; textColor: string; bgColor: string; label: string }> = {
  healthy: {
    color: '#34d399',
    textColor: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-600/15',
    label: 'Healthy',
  },
  degraded: {
    color: '#facc15',
    textColor: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-600/15',
    label: 'Degraded',
  },
  down: {
    color: '#f87171',
    textColor: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-600/15',
    label: 'Down',
  },
  unknown: {
    color: '#a3a3a3',
    textColor: 'text-neutral-500 dark:text-neutral-400',
    bgColor: 'bg-neutral-600/15',
    label: 'Unknown',
  },
}

const TIER_CONFIG: Record<string, { icon: string; label: string; color: string; textColor: string; bgColor: string; borderColor: string }> = {
  reasoning: {
    icon: '🧠',
    label: 'Reasoning',
    color: '#a78bfa',
    textColor: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-600/15',
    borderColor: 'border-purple-600/20',
  },
  balanced: {
    icon: '⚖️',
    label: 'Balanced',
    color: '#60a5fa',
    textColor: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-600/15',
    borderColor: 'border-blue-600/20',
  },
  fast: {
    icon: '⚡',
    label: 'Fast',
    color: '#fb923c',
    textColor: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-600/15',
    borderColor: 'border-orange-600/20',
  },
  free: {
    icon: '🆓',
    label: 'Free',
    color: '#34d399',
    textColor: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-600/15',
    borderColor: 'border-emerald-600/20',
  },
}

const PROVIDER_ICONS: Record<string, string> = {
  'z-ai': '🤖',
  nvidia: '🟢',
  openrouter: '🔵',
  groq: '⚡',
  cerebras: '🟣',
  scaleway: '🟠',
  fireworks: '🎆',
  alibaba: '☁️',
  mistral: '🌀',
}

// ── Helper ────────────────────────────────────────────────────────

function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatContextWindow(tokens: number): string {
  if (tokens >= 131072) return '128K'
  if (tokens >= 65536) return '64K'
  if (tokens >= 32768) return '32K'
  if (tokens >= 16384) return '16K'
  return `${Math.round(tokens / 1024)}K`
}

// ── Provider Test Panel ───────────────────────────────────────────

function ProviderTestPanel({
  provider,
  onClose,
}: {
  provider: ProviderDetail
  onClose: () => void
}) {
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<ProviderTestResultItem | null>(null)

  const runTest = useCallback(async () => {
    setTesting(true)
    setResult(null)
    try {
      const res = await globalThis.fetch('/api/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: provider.provider }),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        toast.error(`Test failed: ${errData.error || res.statusText}`)
        return
      }
      const data = await res.json()
      if (data.results && data.results.length > 0) {
        setResult(data.results[0])
        if (data.results[0].success) {
          toast.success(`${provider.label} test passed — ${data.results[0].latencyMs}ms`)
        } else {
          toast.error(`${provider.label} test failed — ${data.results[0].error || 'Unknown error'}`)
        }
      }
    } catch (err) {
      toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setTesting(false)
    }
  }, [provider])

  const healthCfg = HEALTH_CONFIG[provider.health] || HEALTH_CONFIG.unknown

  return (
    <Dialog open={true} onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Server className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Test Provider: {provider.label}
          </DialogTitle>
          <DialogDescription>
            Run a connectivity and response test against {provider.label}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Provider Summary */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Health</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`h-2.5 w-2.5 rounded-full ${healthCfg.bgColor}`} style={{ backgroundColor: healthCfg.color }} />
                <span className={`text-sm font-semibold ${healthCfg.textColor}`}>{healthCfg.label}</span>
              </div>
            </div>
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Avg Latency</p>
              <p className="text-sm font-semibold tabular-nums mt-1">{formatLatency(provider.avgLatencyMs)}</p>
            </div>
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Models</p>
              <p className="text-sm font-semibold tabular-nums mt-1">{provider.activeModels}/{provider.totalModels}</p>
            </div>
            <div className="rounded-lg bg-accent/30 p-3">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">API Key</p>
              <p className="text-sm font-semibold mt-1">
                {provider.keyStatus.hasAvailableKey ? (
                  <span className="text-emerald-600 dark:text-emerald-400">{provider.keyStatus.activeKeyMasked || 'Available'}</span>
                ) : (
                  <span className="text-red-600 dark:text-red-400">No key</span>
                )}
              </p>
            </div>
          </div>

          {/* Test Button */}
          <Button
            onClick={runTest}
            disabled={testing}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            {testing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Testing {provider.label}...
              </>
            ) : (
              <>
                <TestTube2 className="h-4 w-4 mr-2" />
                Run Provider Test
              </>
            )}
          </Button>

          {/* Test Result */}
          {result && (
            <div className={`rounded-lg border p-4 space-y-3 ${
              result.success
                ? 'border-emerald-600/20 bg-emerald-600/5'
                : 'border-red-600/20 bg-red-600/5'
            }`}>
              <div className="flex items-center gap-2">
                {result.success ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                )}
                <span className={`font-semibold ${result.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {result.success ? 'Test Passed' : 'Test Failed'}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase">Latency</p>
                  <p className="text-sm font-bold tabular-nums">{formatLatency(result.latencyMs)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase">Tokens</p>
                  <p className="text-sm font-bold tabular-nums">{result.tokenCount}</p>
                </div>
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase">Model</p>
                  <p className="text-sm font-bold truncate">{result.model.displayName}</p>
                </div>
              </div>

              {result.response && (
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase mb-1">Response Preview</p>
                  <pre className="text-xs bg-muted/50 rounded-md p-2.5 max-h-32 overflow-y-auto custom-scrollbar font-mono whitespace-pre-wrap">
                    {result.response.slice(0, 300)}
                  </pre>
                </div>
              )}

              {result.error && (
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase mb-1">Error</p>
                  <pre className="text-xs bg-red-600/10 rounded-md p-2.5 font-mono whitespace-pre-wrap text-red-600 dark:text-red-400">
                    {result.error}
                  </pre>
                </div>
              )}

              <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                <span>RPM remaining: <span className="font-bold tabular-nums">{result.rateLimitRemaining.rpm}</span></span>
                <span>RPD remaining: <span className="font-bold tabular-nums">{result.rateLimitRemaining.rpd}</span></span>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Model Test Dialog ─────────────────────────────────────────────

function ModelTestDialog({
  model,
  provider,
  onClose,
}: {
  model: ProviderModel
  provider: string
  onClose: () => void
}) {
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<ProviderTestResultItem | null>(null)

  const runTest = useCallback(async () => {
    setTesting(true)
    setResult(null)
    try {
      const res = await globalThis.fetch('/api/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, model: model.id }),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        toast.error(`Model test failed: ${errData.error || res.statusText}`)
        return
      }
      const data = await res.json()
      if (data.results && data.results.length > 0) {
        setResult(data.results[0])
        if (data.results[0].success) {
          toast.success(`${model.displayName} test passed — ${data.results[0].latencyMs}ms`)
        } else {
          toast.error(`${model.displayName} test failed — ${data.results[0].error || 'Unknown'}`)
        }
      }
    } catch (err) {
      toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setTesting(false)
    }
  }, [model, provider])

  const tierCfg = TIER_CONFIG[model.tier] || TIER_CONFIG.free

  return (
    <Dialog open={true} onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TestTube2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Test Model: {model.displayName}
          </DialogTitle>
          <DialogDescription>
            {tierCfg.icon} {tierCfg.label} tier • {model.provider} • {formatContextWindow(model.contextWindow)} context
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Model Info */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-accent/30 p-3 text-center">
              <p className="text-[10px] text-muted-foreground uppercase">Health</p>
              <p className={`text-lg font-bold tabular-nums mt-1 ${HEALTH_CONFIG[model.health]?.textColor || ''}`}>
                {model.health === 'healthy' ? '✓' : model.health === 'degraded' ? '⚠' : '✗'}
              </p>
            </div>
            <div className="rounded-lg bg-accent/30 p-3 text-center">
              <p className="text-[10px] text-muted-foreground uppercase">Success</p>
              <p className="text-lg font-bold tabular-nums mt-1">{model.successRate}%</p>
            </div>
            <div className="rounded-lg bg-accent/30 p-3 text-center">
              <p className="text-[10px] text-muted-foreground uppercase">Calls</p>
              <p className="text-lg font-bold tabular-nums mt-1">{model.totalCalls}</p>
            </div>
          </div>

          <Button
            onClick={runTest}
            disabled={testing}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            {testing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Testing {model.displayName}...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 mr-2" />
                Run Model Test
              </>
            )}
          </Button>

          {result && (
            <div className={`rounded-lg border p-3 space-y-2 ${
              result.success ? 'border-emerald-600/20 bg-emerald-600/5' : 'border-red-600/20 bg-red-600/5'
            }`}>
              <div className="flex items-center gap-2">
                {result.success ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                )}
                <span className={`text-sm font-semibold ${result.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                  {result.success ? 'Passed' : 'Failed'} — {formatLatency(result.latencyMs)}
                </span>
              </div>
              {result.response && (
                <pre className="text-xs bg-muted/50 rounded p-2 max-h-24 overflow-y-auto custom-scrollbar font-mono whitespace-pre-wrap">
                  {result.response.slice(0, 200)}
                </pre>
              )}
              {result.error && (
                <p className="text-xs text-red-600 dark:text-red-400">{result.error}</p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Batch Test Dialog ─────────────────────────────────────────────

function BatchTestDialog({
  providers,
  onClose,
  onComplete,
}: {
  providers: ProviderDetail[]
  onClose: () => void
  onComplete: (results: ProviderTestResultItem[]) => void
}) {
  const [selectedProviders, setSelectedProviders] = useState<Set<string>>(() =>
    new Set(providers.map(p => p.provider))
  )
  const [testing, setTesting] = useState(false)
  const [results, setResults] = useState<ProviderTestResultItem[]>([])
  const [currentIndex, setCurrentIndex] = useState(-1)
  const [completed, setCompleted] = useState(false)
  const abortRef = useRef(false)

  const toggleProvider = useCallback((providerId: string) => {
    setSelectedProviders(prev => {
      const next = new Set(prev)
      if (next.has(providerId)) {
        next.delete(providerId)
      } else {
        next.add(providerId)
      }
      return next
    })
  }, [])

  const selectAll = useCallback(() => {
    setSelectedProviders(new Set(providers.map(p => p.provider)))
  }, [providers])

  const selectNone = useCallback(() => {
    setSelectedProviders(new Set())
  }, [])

  const runBatchTest = useCallback(async () => {
    if (selectedProviders.size === 0) {
      toast.error('Select at least one provider to test')
      return
    }

    setTesting(true)
    setResults([])
    setCompleted(false)
    abortRef.current = false

    try {
      const res = await globalThis.fetch('/api/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          testAll: true,
          providers: Array.from(selectedProviders),
        }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        toast.error(`Batch test failed: ${errData.error || res.statusText}`)
        setTesting(false)
        return
      }

      const data = await res.json()
      const testResults: ProviderTestResultItem[] = data.results || []

      // Simulate progressive results for UX
      for (let i = 0; i < testResults.length; i++) {
        if (abortRef.current) break
        setCurrentIndex(i)
        setResults(prev => [...prev, testResults[i]])
        await new Promise(resolve => setTimeout(resolve, 100))
      }

      setCompleted(true)
      setCurrentIndex(testResults.length)
      onComplete(testResults)

      const passed = testResults.filter(r => r.success).length
      toast.success(`Batch test complete: ${passed}/${testResults.length} providers passed`)
    } catch (err) {
      toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setTesting(false)
    }
  }, [selectedProviders, onComplete])

  // Summary stats from results
  const passedCount = results.filter(r => r.success).length
  const failedCount = results.filter(r => !r.success).length
  const avgLatency = results.length > 0
    ? Math.round(results.reduce((sum, r) => sum + r.latencyMs, 0) / results.length)
    : 0
  const totalTokens = results.reduce((sum, r) => sum + r.tokenCount, 0)

  return (
    <Dialog open={true} onOpenChange={() => !testing && onClose()}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Swords className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Batch Multi-Provider Test
          </DialogTitle>
          <DialogDescription>
            Test multiple providers simultaneously and compare results
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Provider selection */}
          {!testing && !completed && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-muted-foreground">
                  Select Providers ({selectedProviders.size}/{providers.length})
                </p>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" className="text-[10px] h-6 px-2" onClick={selectAll}>
                    Select All
                  </Button>
                  <Button variant="ghost" size="sm" className="text-[10px] h-6 px-2" onClick={selectNone}>
                    Select None
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto custom-scrollbar">
                {providers.map(p => {
                  const isSelected = selectedProviders.has(p.provider)
                  const icon = PROVIDER_ICONS[p.provider] || '🖥️'
                  const healthCfg = HEALTH_CONFIG[p.health] || HEALTH_CONFIG.unknown
                  return (
                    <div
                      key={p.provider}
                      className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 cursor-pointer transition-all ${
                        isSelected
                          ? 'border-emerald-600/30 bg-emerald-600/5'
                          : 'border-border/50 bg-muted/20 opacity-60'
                      }`}
                      onClick={() => toggleProvider(p.provider)}
                    >
                      <Checkbox
                        checked={isSelected}
                        onCheckedChange={() => toggleProvider(p.provider)}
                        onClick={e => e.stopPropagation()}
                      />
                      <span className="text-sm">{icon}</span>
                      <span className="text-xs font-medium flex-1 truncate">{p.label}</span>
                      <span
                        className="h-2 w-2 rounded-full shrink-0"
                        style={{ backgroundColor: healthCfg.color }}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Progress indicator */}
          {testing && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-emerald-600 dark:text-emerald-400" />
                <span className="text-sm font-medium">
                  Testing {currentIndex + 1}/{selectedProviders.size} providers...
                </span>
              </div>
              <Progress
                value={selectedProviders.size > 0 ? ((currentIndex + 1) / selectedProviders.size) * 100 : 0}
                className="h-2"
              />
            </div>
          )}

          {/* Aggregate summary */}
          {results.length > 0 && (
            <div className={`rounded-lg border p-3 space-y-2 ${
              completed
                ? failedCount === 0
                  ? 'border-emerald-600/20 bg-emerald-600/5'
                  : 'border-yellow-600/20 bg-yellow-600/5'
                : 'border-border/50 bg-muted/20'
            }`}>
              <div className="flex items-center gap-2">
                {completed ? (
                  failedCount === 0 ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                  )
                ) : (
                  <Loader2 className="h-4 w-4 animate-spin text-emerald-600" />
                )}
                <span className="text-sm font-semibold">
                  {completed ? 'Test Complete' : 'Running...'}
                </span>
              </div>
              <div className="grid grid-cols-4 gap-3">
                <div className="text-center">
                  <p className="text-[9px] text-muted-foreground uppercase">Passed</p>
                  <p className="text-lg font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{passedCount}</p>
                </div>
                <div className="text-center">
                  <p className="text-[9px] text-muted-foreground uppercase">Failed</p>
                  <p className="text-lg font-bold tabular-nums text-red-600 dark:text-red-400">{failedCount}</p>
                </div>
                <div className="text-center">
                  <p className="text-[9px] text-muted-foreground uppercase">Avg Latency</p>
                  <p className="text-lg font-bold tabular-nums">{formatLatency(avgLatency)}</p>
                </div>
                <div className="text-center">
                  <p className="text-[9px] text-muted-foreground uppercase">Total Tokens</p>
                  <p className="text-lg font-bold tabular-nums">{totalTokens}</p>
                </div>
              </div>
            </div>
          )}

          {/* Results comparison table */}
          {results.length > 0 && (
            <div className="rounded-lg border border-border/50">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[10px] h-8">Provider</TableHead>
                    <TableHead className="text-[10px]">Model</TableHead>
                    <TableHead className="text-[10px] text-right">Latency</TableHead>
                    <TableHead className="text-[10px] text-center">Status</TableHead>
                    <TableHead className="text-[10px] text-right">Tokens</TableHead>
                    <TableHead className="text-[10px]">Response Preview</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((r, idx) => (
                    <TableRow key={idx} className={
                      r.success ? 'bg-emerald-600/[0.02]' : 'bg-red-600/[0.02]'
                    }>
                      <TableCell className="text-xs font-medium py-2">
                        <div className="flex items-center gap-1.5">
                          <span>{PROVIDER_ICONS[r.provider] || '🖥️'}</span>
                          <span className="capitalize">{r.provider}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs py-2 max-w-[120px] truncate">
                        {r.model.displayName}
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums py-2 font-medium">
                        {formatLatency(r.latencyMs)}
                      </TableCell>
                      <TableCell className="py-2 text-center">
                        {r.success ? (
                          <Badge className="border-0 text-[8px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
                            <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" /> PASS
                          </Badge>
                        ) : (
                          <Badge className="border-0 text-[8px] bg-red-600/15 text-red-600 dark:text-red-400">
                            <XCircle className="h-2.5 w-2.5 mr-0.5" /> FAIL
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums py-2">
                        {r.tokenCount}
                      </TableCell>
                      <TableCell className="text-xs py-2 max-w-[150px]">
                        {r.response ? (
                          <span className="truncate block text-muted-foreground font-mono">
                            {r.response.slice(0, 50)}
                          </span>
                        ) : r.error ? (
                          <span className="text-red-600 dark:text-red-400 truncate block">
                            {r.error.slice(0, 50)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Action buttons */}
          {!testing && (
            <div className="flex items-center gap-2">
              {!completed ? (
                <Button
                  onClick={runBatchTest}
                  disabled={selectedProviders.size === 0}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  <Swords className="h-4 w-4 mr-2" />
                  Run Batch Test ({selectedProviders.size} providers)
                </Button>
              ) : (
                <Button
                  onClick={() => {
                    setCompleted(false)
                    setResults([])
                    setCurrentIndex(-1)
                  }}
                  variant="outline"
                  className="flex-1"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Re-run Test
                </Button>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={testing}
          >
            {completed ? 'Close' : 'Cancel'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Quota Gauge Component ─────────────────────────────────────────

function QuotaGauge({ label, used, limit, color }: { label: string; used: number; limit: number; color: string }) {
  const percent = limit > 0 ? Math.min(100, (used / limit) * 100) : 0
  const remaining = Math.max(0, limit - used)
  const isCritical = percent > 80
  const isWarning = percent > 50

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-muted-foreground">{label}</span>
        <span className={`text-[10px] font-bold tabular-nums ${
          isCritical ? 'text-red-600 dark:text-red-400' :
          isWarning ? 'text-yellow-600 dark:text-yellow-400' :
          'text-emerald-600 dark:text-emerald-400'
        }`}>{remaining}/{limit}</span>
      </div>
      <div className="relative h-2.5 rounded-full bg-muted/30 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${percent}%`,
            backgroundColor: isCritical ? '#f87171' : isWarning ? '#facc15' : color,
            opacity: 0.8,
          }}
        />
      </div>
      <p className="text-[9px] text-muted-foreground tabular-nums">{percent.toFixed(0)}% used</p>
    </div>
  )
}

// ── Main ProviderTab ──────────────────────────────────────────────

export function ProviderTab() {
  const { data: providersData, loading: providersLoading, refetch: refetchProviders } = useApiData<ProvidersListResponse>('/api/providers', 15000)
  const { data: quotasData, refetch: refetchQuotas } = useApiData<QuotasResponse>('/api/providers/quotas', 15000)

  const [testingProvider, setTestingProvider] = useState<ProviderDetail | null>(null)
  const [testingModel, setTestingModel] = useState<{ model: ProviderModel; provider: string } | null>(null)
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set())
  const [activeSection, setActiveSection] = useState('grid')
  const [showBatchTest, setShowBatchTest] = useState(false)
  const [arenaResults, setArenaResults] = useState<ProviderTestResultItem[]>([])
  const [keyEntryProvider, setKeyEntryProvider] = useState<ProviderDetail | null>(null)

  const toggleProviderExpand = useCallback((providerId: string) => {
    setExpandedProviders(prev => {
      const next = new Set(prev)
      if (next.has(providerId)) {
        next.delete(providerId)
      } else {
        next.add(providerId)
      }
      return next
    })
  }, [])

  // Compute stats from API data
  const stats = useMemo(() => {
    if (!providersData) {
      return {
        totalProviders: 0,
        availableModels: 0,
        healthyProviders: 0,
        avgLatency: 0,
      }
    }
    const totalProviders = providersData.summary.totalProviders
    const availableModels = providersData.summary.totalModels
    const healthyProviders = providersData.providers.filter(p => p.health === 'healthy' && p.keyStatus.hasAvailableKey).length
    const testedProviders = providersData.providers.filter(p => p.avgLatencyMs > 0)
    const avgLatency = testedProviders.length > 0
      ? Math.round(testedProviders.reduce((sum, p) => sum + p.avgLatencyMs, 0) / testedProviders.length)
      : 0

    return { totalProviders, availableModels, healthyProviders, avgLatency }
  }, [providersData])

  // All models flattened for the table
  const allModels = useMemo(() => {
    if (!providersData) return []
    const models: Array<ProviderModel & { provider: string; providerLabel: string }> = []
    for (const p of providersData.providers) {
      for (const m of p.models) {
        models.push({ ...m, provider: p.provider, providerLabel: p.label })
      }
    }
    return models
  }, [providersData])

  // Latency chart data from providers
  const latencyChartData = useMemo(() => {
    if (!providersData) return []
    return providersData.providers
      .filter(p => p.avgLatencyMs > 0)
      .map(p => ({
        name: p.label.split(' ')[0].substring(0, 10),
        latency: p.avgLatencyMs,
      }))
      .sort((a, b) => a.latency - b.latency)
  }, [providersData])

  const handleRefresh = useCallback(() => {
    refetchProviders()
    refetchQuotas()
    toast.success('Provider data refreshed')
  }, [refetchProviders, refetchQuotas])

  // Loading skeleton
  if (providersLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-28 rounded-xl bg-muted/30 animate-pulse" />
          ))}
        </div>
        <div className="h-64 rounded-xl bg-muted/30 animate-pulse" />
        <div className="h-48 rounded-xl bg-muted/30 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-6 grid-pattern">
      {/* ── Top Stats Row ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Providers */}
        <Card className="relative overflow-hidden hover-lift shadow-lg border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-emerald-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Total Providers</p>
                <p className="text-2xl font-bold tabular-nums mt-1">{stats.totalProviders}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">With API keys configured</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600/15">
                <Server className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Available Models */}
        <Card className="relative overflow-hidden hover-lift shadow-lg border-blue-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-blue-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Available Models</p>
                <p className="text-2xl font-bold tabular-nums mt-1">{stats.availableModels}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">Total model routes</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/15">
                <Cpu className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Healthy Providers */}
        <Card className="relative overflow-hidden hover-lift shadow-lg border-orange-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 via-orange-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Healthy Providers</p>
                <p className="text-2xl font-bold tabular-nums mt-1">{stats.healthyProviders}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">With healthy API keys</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-600/15">
                <ShieldCheck className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Avg Latency */}
        <Card className="relative overflow-hidden hover-lift shadow-lg border-purple-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 via-purple-600/3 to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Avg Latency</p>
                <p className="text-2xl font-bold tabular-nums mt-1">{formatLatency(stats.avgLatency)}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">Across tested providers</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-600/15">
                <Gauge className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Section Tabs ──────────────────────────────────────── */}
      <Tabs value={activeSection} onValueChange={setActiveSection}>
        <div className="flex items-center justify-between">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="grid" className="text-xs gap-1.5">
              <Server className="h-3.5 w-3.5" />
              Provider Status
            </TabsTrigger>
            <TabsTrigger value="models" className="text-xs gap-1.5">
              <Cpu className="h-3.5 w-3.5" />
              Model Registry
            </TabsTrigger>
            <TabsTrigger value="quotas" className="text-xs gap-1.5">
              <Gauge className="h-3.5 w-3.5" />
              Quota Dashboard
            </TabsTrigger>
            <TabsTrigger value="keys" className="text-xs gap-1.5">
              <Key className="h-3.5 w-3.5" />
              Key Vault
            </TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs gap-1.5 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
              onClick={() => setShowBatchTest(true)}
            >
              <Swords className="h-3.5 w-3.5" />
              Batch Test All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs gap-1.5 text-muted-foreground hover:text-foreground"
              onClick={handleRefresh}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </Button>
          </div>
        </div>

        {/* ── Provider Status Grid ──────────────────────────────── */}
        <TabsContent value="grid" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">Provider Status Grid</h2>
              <DataSourceBadge source="api" />
            </div>
            <Badge variant="outline" className="text-[10px]">
              {providersData?.providers.length ?? 0} providers
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {(providersData?.providers ?? []).map((provider) => {
              const healthCfg = HEALTH_CONFIG[provider.health] || HEALTH_CONFIG.unknown
              const isExpanded = expandedProviders.has(provider.provider)
              const providerIcon = PROVIDER_ICONS[provider.provider] || '🖥️'

              return (
                <Card
                  key={provider.provider}
                  className={`relative overflow-hidden hover-lift shadow-md transition-all duration-300 ${
                    provider.health === 'healthy' ? 'border-emerald-600/15' :
                    provider.health === 'degraded' ? 'border-yellow-600/15' :
                    'border-red-600/15'
                  }`}
                >
                  {/* Health gradient overlay */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${
                    provider.health === 'healthy' ? 'from-emerald-600/5' :
                    provider.health === 'degraded' ? 'from-yellow-600/5' :
                    'from-red-600/5'
                  } via-transparent to-transparent`} />

                  <CardHeader className="relative pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <span className="text-base">{providerIcon}</span>
                        {provider.label}
                        {/* Health indicator dot */}
                        <span className="relative flex h-2.5 w-2.5">
                          {provider.health === 'healthy' && (
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                          )}
                          <span
                            className="relative inline-flex h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: healthCfg.color }}
                          />
                        </span>
                      </CardTitle>
                      <Badge className={`border-0 text-[9px] px-1.5 ${healthCfg.bgColor} ${healthCfg.textColor}`}>
                        {healthCfg.label}
                      </Badge>
                    </div>
                  </CardHeader>

                  <CardContent className="relative p-4 pt-0 space-y-3">
                    {/* Key metrics row */}
                    <div className="grid grid-cols-3 gap-2">
                      <div className="rounded-md bg-accent/30 p-2 text-center">
                        <p className="text-[9px] text-muted-foreground uppercase">Models</p>
                        <p className="text-sm font-bold tabular-nums">{provider.activeModels}/{provider.totalModels}</p>
                      </div>
                      <div className="rounded-md bg-accent/30 p-2 text-center">
                        <p className="text-[9px] text-muted-foreground uppercase">RPM Left</p>
                        <p className="text-sm font-bold tabular-nums">{provider.rateLimits.remaining.rpm}</p>
                      </div>
                      <div className="rounded-md bg-accent/30 p-2 text-center">
                        <p className="text-[9px] text-muted-foreground uppercase">Latency</p>
                        <p className="text-sm font-bold tabular-nums">{formatLatency(provider.avgLatencyMs)}</p>
                      </div>
                    </div>

                    {/* Rate limit bar */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-muted-foreground">Rate Limit (RPM)</span>
                        <span className="font-medium tabular-nums">{provider.rateLimits.remaining.rpm}/{provider.rateLimits.rpm}</span>
                      </div>
                      <Progress
                        value={provider.rateLimits.rpm > 0 ? (provider.rateLimits.remaining.rpm / provider.rateLimits.rpm) * 100 : 0}
                        className="h-1.5"
                      />
                    </div>

                    {/* Cooldown indicator */}
                    {provider.rateLimits.isCooldown && (
                      <div className="flex items-center gap-2 rounded-md bg-red-600/10 border border-red-600/20 px-2.5 py-1.5 text-xs text-red-600 dark:text-red-400">
                        <Timer className="h-3 w-3 animate-pulse" />
                        <span>Cooldown active — {Math.ceil(provider.rateLimits.cooldownRemainingMs / 1000)}s remaining</span>
                      </div>
                    )}

                    {/* Key status — clickable to open key entry */}
                    <div
                      className="flex items-center gap-2 text-[10px] rounded-md bg-accent/20 px-2 py-1.5 cursor-pointer hover:bg-accent/40 transition-colors"
                      onClick={() => setKeyEntryProvider(provider)}
                      title="Click to manage API key"
                    >
                      <Key className="h-3 w-3 text-muted-foreground" />
                      <span className="flex-1">
                        {provider.keyStatus.hasAvailableKey ? (
                          <span className="flex items-center gap-1.5">
                            <Badge className="border-0 text-[8px] px-1 py-0 bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
                              <Lock className="h-2 w-2 mr-0.5" />
                              KEY ACTIVE
                            </Badge>
                            {provider.keyStatus.activeKeyMasked && (
                              <span className="font-mono text-muted-foreground">{provider.keyStatus.activeKeyMasked}</span>
                            )}
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5">
                            <Badge className="border-0 text-[8px] px-1 py-0 bg-red-600/15 text-red-600 dark:text-red-400">
                              NO KEY
                            </Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-4 text-[9px] px-1 py-0 gap-0.5 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
                              onClick={(e) => {
                                e.stopPropagation()
                                setKeyEntryProvider(provider)
                              }}
                            >
                              <Plus className="h-2.5 w-2.5" />
                              Add Key
                            </Button>
                          </span>
                        )}
                      </span>
                      <span className="text-muted-foreground shrink-0">
                        {provider.keyStatus.healthyKeys}/{provider.keyStatus.totalKeys} healthy
                      </span>
                    </div>

                    {/* Expanded model list */}
                    {isExpanded && provider.models.length > 0 && (
                      <div className="space-y-1.5 pt-2 border-t border-border/50">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Models</p>
                        {provider.models.map(m => {
                          const mHealth = HEALTH_CONFIG[m.health] || HEALTH_CONFIG.unknown
                          const mTier = TIER_CONFIG[m.tier] || TIER_CONFIG.free
                          return (
                            <div
                              key={m.id}
                              className="flex items-center gap-2 rounded-md bg-accent/20 px-2.5 py-1.5 text-xs"
                            >
                              <span
                                className="h-2 w-2 rounded-full shrink-0"
                                style={{ backgroundColor: mHealth.color }}
                              />
                              <span className="truncate flex-1 font-medium">{m.displayName}</span>
                              <Badge className={`border-0 text-[8px] px-1 py-0 ${mTier.bgColor} ${mTier.textColor}`}>
                                {mTier.icon} {mTier.label}
                              </Badge>
                              <span className="text-[10px] text-muted-foreground tabular-nums shrink-0">{formatLatency(m.latencyMs)}</span>
                            </div>
                          )
                        })}
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="flex items-center gap-2 pt-1">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1 text-[11px] h-7 gap-1"
                        onClick={() => setTestingProvider(provider)}
                      >
                        <TestTube2 className="h-3 w-3" />
                        Test
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="flex-1 text-[11px] h-7 gap-1"
                        onClick={() => toggleProviderExpand(provider.provider)}
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="h-3 w-3" />
                            Collapse
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-3 w-3" />
                            Details
                          </>
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Latency Chart */}
          {latencyChartData.length > 0 && (
            <Card className="relative overflow-hidden border-emerald-600/15">
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
              <CardHeader className="relative pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  Provider Latency Comparison
                  <DataSourceBadge source="api" />
                </CardTitle>
              </CardHeader>
              <CardContent className="relative p-4 pt-0">
                <div className="h-[160px]">
                  <NexusBarChart
                    data={latencyChartData}
                    dataKey="latency"
                    nameKey="name"
                    color={COLORS.emerald}
                    height={160}
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* ── Provider Arena ──────────────────────────────────── */}
          <Card className="relative overflow-hidden border-emerald-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  Provider Arena
                </CardTitle>
                {arenaResults.length > 0 && (
                  <Badge className="border-0 text-[9px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
                    {arenaResults.filter(r => r.success).length}/{arenaResults.length} passed
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              {arenaResults.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <Swords className="h-8 w-8 text-muted-foreground/30 mb-3" />
                  <p className="text-sm text-muted-foreground font-medium">Not yet tested</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">
                    Run a batch test to see provider latency comparison
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3 text-xs gap-1.5 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
                    onClick={() => setShowBatchTest(true)}
                  >
                    <Swords className="h-3.5 w-3.5" />
                    Run Batch Test
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Arena latency bar chart */}
                  <div className="h-[200px]">
                    <NexusBarChart
                      data={arenaResults
                        .filter(r => r.success)
                        .sort((a, b) => a.latencyMs - b.latencyMs)
                        .map(r => ({
                          name: r.provider.charAt(0).toUpperCase() + r.provider.slice(1).substring(0, 8),
                          latency: r.latencyMs,
                        }))
                      }
                      dataKey="latency"
                      nameKey="name"
                      color={COLORS.emerald}
                      height={200}
                    />
                  </div>

                  {/* Arena leaderboard */}
                  <div className="space-y-1.5">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Leaderboard</p>
                    {arenaResults
                      .sort((a, b) => {
                        // Sort by success first, then latency
                        if (a.success !== b.success) return a.success ? -1 : 1
                        return a.latencyMs - b.latencyMs
                      })
                      .map((r, idx) => (
                        <div
                          key={r.provider}
                          className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-xs ${
                            r.success
                              ? idx === 0
                                ? 'bg-emerald-600/10 border border-emerald-600/20'
                                : 'bg-accent/30'
                              : 'bg-red-600/5 border border-red-600/10'
                          }`}
                        >
                          <span className="w-5 text-center font-bold tabular-nums text-muted-foreground">
                            {idx === 0 && r.success ? '🏆' : `#${idx + 1}`}
                          </span>
                          <span className="text-sm">{PROVIDER_ICONS[r.provider] || '🖥️'}</span>
                          <span className="font-medium flex-1 capitalize">{r.provider}</span>
                          <span className="text-[10px] text-muted-foreground truncate max-w-[100px]">
                            {r.model.displayName}
                          </span>
                          {r.success ? (
                            <>
                              <Badge className="border-0 text-[8px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
                                {formatLatency(r.latencyMs)}
                              </Badge>
                              <Badge className="border-0 text-[8px] bg-blue-600/15 text-blue-600 dark:text-blue-400">
                                {r.tokenCount} tok
                              </Badge>
                            </>
                          ) : (
                            <Badge className="border-0 text-[8px] bg-red-600/15 text-red-600 dark:text-red-400">
                              <XCircle className="h-2.5 w-2.5 mr-0.5" /> FAIL
                            </Badge>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Model Registry Table ──────────────────────────────── */}
        <TabsContent value="models" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">Model Registry</h2>
              <DataSourceBadge source="api" />
            </div>
            <Badge variant="outline" className="text-[10px]">
              {allModels.length} models
            </Badge>
          </div>

          <Card className="relative overflow-hidden border-emerald-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/2 via-transparent to-transparent" />
            <CardContent className="relative p-0">
              <div className="max-h-[520px] overflow-y-auto custom-scrollbar">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-[10px] uppercase tracking-wider">Model</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider">Provider</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider">Tier</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider">Context</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider">Health</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider">Success</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider">Latency</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider">Capabilities</TableHead>
                      <TableHead className="text-[10px] uppercase tracking-wider w-20">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {allModels.map((model) => {
                      const mHealth = HEALTH_CONFIG[model.health] || HEALTH_CONFIG.unknown
                      const mTier = TIER_CONFIG[model.tier] || TIER_CONFIG.free
                      return (
                        <TableRow key={model.id} className="hover:bg-accent/30">
                          <TableCell>
                            <div className="flex flex-col">
                              <span className="text-xs font-medium truncate max-w-[180px]">{model.displayName}</span>
                              <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[180px]">{model.actualModel}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <span className="text-xs">{model.providerLabel}</span>
                          </TableCell>
                          <TableCell>
                            <Badge className={`border-0 text-[9px] px-1.5 py-0 ${mTier.bgColor} ${mTier.textColor}`}>
                              {mTier.icon} {mTier.label}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <span className="text-xs tabular-nums">{formatContextWindow(model.contextWindow)}</span>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <span
                                className="h-2 w-2 rounded-full"
                                style={{ backgroundColor: mHealth.color }}
                              />
                              <span className={`text-[10px] font-medium ${mHealth.textColor}`}>
                                {mHealth.label}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <Progress
                                value={model.successRate}
                                className="h-1.5 w-12"
                              />
                              <span className="text-[10px] tabular-nums font-medium">{model.successRate}%</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <span className="text-xs tabular-nums">{formatLatency(model.latencyMs)}</span>
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {model.capabilities.slice(0, 3).map(cap => (
                                <Badge key={cap} variant="outline" className="text-[8px] px-1 py-0 h-4">
                                  {cap}
                                </Badge>
                              ))}
                              {model.capabilities.length > 3 && (
                                <Badge variant="outline" className="text-[8px] px-1 py-0 h-4">
                                  +{model.capabilities.length - 3}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 text-[10px] gap-1 text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300"
                              onClick={() => setTestingModel({ model, provider: model.provider })}
                            >
                              <Zap className="h-3 w-3" />
                              Test
                            </Button>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Quota Dashboard ────────────────────────────────────── */}
        <TabsContent value="quotas" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">Quota Dashboard</h2>
              <DataSourceBadge source="api" />
            </div>
            <div className="flex items-center gap-2">
              {quotasData?.summary.overallHealth && (
                <Badge className={`border-0 text-[9px] px-2 ${
                  quotasData.summary.overallHealth === 'healthy' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
                  quotasData.summary.overallHealth === 'degraded' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
                  'bg-red-600/15 text-red-600 dark:text-red-400'
                }`}>
                  {quotasData.summary.overallHealth.toUpperCase()}
                </Badge>
              )}
            </div>
          </div>

          {/* Summary Stats */}
          {quotasData && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-lg bg-accent/30 p-3 text-center">
                <Globe className="h-4 w-4 text-blue-600 dark:text-blue-400 mx-auto mb-1" />
                <p className="text-lg font-bold tabular-nums">{quotasData.summary.totalProviders}</p>
                <p className="text-[9px] text-muted-foreground">Total Providers</p>
              </div>
              <div className="rounded-lg bg-accent/30 p-3 text-center">
                <Timer className="h-4 w-4 text-red-600 dark:text-red-400 mx-auto mb-1" />
                <p className="text-lg font-bold tabular-nums">{quotasData.summary.providersInCooldown}</p>
                <p className="text-[9px] text-muted-foreground">In Cooldown</p>
              </div>
              <div className="rounded-lg bg-accent/30 p-3 text-center">
                <Hash className="h-4 w-4 text-orange-600 dark:text-orange-400 mx-auto mb-1" />
                <p className="text-lg font-bold tabular-nums">{quotasData.summary.totalRequestsToday}</p>
                <p className="text-[9px] text-muted-foreground">Requests Today</p>
              </div>
              <div className="rounded-lg bg-accent/30 p-3 text-center">
                <Key className="h-4 w-4 text-emerald-600 dark:text-emerald-400 mx-auto mb-1" />
                <p className="text-lg font-bold tabular-nums">{quotasData.summary.totalKeysAvailable}</p>
                <p className="text-[9px] text-muted-foreground">Keys Available</p>
              </div>
            </div>
          )}

          {/* Per-provider quota cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {(quotasData?.providers ?? []).map((quota) => {
              const providerIcon = PROVIDER_ICONS[quota.provider] || '🖥️'
              const isCooldown = quota.cooldown.isActive
              const isCriticalRpm = quota.rateLimits.rpm.percentUsed > 80
              const isCriticalRpd = quota.rateLimits.rpd.percentUsed > 80

              return (
                <Card
                  key={quota.provider}
                  className={`relative overflow-hidden hover-lift shadow-md ${
                    isCooldown ? 'border-red-600/20' :
                    isCriticalRpm || isCriticalRpd ? 'border-yellow-600/15' :
                    'border-emerald-600/10'
                  }`}
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${
                    isCooldown ? 'from-red-600/5' :
                    isCriticalRpm ? 'from-yellow-600/5' :
                    'from-emerald-600/3'
                  } via-transparent to-transparent`} />

                  <CardHeader className="relative pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <span className="text-base">{providerIcon}</span>
                        {quota.provider}
                      </CardTitle>
                      {isCooldown && (
                        <Badge className="border-0 text-[9px] px-1.5 bg-red-600/15 text-red-600 dark:text-red-400 animate-pulse">
                          COOLDOWN
                        </Badge>
                      )}
                    </div>
                    <p className="text-[10px] text-muted-foreground">{quota.description}</p>
                  </CardHeader>

                  <CardContent className="relative p-4 pt-0 space-y-3">
                    {/* Rate limit gauges */}
                    <QuotaGauge
                      label="Requests Per Minute"
                      used={quota.rateLimits.rpm.used}
                      limit={quota.rateLimits.rpm.limit}
                      color={COLORS.emerald}
                    />
                    <QuotaGauge
                      label="Requests Per Day"
                      used={quota.rateLimits.rpd.used}
                      limit={quota.rateLimits.rpd.limit}
                      color={COLORS.blue}
                    />

                    {/* Cooldown timer */}
                    {isCooldown && (
                      <div className="flex items-center gap-2 rounded-md bg-red-600/10 border border-red-600/20 px-2.5 py-2 text-xs text-red-600 dark:text-red-400">
                        <Timer className="h-3.5 w-3.5 animate-pulse" />
                        <div>
                          <p className="font-medium">Cooldown active</p>
                          {quota.cooldown.remainingMs > 0 && (
                            <p className="text-[10px]">{Math.ceil(quota.cooldown.remainingMs / 1000)}s remaining</p>
                          )}
                          {quota.cooldown.reason && (
                            <p className="text-[10px] opacity-80">{quota.cooldown.reason}</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Request stats */}
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="rounded-md bg-accent/30 p-1.5">
                        <p className="text-[9px] text-muted-foreground uppercase">Total</p>
                        <p className="text-xs font-bold tabular-nums">{quota.requestStats.totalRequests}</p>
                      </div>
                      <div className="rounded-md bg-accent/30 p-1.5">
                        <p className="text-[9px] text-muted-foreground uppercase">Rejected</p>
                        <p className="text-xs font-bold tabular-nums text-red-600 dark:text-red-400">{quota.requestStats.totalRejected}</p>
                      </div>
                      <div className="rounded-md bg-accent/30 p-1.5">
                        <p className="text-[9px] text-muted-foreground uppercase">429s</p>
                        <p className="text-xs font-bold tabular-nums text-yellow-600 dark:text-yellow-400">{quota.requestStats.consecutive429s}</p>
                      </div>
                    </div>

                    {/* Key health */}
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <Key className="h-3 w-3" />
                        Key Health
                      </span>
                      <span className={quota.keyHealth.hasAvailableKey ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-red-600 dark:text-red-400 font-medium'}>
                        {quota.keyHealth.hasAvailableKey
                          ? `${quota.keyHealth.healthyKeys}/${quota.keyHealth.totalKeys} healthy`
                          : 'No key available'}
                      </span>
                    </div>

                    {/* Cache stats */}
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <Sparkles className="h-3 w-3" />
                        Cache Hit Rate
                      </span>
                      <span className="font-medium tabular-nums">
                        {quota.cache.hitRate > 0 ? `${(quota.cache.hitRate * 100).toFixed(1)}%` : 'N/A'}
                      </span>
                    </div>

                    {/* Queue stats */}
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <Activity className="h-3 w-3" />
                        Queue
                      </span>
                      <span className="font-medium tabular-nums">
                        {quota.queue.pending} pending · {quota.queue.processing} processing
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Free Tier Notes */}
          <Card className="relative overflow-hidden border-emerald-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Info className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Free Tier Quota Notes
              </CardTitle>
            </CardHeader>
            <CardContent className="relative p-4 pt-0">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="flex items-start gap-3 rounded-lg bg-accent/30 p-3">
                  <Flame className="h-5 w-5 text-orange-600 dark:text-orange-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium">Fireworks AI</p>
                    <p className="text-[10px] text-muted-foreground">$6 credits on free tier. Use sparingly for production workloads. Ideal for StressLab and quick tests.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg bg-accent/30 p-3">
                  <Globe className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium">Alibaba Cloud (Qwen)</p>
                    <p className="text-[10px] text-muted-foreground">100+ models available, 1M free tokens each. Excellent for research and development. Best free-tier value.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg bg-accent/30 p-3">
                  <Zap className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium">NVIDIA NIM Free</p>
                    <p className="text-[10px] text-muted-foreground">40 RPM on free tier. Models like Gemma-3-27B and Llama available at no cost with rate limits.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg bg-accent/30 p-3">
                  <CircleDot className="h-5 w-5 text-purple-600 dark:text-purple-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium">OpenRouter Free</p>
                    <p className="text-[10px] text-muted-foreground">Access to DeepSeek, Llama, and other models for free. Rate limited to 20 RPM. Some models may have slower responses.</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Key Vault Tab ────────────────────────────────────── */}
        <TabsContent value="keys" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">Key Vault</h2>
              <DataSourceBadge source="api" />
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-[10px]">
                {providersData?.providers.filter(p => p.keyStatus.hasAvailableKey).length ?? 0}/{providersData?.providers.length ?? 0} configured
              </Badge>
            </div>
          </div>

          {/* Key overview cards for all providers */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {(providersData?.providers ?? []).map((provider) => {
              const providerIcon = PROVIDER_ICONS[provider.provider] || '🖥️'
              const hasKey = provider.keyStatus.hasAvailableKey

              return (
                <Card
                  key={provider.provider}
                  className={`relative overflow-hidden hover-lift shadow-md transition-all duration-300 ${
                    hasKey ? 'border-emerald-600/15' : 'border-red-600/15'
                  }`}
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${
                    hasKey ? 'from-emerald-600/5' : 'from-red-600/5'
                  } via-transparent to-transparent`} />

                  <div className="relative p-4 space-y-3">
                    {/* Provider header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{providerIcon}</span>
                        <div>
                          <p className="text-sm font-semibold">{provider.label}</p>
                          <p className="text-[10px] text-muted-foreground font-mono">{provider.provider}</p>
                        </div>
                      </div>
                      {hasKey ? (
                        <Badge className="border-0 text-[9px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
                          <Lock className="h-2.5 w-2.5 mr-0.5" />
                          ACTIVE
                        </Badge>
                      ) : (
                        <Badge className="border-0 text-[9px] bg-red-600/15 text-red-600 dark:text-red-400">
                          NO KEY
                        </Badge>
                      )}
                    </div>

                    {/* Key info */}
                    <div className="rounded-md bg-accent/30 p-2.5 space-y-1.5">
                      {hasKey && provider.keyStatus.activeKeyMasked ? (
                        <div className="flex items-center gap-2">
                          <Lock className="h-3 w-3 text-emerald-600/60 dark:text-emerald-400/60" />
                          <span className="text-xs font-mono">{provider.keyStatus.activeKeyMasked}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Key className="h-3 w-3 text-red-600/60 dark:text-red-400/60" />
                          <span className="text-xs text-muted-foreground">No API key configured</span>
                        </div>
                      )}
                      <div className="flex items-center justify-between text-[9px] text-muted-foreground">
                        <span>Keys: {provider.keyStatus.totalKeys}</span>
                        <span>Healthy: {provider.keyStatus.healthyKeys}/{provider.keyStatus.totalKeys}</span>
                      </div>
                    </div>

                    {/* Action button */}
                    <Button
                      className={`w-full text-[11px] h-7 gap-1.5 ${
                        hasKey
                          ? 'bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/20 border border-emerald-600/20'
                          : 'bg-red-600/10 text-red-600 dark:text-red-400 hover:bg-red-600/20 border border-red-600/20'
                      }`}
                      variant="outline"
                      onClick={() => setKeyEntryProvider(provider)}
                    >
                      {hasKey ? (
                        <>
                          <Shield className="h-3 w-3" />
                          Manage Key
                        </>
                      ) : (
                        <>
                          <Plus className="h-3 w-3" />
                          Add API Key
                        </>
                      )}
                    </Button>
                  </div>
                </Card>
              )
            })}
          </div>

          {/* Encryption info */}
          <Card className="relative overflow-hidden border-emerald-600/15">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <div className="flex items-start gap-3">
                <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-2">
                  <p className="text-xs font-medium">Key Encryption & Security</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    <div className="rounded-md bg-accent/30 p-2.5">
                      <p className="text-[9px] text-muted-foreground uppercase">Algorithm</p>
                      <p className="text-xs font-medium mt-0.5">AES-256-GCM</p>
                    </div>
                    <div className="rounded-md bg-accent/30 p-2.5">
                      <p className="text-[9px] text-muted-foreground uppercase">Key Derivation</p>
                      <p className="text-xs font-medium mt-0.5">256-bit env-based</p>
                    </div>
                    <div className="rounded-md bg-accent/30 p-2.5">
                      <p className="text-[9px] text-muted-foreground uppercase">Client Exposure</p>
                      <p className="text-xs font-medium mt-0.5">Masked only (sk-...XXXX)</p>
                    </div>
                  </div>
                  <p className="text-[10px] text-muted-foreground">
                    API keys are encrypted before storage using AES-256-GCM with a 96-bit IV and 128-bit authentication tag.
                    The plaintext key is never sent to the client — only a masked version showing the first 8 and last 4 characters.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ── Provider Test Dialog ────────────────────────────────── */}
      {testingProvider && (
        <ProviderTestPanel
          provider={testingProvider}
          onClose={() => setTestingProvider(null)}
        />
      )}

      {/* ── Model Test Dialog ───────────────────────────────────── */}
      {testingModel && (
        <ModelTestDialog
          model={testingModel.model}
          provider={testingModel.provider}
          onClose={() => setTestingModel(null)}
        />
      )}

      {/* ── API Key Entry Dialog ───────────────────────────────── */}
      {keyEntryProvider && (
        <ApiKeyEntry
          provider={keyEntryProvider.provider}
          providerLabel={keyEntryProvider.label}
          providerIcon={PROVIDER_ICONS[keyEntryProvider.provider] || '🖥️'}
          hasAvailableKey={keyEntryProvider.keyStatus.hasAvailableKey}
          activeKeyMasked={keyEntryProvider.keyStatus.activeKeyMasked}
          healthyKeys={keyEntryProvider.keyStatus.healthyKeys}
          totalKeys={keyEntryProvider.keyStatus.totalKeys}
          open={!!keyEntryProvider}
          onClose={() => setKeyEntryProvider(null)}
          onKeySaved={() => {
            refetchProviders()
            refetchQuotas()
          }}
        />
      )}
    </div>
  )
}
