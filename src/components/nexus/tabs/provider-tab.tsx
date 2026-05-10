'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import {
  Server,
  Key,
  Gauge,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Zap,
  Eye,
  Code,
  Wrench,
  FileCode,
  Binary,
  CircleDot,
  Loader2,
  DollarSign,
  TestTube,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ProviderModel {
  id: string
  tier: string
  displayName: string
  health: string
  capabilities: string[]
}

interface ProviderData {
  provider: string
  label: string
  isAvailable: boolean
  activeModels: number
  totalModels: number
  health: 'healthy' | 'degraded' | 'down' | 'unknown'
  rateLimitRemaining: number
  avgLatencyMs: number
  models: ProviderModel[]
  keyStatus: {
    totalKeys: number
    healthyKeys: number
    hasAvailableKey: boolean
    activeKeyMasked: string | null
  }
  rateLimits: {
    rpm: number
    rpd: number
    remaining: { rpm: number; rpd: number }
    isCooldown: boolean
    cooldownRemainingMs: number
    description: string
  }
  costEstimate: {
    inputPer1k: number
    outputPer1k: number
    currency: string
    note: string
  }
  capabilities: {
    chat: boolean
    vision: boolean
    embedding: boolean
    code: boolean
    tools: boolean
    completion: boolean
  }
}

interface ProvidersResponse {
  providers: ProviderData[]
  summary: {
    totalProviders: number
    availableProviders: number
    totalModels: number
    healthyModels: number
  }
}

const keyStatusConfig = {
  valid: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', label: 'Configured' },
  expiring: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', label: 'Expiring Soon' },
  missing: { icon: XCircle, color: 'text-red-600 dark:text-red-400', label: 'Not Configured' },
  invalid: { icon: XCircle, color: 'text-red-600 dark:text-red-400', label: 'Invalid' },
}

function getKeyStatus(provider: ProviderData) {
  if (provider.keyStatus.hasAvailableKey && provider.keyStatus.healthyKeys > 0) return 'valid'
  if (provider.keyStatus.totalKeys > 0 && !provider.keyStatus.hasAvailableKey) return 'expiring'
  return 'missing'
}

const capabilityIcons: Record<string, { icon: React.ElementType; label: string; color: string }> = {
  chat: { icon: CircleDot, label: 'Chat', color: 'text-emerald-600 dark:text-emerald-400' },
  vision: { icon: Eye, label: 'Vision', color: 'text-blue-600 dark:text-blue-400' },
  embedding: { icon: Binary, label: 'Embedding', color: 'text-purple-600 dark:text-purple-400' },
  code: { icon: Code, label: 'Code', color: 'text-amber-600 dark:text-amber-400' },
  tools: { icon: Wrench, label: 'Tools', color: 'text-cyan-600 dark:text-cyan-400' },
  completion: { icon: FileCode, label: 'Completion', color: 'text-rose-600 dark:text-rose-400' },
}

