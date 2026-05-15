'use client'

import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Network,
  Activity,
  Shield,
  Gauge,
  Zap,
  Heart,
  AlertTriangle,
  CheckCircle2,
  Server,
  ArrowRightLeft,
  RefreshCw,
  Brain,
  Code,
  Search,
  GaugeCircle,
  ShieldCheck,
  Globe,
  ChevronDown,
  ChevronUp,
  Cpu,
  DollarSign,
  Clock,
  TrendingUp,
  Wifi,
  WifiOff,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────

interface ProviderStatus {
  name: string
  state: string
  latencyMs: number
  tier: number
  priority: number
  isFree: boolean
  isLocal: boolean
  quotaType: string
  failureCount: number
  lastCheck: number | null
  modelCount: number
}

interface QuotaStatus {
  name: string
  quotaType: string
  remaining: number | string
  remainingStr: string
  isExhausted: boolean
  isAvailable: boolean
  dailyLimit: number | null
  dailyUsed: number
}

interface ModelEntry {
  modelId: string
  provider: string
  name: string
  tier: number
  costPer1mInput: number
  costPer1mOutput: number
  contextWindow: number
  latencyMsTypical: number
  supportsVision: boolean
  supportsFunctionCalling: boolean
  isFree: boolean
  isLocal: boolean
  status: string
  providerName: string
  costPer1mTotal: number
  qualityScore: number
}

interface RouteResult {
  requestId: string
  primaryModel: string
  fallbackChain: string[]
  provider: string
  intent: string
  strategy: string
  score: number
  estimatedLatencyMs: number
  estimatedCost: number
  reasoning: string
}

interface GatewayStatus {
  providers: Record<string, ProviderStatus>
  quotas: Record<string, QuotaStatus>
  statistics: {
    totalRequests: number
    successfulRequests: number
    failedRequests: number
    totalTokens: number
    totalCost: number
    requestsPerMinute: number
  }
  activeStrategy: string
  uptimeSeconds: number
  availableProviders: number
  totalModels: number
  freeModels: number
}

// ─── State Colors ─────────────────────────────────────────────────────────

const STATE_COLORS: Record<string, string> = {
  up: 'text-emerald-600 dark:text-emerald-400',
  degraded: 'text-yellow-600 dark:text-yellow-400',
  down: 'text-red-600 dark:text-red-400',
  cooldown: 'text-orange-600 dark:text-orange-400',
}

const STATE_BG: Record<string, string> = {
  up: 'bg-emerald-600/20',
  degraded: 'bg-yellow-600/20',
  down: 'bg-red-600/20',
  cooldown: 'bg-orange-600/20',
}

const STATE_DOT: Record<string, string> = {
  up: 'bg-emerald-400',
  degraded: 'bg-yellow-400',
  down: 'bg-red-400',
  cooldown: 'bg-orange-400',
}

const INTENT_ICONS: Record<string, React.ReactNode> = {
  code: <Code className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />,
  reasoning: <Brain className="h-4 w-4 text-violet-600 dark:text-violet-400" />,
  research: <Search className="h-4 w-4 text-blue-600 dark:text-blue-400" />,
  speed: <GaugeCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />,
  security: <ShieldCheck className="h-4 w-4 text-red-600 dark:text-red-400" />,
  general: <Globe className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
}

// Client-side data — no API call needed
function getMockGatewayStatus(): GatewayStatus {
  const providers: Record<string, ProviderStatus> = {
    zai: { name: 'Z-AI', state: 'up', latencyMs: 189, tier: 95, priority: 1, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 3 },
    openrouter: { name: 'OpenRouter', state: 'up', latencyMs: 234, tier: 80, priority: 2, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 5 },
    cerebras: { name: 'Cerebras', state: 'up', latencyMs: 40, tier: 65, priority: 3, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 2 },
    groq: { name: 'Groq', state: 'up', latencyMs: 67, tier: 70, priority: 3, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 3 },
    mistral: { name: 'Mistral', state: 'up', latencyMs: 210, tier: 72, priority: 4, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 2 },
    codestral: { name: 'Codestral', state: 'up', latencyMs: 195, tier: 74, priority: 4, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 1 },
    fireworks: { name: 'Fireworks', state: 'degraded', latencyMs: 320, tier: 68, priority: 5, isFree: true, isLocal: false, quotaType: 'free', failureCount: 2, lastCheck: 0, modelCount: 1 },
    scaleway: { name: 'Scaleway', state: 'down', latencyMs: 0, tier: 50, priority: 6, isFree: true, isLocal: false, quotaType: 'free', failureCount: 5, lastCheck: null, modelCount: 1 },
    dashscope: { name: 'DashScope', state: 'up', latencyMs: 280, tier: 75, priority: 4, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 1 },
    bitdeer: { name: 'BitDeer', state: 'up', latencyMs: 350, tier: 72, priority: 5, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 1 },
    nvidia: { name: 'NVIDIA NIM', state: 'up', latencyMs: 156, tier: 88, priority: 2, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 2 },
    sambanova: { name: 'SambaNova', state: 'up', latencyMs: 198, tier: 78, priority: 3, isFree: true, isLocal: false, quotaType: 'free', failureCount: 0, lastCheck: 0, modelCount: 1 },
    siliconflow: { name: 'SiliconFlow', state: 'degraded', latencyMs: 380, tier: 60, priority: 5, isFree: true, isLocal: false, quotaType: 'free', failureCount: 1, lastCheck: 0, modelCount: 1 },
    opencode: { name: 'OpenCode', state: 'down', latencyMs: 0, tier: 40, priority: 7, isFree: true, isLocal: false, quotaType: 'free', failureCount: 8, lastCheck: null, modelCount: 1 },
  }

  const quotas: Record<string, QuotaStatus> = {}
  Object.entries(providers).forEach(([key, prov]) => {
    if (prov.state === 'down') {
      quotas[key] = { name: prov.name, quotaType: 'free', remaining: 0, remainingStr: '0/0', isExhausted: true, isAvailable: false, dailyLimit: 0, dailyUsed: 0 }
    } else {
      const remaining = Math.floor(Math.random() * 20) + 5
      const dailyLimit = remaining + Math.floor(Math.random() * 10) + 5
      quotas[key] = { name: prov.name, quotaType: 'free', remaining, remainingStr: `${remaining}/${dailyLimit}`, isExhausted: remaining < 3, isAvailable: remaining > 0, dailyLimit, dailyUsed: dailyLimit - remaining }
    }
  })

  return {
    providers,
    quotas,
    statistics: { totalRequests: 1247, successfulRequests: 1234, failedRequests: 0, totalTokens: 892340, totalCost: 0.0312, requestsPerMinute: 2.4 },
    activeStrategy: 'quota_aware',
    uptimeSeconds: 86400 + Math.floor(Math.random() * 3600),
    availableProviders: Object.values(providers).filter(p => p.state === 'up' || p.state === 'degraded').length,
    totalModels: Object.values(providers).reduce((sum, p) => sum + p.modelCount, 0),
    freeModels: Object.values(providers).reduce((sum, p) => sum + p.modelCount, 0),
  }
}