export function ProviderTab() {
  const [data, setData] = useState<ProvidersResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; latencyMs: number; error?: string }>>({})

  const fetchProviders = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/ai/providers')
      if (!response.ok) {
        throw new Error(`Failed to fetch providers: ${response.status}`)
      }
      const json = await response.json()
      setData(json)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load providers')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProviders()
  }, [fetchProviders])

  const testConnection = useCallback(async (provider: string) => {
    setTestingProvider(provider)
    try {
      const response = await fetch('/api/ai/providers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      })
      const result = await response.json()
      setTestResults(prev => ({
        ...prev,
        [provider]: {
          success: result.isAvailable ?? false,
          latencyMs: result.latencyMs ?? -1,
          error: result.error,
        },
      }))
      // Refresh provider data after test
      fetchProviders()
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [provider]: {
          success: false,
          latencyMs: -1,
          error: err instanceof Error ? err.message : 'Test failed',
        },
      }))
    } finally {
      setTestingProvider(null)
    }
  }, [fetchProviders])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-lg font-semibold">Provider Management</h2>
          </div>
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Card key={i} className="bg-card/50 border-border/50">
              <CardContent className="p-4"><Skeleton className="h-12 w-full" /></CardContent>
            </Card>
          ))}
        </div>
        {[1, 2, 3].map(i => (
          <Card key={i} className="bg-card/50 border-border/50">
            <CardContent className="p-4"><Skeleton className="h-32 w-full" /></CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-lg font-semibold">Provider Management</h2>
          </div>
        </div>
        <Card className="bg-red-500/5 border-red-500/20">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-2" />
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            <Button size="sm" variant="outline" className="mt-3 gap-1.5" onClick={fetchProviders}>
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const providers = data?.providers || []
  const summary = data?.summary || { totalProviders: 0, availableProviders: 0, totalModels: 0, healthyModels: 0 }
  const activeCount = providers.filter(p => p.isAvailable).length
  const warningCount = providers.filter(p => p.health === 'degraded').length
  const inactiveCount = providers.filter(p => !p.isAvailable && p.health !== 'degraded').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold">Provider Management</h2>
          {data && (
            <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
              Live
            </Badge>
          )}
        </div>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={fetchProviders} disabled={loading}>
          <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
          Refresh All
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{activeCount}</div>
            <div className="text-xs text-muted-foreground">Active</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{warningCount}</div>
            <div className="text-xs text-muted-foreground">Warning</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">{inactiveCount}</div>
            <div className="text-xs text-muted-foreground">Inactive</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">{summary.totalModels}</div>
            <div className="text-xs text-muted-foreground">Total Models</div>
          </CardContent>
        </Card>
      </div>

      {/* Provider Cards */}
      <div className="space-y-4">
        {providers.map((provider) => {
          const keyStatus = getKeyStatus(provider)
          const keyConfig = keyStatusConfig[keyStatus]
          const KeyIcon = keyConfig.icon
          const testResult = testResults[provider.provider]

          return (
            <Card key={provider.provider} className="bg-card/50 border-border/50">
              <CardContent className="p-4">
                {/* Header Row */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Server className="h-5 w-5 text-muted-foreground" />
                    <span className="text-sm font-bold">{provider.label}</span>
                    <Badge
                      variant="outline"
                      className={cn('text-[10px]', {
                        'border-emerald-600/30 text-emerald-600 dark:text-emerald-400': provider.health === 'healthy',
                        'border-yellow-600/30 text-yellow-600 dark:text-yellow-400': provider.health === 'degraded',
                        'border-red-600/30 text-red-600 dark:text-red-400': provider.health === 'down' || (!provider.isAvailable && keyStatus === 'missing'),
                        'border-gray-600/30 text-gray-600 dark:text-gray-400': provider.health === 'unknown' && provider.isAvailable,
                      })}
                    >
                      {provider.isAvailable
                        ? provider.health === 'degraded' ? 'DEGRADED' : provider.health.toUpperCase()
                        : 'INACTIVE'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <KeyIcon className={cn('h-4 w-4', keyConfig.color)} />
                    <span className={cn('text-xs', keyConfig.color)}>{keyConfig.label}</span>
                  </div>
                </div>

                {/* Key Status & Models Row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                  {/* API Key */}
                  <div className="space-y-1">
                    <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Key className="h-3 w-3" /> API Key
                    </div>
                    <code className="text-xs font-mono">
                      {provider.keyStatus.activeKeyMasked || '---'}
                    </code>
                    <div className="text-[9px] text-muted-foreground">
                      {provider.keyStatus.healthyKeys}/{provider.keyStatus.totalKeys} keys healthy
                    </div>
                  </div>

                  {/* Models */}
                  <div className="space-y-1">
                    <div className="text-[10px] text-muted-foreground">Models</div>
                    <span className="text-xs font-mono">{provider.activeModels}/{provider.totalModels}</span>
                    <div className="text-[9px] text-muted-foreground">
                      {provider.activeModels > 0 ? 'Active' : 'No models active'}
                    </div>
                  </div>

                  {/* Latency */}
                  <div className="space-y-1">
                    <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Gauge className="h-3 w-3" /> Avg Latency
                    </div>
                    <span className="text-xs font-mono">{provider.avgLatencyMs > 0 ? `${provider.avgLatencyMs}ms` : 'N/A'}</span>
                  </div>

                  {/* Cost */}
                  <div className="space-y-1">
                    <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <DollarSign className="h-3 w-3" /> Cost
                    </div>
                    <span className="text-xs font-mono">
                      {provider.costEstimate.inputPer1k === 0 && provider.costEstimate.outputPer1k === 0
                        ? 'FREE'
                        : `$${provider.costEstimate.inputPer1k}/$${provider.costEstimate.outputPer1k}`}
                    </span>
                    <div className="text-[9px] text-muted-foreground truncate" title={provider.costEstimate.note}>
                      {provider.costEstimate.note}
                    </div>
                  </div>
                </div>

                {/* Capabilities */}
                <div className="mb-3">
                  <div className="text-[10px] text-muted-foreground mb-1.5">Capabilities</div>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(provider.capabilities).map(([cap, enabled]) => {
                      const capInfo = capabilityIcons[cap]
                      if (!capInfo || !enabled) return null
                      const CapIcon = capInfo.icon
                      return (
                        <Badge
                          key={cap}
                          variant="secondary"
                          className="h-5 px-1.5 text-[9px] gap-1 bg-card border border-border/50"
                        >
                          <CapIcon className={cn('h-2.5 w-2.5', capInfo.color)} />
                          {capInfo.label}
                        </Badge>
                      )
                    })}
                  </div>
                </div>

                {/* Rate Limits & Quota */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                  {/* Rate Limit */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground">Rate Limit (RPM)</span>
                      <span className="font-mono">{provider.rateLimits.remaining.rpm} / {provider.rateLimits.rpm}</span>
                    </div>
                    <Progress
                      value={provider.rateLimits.rpm > 0 ? (provider.rateLimits.remaining.rpm / provider.rateLimits.rpm) * 100 : 0}
                      className="h-1.5"
                    />
                  </div>

                  {/* Daily Limit */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground">Daily Limit (RPD)</span>
                      <span className="font-mono">{provider.rateLimits.remaining.rpd.toLocaleString()} / {provider.rateLimits.rpd.toLocaleString()}</span>
                    </div>
                    <Progress
                      value={provider.rateLimits.rpd > 0 ? (provider.rateLimits.remaining.rpd / provider.rateLimits.rpd) * 100 : 0}
                      className="h-1.5"
                    />
                  </div>
                </div>

                {/* Cooldown Warning */}
                {provider.rateLimits.isCooldown && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-yellow-500/10 border border-yellow-500/20 mb-3">
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
                    <span className="text-[10px] text-yellow-600 dark:text-yellow-400">
                      Cooldown active — {Math.ceil(provider.rateLimits.cooldownRemainingMs / 1000)}s remaining
                    </span>
                  </div>
                )}

                {/* Models List (collapsible) */}
                {provider.models && provider.models.length > 0 && (
                  <div className="mb-3">
                    <Separator className="mb-2" />
                    <div className="text-[10px] text-muted-foreground mb-1.5">Available Models</div>
                    <div className="flex flex-wrap gap-1.5">
                      {provider.models.map((model) => (
                        <Badge
                          key={model.id}
                          variant="outline"
                          className={cn('text-[9px] h-5 px-1.5', {
                            'border-emerald-600/30 text-emerald-600 dark:text-emerald-400': model.health === 'healthy',
                            'border-yellow-600/30 text-yellow-600 dark:text-yellow-400': model.health === 'degraded',
                            'border-red-600/30 text-red-600 dark:text-red-400': model.health === 'down',
                            'border-gray-400/30 text-gray-500': model.health === 'unknown',
                          })}
                        >
                          {model.displayName}
                          <span className="ml-1 opacity-60">({model.tier})</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Test Connection & Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-border/30">
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-[10px] gap-1"
                      onClick={() => testConnection(provider.provider)}
                      disabled={testingProvider === provider.provider}
                    >
                      {testingProvider === provider.provider ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <TestTube className="h-3 w-3" />
                      )}
                      Test Connection
                    </Button>
                    {provider.keyStatus.hasAvailableKey && (
                      <Badge variant="secondary" className="h-5 px-1.5 text-[9px] bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-0">
                        <Zap className="h-2.5 w-2.5 mr-0.5" />
                        Ready
                      </Badge>
                    )}
                  </div>

                  {/* Test Result */}
                  {testResult && (
                    <div className={cn('flex items-center gap-1.5 text-[10px]', {
                      'text-emerald-600 dark:text-emerald-400': testResult.success,
                      'text-red-600 dark:text-red-400': !testResult.success,
                    })}>
                      {testResult.success ? (
                        <>
                          <CheckCircle2 className="h-3 w-3" />
                          Connected ({testResult.latencyMs}ms)
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3 w-3" />
                          {testResult.error || 'Failed'}
                        </>
                      )}
                    </div>
                  )}

                  <span className="text-[9px] text-muted-foreground font-mono">
                    {provider.rateLimits.description}
                  </span>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