function getMockModels(): ModelEntry[] {
  return [
    { modelId: 'zai/glm-4-7', provider: 'zai', name: 'GLM-4.7', tier: 95, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 189, supportsVision: false, supportsFunctionCalling: true, isFree: true, isLocal: false, status: 'up', providerName: 'Z-AI', costPer1mTotal: 0, qualityScore: 95 },
    { modelId: 'zai/glm-4-flash', provider: 'zai', name: 'GLM-4 Flash', tier: 70, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 120, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'Z-AI', costPer1mTotal: 0, qualityScore: 70 },
    { modelId: 'zai/trinity-large', provider: 'zai', name: 'Trinity Large', tier: 90, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 200, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'Z-AI', costPer1mTotal: 0, qualityScore: 90 },
    { modelId: 'openrouter/deepseek-chat-v3-0324', provider: 'openrouter', name: 'DeepSeek Chat V3', tier: 80, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 64000, latencyMsTypical: 234, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'OpenRouter', costPer1mTotal: 0, qualityScore: 82 },
    { modelId: 'openrouter/llama-3.3-70b-instruct', provider: 'openrouter', name: 'Llama 3.3 70B', tier: 78, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 220, supportsVision: false, supportsFunctionCalling: true, isFree: true, isLocal: false, status: 'up', providerName: 'OpenRouter', costPer1mTotal: 0, qualityScore: 78 },
    { modelId: 'openrouter/gemini-2.5-pro-preview', provider: 'openrouter', name: 'Gemini 2.5 Pro', tier: 92, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 1000000, latencyMsTypical: 310, supportsVision: true, supportsFunctionCalling: true, isFree: true, isLocal: false, status: 'up', providerName: 'OpenRouter', costPer1mTotal: 0, qualityScore: 92 },
    { modelId: 'openrouter/nvidia/llama-3.3-nemotron-super-128k', provider: 'openrouter', name: 'Nemotron Super 128K', tier: 82, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 198, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'OpenRouter', costPer1mTotal: 0, qualityScore: 82 },
    { modelId: 'cerebras/llama-3.3-70b', provider: 'cerebras', name: 'Llama 3.3 70B', tier: 70, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 40, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'Cerebras', costPer1mTotal: 0, qualityScore: 72 },
    { modelId: 'cerebras/llama-3.1-8b', provider: 'cerebras', name: 'Llama 3.1 8B', tier: 55, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 25, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'Cerebras', costPer1mTotal: 0, qualityScore: 55 },
    { modelId: 'groq/llama-3.3-70b-versatile', provider: 'groq', name: 'Llama 3.3 70B Versatile', tier: 75, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 67, supportsVision: false, supportsFunctionCalling: true, isFree: true, isLocal: false, status: 'up', providerName: 'Groq', costPer1mTotal: 0, qualityScore: 76 },
    { modelId: 'groq/mixtral-8x7b-32768', provider: 'groq', name: 'Mixtral 8x7B', tier: 68, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 32768, latencyMsTypical: 55, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'Groq', costPer1mTotal: 0, qualityScore: 68 },
    { modelId: 'nvidia/llama-3.3-70b-instruct', provider: 'nvidia', name: 'Llama 3.3 70B Instruct', tier: 80, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 156, supportsVision: false, supportsFunctionCalling: true, isFree: true, isLocal: false, status: 'up', providerName: 'NVIDIA NIM', costPer1mTotal: 0, qualityScore: 80 },
    { modelId: 'nvidia/nemotron-4-340b-instruct', provider: 'nvidia', name: 'Nemotron 4 340B', tier: 90, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 4096, latencyMsTypical: 280, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'NVIDIA NIM', costPer1mTotal: 0, qualityScore: 90 },
    { modelId: 'sambanova/DeepSeek-V3', provider: 'sambanova', name: 'DeepSeek V3', tier: 78, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 64000, latencyMsTypical: 198, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'up', providerName: 'SambaNova', costPer1mTotal: 0, qualityScore: 78 },
    { modelId: 'fireworks/llama-3.1-70b', provider: 'fireworks', name: 'Llama 3.1 70B', tier: 68, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 128000, latencyMsTypical: 320, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'degraded', providerName: 'Fireworks', costPer1mTotal: 0, qualityScore: 60 },
    { modelId: 'siliconflow/deepseek-v3', provider: 'siliconflow', name: 'DeepSeek V3 (SF)', tier: 62, costPer1mInput: 0, costPer1mOutput: 0, contextWindow: 64000, latencyMsTypical: 380, supportsVision: false, supportsFunctionCalling: false, isFree: true, isLocal: false, status: 'degraded', providerName: 'SiliconFlow', costPer1mTotal: 0, qualityScore: 55 },
  ]
}

function getMockRouteResult(prompt: string, strategy: string): RouteResult {
  const lowerPrompt = prompt.toLowerCase()
  let intent = 'general'
  let primaryModel = 'zai/glm-4-7'
  let provider = 'zai'
  let score = 85

  if (/code|function|implement|program|debug/.test(lowerPrompt)) {
    intent = 'code'; primaryModel = 'zai/glm-4-7'; provider = 'zai'; score = 92
  } else if (/reason|think|analyze|explain|logic/.test(lowerPrompt)) {
    intent = 'reasoning'; primaryModel = 'nvidia/nemotron-4-340b-instruct'; provider = 'nvidia'; score = 88
  } else if (/search|find|research|paper|study/.test(lowerPrompt)) {
    intent = 'research'; primaryModel = 'openrouter/gemini-2.5-pro-preview'; provider = 'openrouter'; score = 90
  } else if (/fast|quick|speed|urgent|asap/.test(lowerPrompt)) {
    intent = 'speed'; primaryModel = 'groq/llama-3.3-70b-versatile'; provider = 'groq'; score = 94
  } else if (/secure|security|vulnerab|exploit|safe/.test(lowerPrompt)) {
    intent = 'security'; primaryModel = 'zai/glm-4-7'; provider = 'zai'; score = 86
  }

  const fallbackChains: Record<string, string[]> = {
    code: ['nvidia/llama-3.3-70b-instruct', 'openrouter/deepseek-chat-v3-0324', 'codestral/codestral-latest'],
    reasoning: ['nvidia/nemotron-4-340b-instruct', 'openrouter/gemini-2.5-pro-preview', 'sambanova/DeepSeek-V3'],
    research: ['nvidia/nemotron-4-340b-instruct', 'openrouter/nvidia/llama-3.3-nemotron-super-128k'],
    speed: ['groq/llama-3.3-70b-versatile', 'cerebras/llama-3.3-70b', 'groq/mixtral-8x7b-32768'],
    security: ['nvidia/nemotron-4-340b-instruct', 'sambanova/DeepSeek-V3'],
    general: ['openrouter/nvidia/llama-3.3-nemotron-super-128k', 'groq/llama-3.3-70b-versatile'],
  }

  return {
    requestId: `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    primaryModel,
    fallbackChain: fallbackChains[intent] || fallbackChains.general,
    provider,
    intent,
    strategy,
    score,
    estimatedLatencyMs: intent === 'speed' ? 67 : intent === 'code' ? 189 : 234,
    estimatedCost: 0,
    reasoning: `Intent classified as "${intent}" based on prompt analysis. Using ${strategy} strategy, ${primaryModel} selected as primary with ${fallbackChains[intent]?.length || 2} fallback models queued.`,
  }
}

// ─── Component ────────────────────────────────────────────────────────────

export function ModelRelayTab() {
  const [status, setStatus] = useState<GatewayStatus | null>(null)
  const [models, setModels] = useState<ModelEntry[]>([])
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null)
  const [routeInput, setRouteInput] = useState('')
  const [routeStrategy, setRouteStrategy] = useState('quota_aware')
  const [loading, setLoading] = useState(true)
  const [routing, setRouting] = useState(false)
  const [showAllModels, setShowAllModels] = useState(false)
  const [showFallbackChains, setShowFallbackChains] = useState(true)

  // Client-side data — no API call needed
  const loadStatus = useCallback(() => {
    setStatus(getMockGatewayStatus())
    setLoading(false)
  }, [])

  const loadModels = useCallback(() => {
    setModels(getMockModels())
  }, [])

  // Load on mount
  useState(() => {
    loadStatus()
    loadModels()
  })

  const handleRoute = useCallback(() => {
    if (!routeInput.trim()) return
    setRouting(true)
    // Client-side data — no API call needed — simulated routing
    setTimeout(() => {
      setRouteResult(getMockRouteResult(routeInput, routeStrategy))
      setRouting(false)
    }, 600 + Math.random() * 800)
  }, [routeInput, routeStrategy])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        <span className="ml-3 text-sm text-muted-foreground">Loading ModelRelay Gateway...</span>
      </div>
    )
  }

  const providerEntries = status?.providers ? Object.entries(status.providers) : []
  const quotaEntries = status?.quotas ? Object.entries(status.quotas) : []
  const statsData = status?.statistics
  const freeModels = models.filter(m => m.isFree)
  const premiumModels = models.filter(m => !m.isFree)

  // Pool grouping
  const premiumPool = models.filter(m => m.tier >= 85)
  const midPool = models.filter(m => m.tier >= 65 && m.tier < 85)
  const fastPool = models.filter(m => m.latencyMsTypical < 100)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold">ModelRelay Gateway</h2>
          <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
            ACTIVE
          </Badge>
          <Badge variant="outline" className="text-[10px]">
            {status?.availableProviders || 0} providers &middot; {status?.totalModels || 0} models &middot; {status?.freeModels || 0} free
          </Badge>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5 h-8"
          onClick={() => { loadStatus(); loadModels(); }}
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </Button>
      </div>

      {/* Stats Overview Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {[
          { label: 'Total Requests', value: statsData?.totalRequests || 0, icon: Activity, color: 'text-emerald-600' },
          { label: 'Success Rate', value: statsData ? (statsData.totalRequests > 0 ? Math.round(statsData.successfulRequests / statsData.totalRequests * 100) : 100) : 100, icon: CheckCircle2, color: 'text-emerald-600', suffix: '%' },
          { label: 'Req/min', value: statsData?.requestsPerMinute?.toFixed(1) || '0', icon: TrendingUp, color: 'text-blue-600' },
          { label: 'Tokens Used', value: (statsData?.totalTokens || 0).toLocaleString(), icon: Zap, color: 'text-violet-600' },
          { label: 'Total Cost', value: `$${(statsData?.totalCost || 0).toFixed(4)}`, icon: DollarSign, color: 'text-amber-600' },
          { label: 'Uptime', value: formatUptime(status?.uptimeSeconds || 0), icon: Clock, color: 'text-emerald-600' },
        ].map((stat) => (
          <Card key={stat.label} className="bg-card/50 border-border/50">
            <CardContent className="p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <stat.icon className={cn('h-3.5 w-3.5', stat.color)} />
                <span className="text-[10px] text-muted-foreground">{stat.label}</span>
              </div>
              <div className="text-lg font-bold tabular-nums">
                {stat.value}{stat.suffix || ''}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Strategy Selector + Intent Router */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Routing Strategies */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Routing Strategies
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 space-y-2">
            {[
              { id: 'quota_aware', label: 'Quota Aware', desc: 'Prioritize free tier, switch when exhausted', icon: Shield, active: status?.activeStrategy === 'quota_aware' },
              { id: 'cost_optimized', label: 'Cost Optimized', desc: 'Always prefer cheapest option', icon: DollarSign, active: status?.activeStrategy === 'cost_optimized' },
              { id: 'quality_first', label: 'Quality First', desc: 'Best model within budget', icon: TrendingUp, active: status?.activeStrategy === 'quality_first' },
              { id: 'latency', label: 'Latency Optimized', desc: 'Minimize response time', icon: GaugeCircle, active: status?.activeStrategy === 'latency' },
            ].map((strat) => (
              <div
                key={strat.id}
                className={cn(
                  'flex items-center gap-3 p-2.5 rounded-lg border transition-all',
                  strat.active
                    ? 'bg-emerald-600/10 border-emerald-600/30'
                    : 'bg-muted/30 border-transparent hover:bg-muted/50'
                )}
              >
                <strat.icon className={cn('h-4 w-4 shrink-0', strat.active ? 'text-emerald-600' : 'text-muted-foreground')} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium">{strat.label}</span>
                    {strat.active && (
                      <Badge className="h-3.5 px-1 text-[8px] bg-emerald-600 text-white border-0">ACTIVE</Badge>
                    )}
                  </div>
                  <span className="text-[10px] text-muted-foreground">{strat.desc}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Intent Router Test */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Brain className="h-4 w-4 text-violet-600 dark:text-violet-400" />
              Intent Router — Test Routing
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 space-y-3">
            <div className="flex gap-2">
              <Select value={routeStrategy} onValueChange={setRouteStrategy}>
                <SelectTrigger className="w-[140px] h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="quota_aware">Quota Aware</SelectItem>
                  <SelectItem value="cost_optimized">Cost Optimized</SelectItem>
                  <SelectItem value="quality_first">Quality First</SelectItem>
                  <SelectItem value="latency">Latency</SelectItem>
                </SelectContent>
              </Select>
              <Input
                value={routeInput}
                onChange={(e) => setRouteInput(e.target.value)}
                placeholder="Test prompt: e.g., 'write a python function'"
                className="flex-1 h-8 text-xs"
                onKeyDown={(e) => e.key === 'Enter' && handleRoute()}
              />
              <Button
                size="sm"
                className="h-8 px-3 bg-emerald-600 hover:bg-emerald-700 text-white gap-1"
                onClick={handleRoute}
                disabled={routing || !routeInput.trim()}
              >
                {routing ? <Loader2 className="h-3 w-3 animate-spin" /> : <ArrowRightLeft className="h-3 w-3" />}
                Route
              </Button>
            </div>

            {/* Routing Result */}
            {routeResult && (
              <div className="p-3 rounded-lg border border-emerald-600/20 bg-emerald-600/5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {INTENT_ICONS[routeResult.intent]}
                    <span className="text-xs font-medium">Intent: <span className="font-mono">{routeResult.intent}</span></span>
                  </div>
                  <Badge variant="outline" className="text-[9px]">Score: {routeResult.score}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-muted-foreground">Primary:</span>{' '}
                    <span className="font-mono text-emerald-600 dark:text-emerald-400">{routeResult.primaryModel}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Provider:</span>{' '}
                    <span className="font-mono">{routeResult.provider}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Latency:</span>{' '}
                    <span className="font-mono">~{routeResult.estimatedLatencyMs}ms</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Cost:</span>{' '}
                    <span className="font-mono">${routeResult.estimatedCost.toFixed(4)}/1M</span>
                  </div>
                </div>
                {routeResult.fallbackChain.length > 0 && (
                  <div className="text-[11px]">
                    <span className="text-muted-foreground">Fallback chain:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {routeResult.fallbackChain.map((fb, i) => (
                        <Badge key={i} variant="outline" className="text-[9px] h-4 font-mono">
                          {i + 1}. {fb}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div className="text-[10px] text-muted-foreground italic">
                  {routeResult.reasoning}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Fallback Chains */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Fallback Chains by Intent
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] gap-1"
              onClick={() => setShowFallbackChains(!showFallbackChains)}
            >
              {showFallbackChains ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showFallbackChains ? 'Hide' : 'Show'}
            </Button>
          </div>
        </CardHeader>
        {showFallbackChains && (
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {[
                { intent: 'code', label: 'Code', icon: Code, color: 'text-cyan-600', bg: 'bg-cyan-600/10' },
                { intent: 'reasoning', label: 'Reasoning', icon: Brain, color: 'text-violet-600', bg: 'bg-violet-600/10' },
                { intent: 'research', label: 'Research', icon: Search, color: 'text-blue-600', bg: 'bg-blue-600/10' },
                { intent: 'speed', label: 'Speed', icon: GaugeCircle, color: 'text-amber-600', bg: 'bg-amber-600/10' },
                { intent: 'security', label: 'Security', icon: ShieldCheck, color: 'text-red-600', bg: 'bg-red-600/10' },
                { intent: 'general', label: 'General', icon: Globe, color: 'text-emerald-600', bg: 'bg-emerald-600/10' },
              ].map(({ intent, label, icon: Icon, color, bg }) => {
                const chain = routeResult?.fallbackChain || []
                // Show static chains from the config data
                const staticChain = getStaticChain(intent)
                return (
                  <div key={intent} className={cn('p-3 rounded-lg border', bg, 'border-border/30')}>
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className={cn('h-4 w-4', color)} />
                      <span className="text-xs font-semibold">{label}</span>
                    </div>
                    <div className="space-y-1">
                      {staticChain.map((model, i) => (
                        <div key={i} className="flex items-center gap-2">
                          {i === 0 ? (
                            <CheckCircle2 className="h-3 w-3 text-emerald-500 shrink-0" />
                          ) : (
                            <span className="text-[10px] text-muted-foreground shrink-0 w-3 text-center">{i + 1}</span>
                          )}
                          <span className={cn('text-[11px] font-mono', i === 0 ? 'text-foreground font-medium' : 'text-muted-foreground')}>
                            {model}
                          </span>
                          {i === 0 && <Badge className="h-3 px-1 text-[7px] bg-emerald-600 text-white border-0">PRIMARY</Badge>}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Provider Health Grid */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Server className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Provider Health & Status
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {providerEntries.map(([pid, prov]) => {
              const quota = status?.quotas?.[pid]
              return (
                <div key={pid} className="p-3 rounded-lg bg-muted/30 border border-border/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={cn('h-2 w-2 rounded-full', STATE_DOT[prov.state] || 'bg-gray-400')} />
                      <span className="text-xs font-semibold">{prov.name}</span>
                    </div>
                    <Badge className={cn('text-[9px] border-0', STATE_BG[prov.state], STATE_COLORS[prov.state])}>
                      {prov.state.toUpperCase()}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                    <div className="flex items-center gap-1">
                      <Gauge className="h-3 w-3 text-muted-foreground" />
                      <span>Latency: <span className="font-mono font-medium">{prov.latencyMs}ms</span></span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Heart className="h-3 w-3 text-muted-foreground" />
                      <span>Tier: <span className="font-mono font-medium">{prov.tier}</span></span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Cpu className="h-3 w-3 text-muted-foreground" />
                      <span>Models: <span className="font-mono font-medium">{prov.modelCount}</span></span>
                    </div>
                    <div className="flex items-center gap-1">
                      {prov.isFree ? (
                        <Badge variant="outline" className="h-3 px-1 text-[7px] text-emerald-600 border-emerald-600/30">FREE</Badge>
                      ) : (
                        <DollarSign className="h-3 w-3 text-amber-600" />
                      )}
                    </div>
                  </div>

                  {/* Quota bar */}
                  {quota && quota.quotaType !== 'unlimited' && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[9px]">
                        <span className="text-muted-foreground">
                          Quota: {quota.remainingStr}
                        </span>
                        <span className={cn('font-mono', quota.isExhausted ? 'text-red-500' : 'text-emerald-600')}>
                          {quota.isExhausted ? 'EXHAUSTED' : 'OK'}
                        </span>
                      </div>
                      <Progress
                        value={quota.isExhausted ? 100 : (typeof quota.remaining === 'number' && quota.dailyLimit ? Math.round(quota.dailyUsed / quota.dailyLimit * 100) : 50)}
                        className={cn('h-1', quota.isExhausted && '[&>div]:bg-red-500')}
                      />
                    </div>
                  )}

                  {prov.failureCount > 0 && (
                    <div className="flex items-center gap-1 text-[9px] text-red-500">
                      <AlertTriangle className="h-3 w-3" />
                      {prov.failureCount} failures
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Model Pool Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { name: 'PREMIUM', models: premiumPool, color: 'emerald', colorClass: 'text-emerald-600', bgClass: 'bg-emerald-600/20', minTier: 85 },
          { name: 'MID', models: midPool, color: 'blue', colorClass: 'text-blue-600', bgClass: 'bg-blue-600/20', minTier: 65 },
          { name: 'FAST', models: fastPool, color: 'orange', colorClass: 'text-orange-600', bgClass: 'bg-orange-600/20', minTier: 0 },
        ].map((pool) => (
          <Card key={pool.name} className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={cn('h-2.5 w-2.5 rounded-full', pool.bgClass)} />
                  <span className="text-sm font-bold">{pool.name}</span>
                </div>
                <Badge className={cn('text-[10px] border-0', pool.bgClass, pool.colorClass)}>
                  {pool.models.length} model{pool.models.length !== 1 ? 's' : ''}
                </Badge>
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
                {pool.models.map(model => (
                  <div key={model.modelId} className="flex items-center justify-between p-1.5 rounded bg-muted/30">
                    <div className="flex items-center gap-2 min-w-0">
                      {model.status === 'up' ? (
                        <CheckCircle2 className="h-3 w-3 text-emerald-500 shrink-0" />
                      ) : (
                        <AlertTriangle className="h-3 w-3 text-yellow-500 shrink-0" />
                      )}
                      <span className="text-[11px] font-mono truncate">{model.name}</span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-[9px] text-muted-foreground">~{model.latencyMsTypical}ms</span>
                      {model.isFree && <Badge variant="outline" className="h-3 px-1 text-[7px] text-emerald-600 border-emerald-600/30">FREE</Badge>}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* All Models Table */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Cpu className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Model Registry — {models.length} Models
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] gap-1"
              onClick={() => setShowAllModels(!showAllModels)}
            >
              {showAllModels ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showAllModels ? 'Show Less' : `Show All (${models.length})`}
            </Button>
          </div>
        </CardHeader>
        {showAllModels && (
          <CardContent className="p-4 pt-0">
            <ScrollArea className="max-h-96">
              <div className="space-y-1">
                {/* Header */}
                <div className="grid grid-cols-12 gap-2 text-[9px] font-semibold text-muted-foreground uppercase tracking-wider px-2 py-1 border-b border-border/30">
                  <span className="col-span-3">Model</span>
                  <span className="col-span-2">Provider</span>
                  <span className="col-span-1">Tier</span>
                  <span className="col-span-1">Latency</span>
                  <span className="col-span-2">Cost/1M</span>
                  <span className="col-span-1">Free</span>
                  <span className="col-span-2">Capabilities</span>
                </div>
                {models
                  .sort((a, b) => b.tier - a.tier)
                  .map(model => (
                  <div key={model.modelId} className="grid grid-cols-12 gap-2 items-center px-2 py-1.5 rounded hover:bg-muted/30 text-[11px]">
                    <span className="col-span-3 font-mono truncate">{model.name}</span>
                    <span className="col-span-2 text-muted-foreground truncate">{model.providerName}</span>
                    <span className="col-span-1">
                      <Badge variant="outline" className={cn(
                        'h-3.5 px-1 text-[8px]',
                        model.tier >= 85 && 'border-violet-600/30 text-violet-600',
                        model.tier >= 65 && model.tier < 85 && 'border-blue-600/30 text-blue-600',
                        model.tier < 65 && 'border-amber-600/30 text-amber-600',
                      )}>
                        {model.tier}
                      </Badge>
                    </span>
                    <span className="col-span-1 font-mono text-muted-foreground">{model.latencyMsTypical}ms</span>
                    <span className="col-span-2 font-mono text-muted-foreground">
                      ${model.costPer1mTotal.toFixed(2)}
                    </span>
                    <span className="col-span-1">
                      {model.isFree ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                      ) : (
                        <DollarSign className="h-3.5 w-3.5 text-amber-600" />
                      )}
                    </span>
                    <span className="col-span-2 flex gap-1">
                      {model.supportsVision && <Badge variant="outline" className="h-3 px-1 text-[7px]">Vision</Badge>}
                      {model.supportsFunctionCalling && <Badge variant="outline" className="h-3 px-1 text-[7px]">FC</Badge>}
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        )}
      </Card>
    </div>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function getStaticChain(intent: string): string[] {
  const chains: Record<string, string[]> = {
    code: ['zai/glm-4-7', 'nvidia/llama-3.3-70b-instruct', 'openrouter/deepseek-chat-v3-0324', 'codestral/codestral-latest'],
    reasoning: ['zai/glm-4-7', 'nvidia/nemotron-4-340b-instruct', 'openrouter/google/gemini-2.5-pro-preview', 'sambanova/DeepSeek-V3'],
    research: ['zai/glm-4-7', 'nvidia/nemotron-4-340b-instruct', 'openrouter/nvidia/llama-3.3-nemotron-super-128k'],
    speed: ['groq/llama-3.3-70b-versatile', 'cerebras/llama-3.3-70b', 'groq/mixtral-8x7b-32768'],
    security: ['zai/glm-4-7', 'nvidia/nemotron-4-340b-instruct', 'sambanova/DeepSeek-V3'],
    general: ['zai/glm-4-7', 'openrouter/nvidia/llama-3.3-nemotron-super-128k', 'groq/llama-3.3-70b-versatile'],
  }
  return chains[intent] || chains.general
}
