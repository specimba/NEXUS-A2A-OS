'use client'

import { useState, useCallback, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from 'recharts'
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
  ChevronDown,
  ChevronUp,
  Activity,
  BarChart3,
  PieChart as PieChartIcon,
  Grid3x3,
  Play,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'

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

const healthColorMap: Record<string, string> = {
  healthy: 'bg-emerald-500',
  degraded: 'bg-yellow-500',
  down: 'bg-red-500',
  unknown: 'bg-gray-400',
}

const healthLabelMap: Record<string, string> = {
  healthy: 'Healthy',
  degraded: 'Degraded',
  down: 'Down',
  unknown: 'Unknown',
}

// Client-side data — no API call needed
function getMockProviders(): ProvidersResponse {
  const providers: ProviderData[] = [
    {
      provider: 'zai', label: 'Z-AI', isAvailable: true, activeModels: 3, totalModels: 3, health: 'healthy',
      rateLimitRemaining: 85, avgLatencyMs: 189,
      models: [
        { id: 'glm-4-7', tier: 'PREMIUM', displayName: 'GLM-4.7', health: 'healthy', capabilities: ['chat', 'code', 'tools'] },
        { id: 'glm-4-flash', tier: 'FAST', displayName: 'GLM-4 Flash', health: 'healthy', capabilities: ['chat', 'completion'] },
        { id: 'trinity-large', tier: 'PREMIUM', displayName: 'Trinity Large', health: 'healthy', capabilities: ['chat', 'code'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...zai' },
      rateLimits: { rpm: 60, rpd: 1440, remaining: { rpm: 51, rpd: 1224 }, isCooldown: false, cooldownRemainingMs: 0, description: '60 RPM / 1440 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: true, tools: true, completion: true },
    },
    {
      provider: 'openrouter', label: 'OpenRouter', isAvailable: true, activeModels: 5, totalModels: 5, health: 'healthy',
      rateLimitRemaining: 72, avgLatencyMs: 234,
      models: [
        { id: 'deepseek-chat-v3', tier: 'MID', displayName: 'DeepSeek Chat V3', health: 'healthy', capabilities: ['chat', 'code'] },
        { id: 'llama-3.3-70b-instruct', tier: 'MID', displayName: 'Llama 3.3 70B', health: 'healthy', capabilities: ['chat', 'completion'] },
        { id: 'gemini-2.5-pro', tier: 'PREMIUM', displayName: 'Gemini 2.5 Pro', health: 'healthy', capabilities: ['chat', 'vision'] },
        { id: 'nemotron-super-128k', tier: 'MID', displayName: 'Nemotron Super 128K', health: 'healthy', capabilities: ['chat'] },
        { id: 'qwen3-coder', tier: 'MID', displayName: 'Qwen3 Coder', health: 'degraded', capabilities: ['chat', 'code'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...or' },
      rateLimits: { rpm: 50, rpd: 1000, remaining: { rpm: 36, rpd: 720 }, isCooldown: false, cooldownRemainingMs: 0, description: '50 RPM / 1000 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier models' },
      capabilities: { chat: true, vision: true, embedding: false, code: true, tools: false, completion: true },
    },
    {
      provider: 'cerebras', label: 'Cerebras Free', isAvailable: true, activeModels: 2, totalModels: 2, health: 'healthy',
      rateLimitRemaining: 90, avgLatencyMs: 40,
      models: [
        { id: 'llama-3.3-70b', tier: 'FAST', displayName: 'Llama 3.3 70B', health: 'healthy', capabilities: ['chat', 'completion'] },
        { id: 'llama-3.1-8b', tier: 'FAST', displayName: 'Llama 3.1 8B', health: 'healthy', capabilities: ['chat', 'completion'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...cer' },
      rateLimits: { rpm: 30, rpd: 720, remaining: { rpm: 27, rpd: 648 }, isCooldown: false, cooldownRemainingMs: 0, description: '30 RPM / 720 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: false, tools: false, completion: true },
    },
    {
      provider: 'groq', label: 'Groq Free', isAvailable: true, activeModels: 3, totalModels: 3, health: 'healthy',
      rateLimitRemaining: 65, avgLatencyMs: 67,
      models: [
        { id: 'llama-3.3-70b-versatile', tier: 'FAST', displayName: 'Llama 3.3 70B Versatile', health: 'healthy', capabilities: ['chat', 'tools'] },
        { id: 'mixtral-8x7b', tier: 'FAST', displayName: 'Mixtral 8x7B', health: 'healthy', capabilities: ['chat'] },
        { id: 'gemma-fast', tier: 'FAST', displayName: 'Gemma Fast', health: 'healthy', capabilities: ['chat'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...groq' },
      rateLimits: { rpm: 30, rpd: 1440, remaining: { rpm: 19, rpd: 936 }, isCooldown: false, cooldownRemainingMs: 0, description: '30 RPM / 1440 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: false, tools: true, completion: true },
    },
    {
      provider: 'mistral', label: 'Mistral Free', isAvailable: true, activeModels: 2, totalModels: 2, health: 'healthy',
      rateLimitRemaining: 78, avgLatencyMs: 210,
      models: [
        { id: 'mistral-small', tier: 'MID', displayName: 'Mistral Small', health: 'healthy', capabilities: ['chat', 'code'] },
        { id: 'mistral-nemo', tier: 'MID', displayName: 'Mistral Nemo', health: 'healthy', capabilities: ['chat'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...mis' },
      rateLimits: { rpm: 15, rpd: 360, remaining: { rpm: 11, rpd: 280 }, isCooldown: false, cooldownRemainingMs: 0, description: '15 RPM / 360 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: true, tools: false, completion: true },
    },
    {
      provider: 'codestral', label: 'Codestral Free', isAvailable: true, activeModels: 1, totalModels: 1, health: 'healthy',
      rateLimitRemaining: 82, avgLatencyMs: 195,
      models: [
        { id: 'codestral-latest', tier: 'MID', displayName: 'Codestral Latest', health: 'healthy', capabilities: ['chat', 'code'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...cs' },
      rateLimits: { rpm: 10, rpd: 240, remaining: { rpm: 8, rpd: 196 }, isCooldown: false, cooldownRemainingMs: 0, description: '10 RPM / 240 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: true, tools: false, completion: true },
    },
    {
      provider: 'fireworks', label: 'Fireworks AI', isAvailable: true, activeModels: 1, totalModels: 1, health: 'degraded',
      rateLimitRemaining: 55, avgLatencyMs: 320,
      models: [
        { id: 'llama-3.1-70b', tier: 'MID', displayName: 'Llama 3.1 70B', health: 'degraded', capabilities: ['chat'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...fw' },
      rateLimits: { rpm: 20, rpd: 480, remaining: { rpm: 11, rpd: 264 }, isCooldown: true, cooldownRemainingMs: 45000, description: '20 RPM / 480 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: false, tools: false, completion: true },
    },
    {
      provider: 'scaleway', label: 'Scaleway', isAvailable: false, activeModels: 0, totalModels: 1, health: 'down',
      rateLimitRemaining: 0, avgLatencyMs: 0,
      models: [
        { id: 'llama-3.1-8b-instruct', tier: 'FAST', displayName: 'Llama 3.1 8B Instruct', health: 'down', capabilities: ['chat'] },
      ],
      keyStatus: { totalKeys: 0, healthyKeys: 0, hasAvailableKey: false, activeKeyMasked: null },
      rateLimits: { rpm: 0, rpd: 0, remaining: { rpm: 0, rpd: 0 }, isCooldown: false, cooldownRemainingMs: 0, description: 'Not configured' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: false, tools: false, completion: false },
    },
    {
      provider: 'dashscope', label: 'DashScope (Qwen)', isAvailable: true, activeModels: 1, totalModels: 1, health: 'healthy',
      rateLimitRemaining: 88, avgLatencyMs: 280,
      models: [
        { id: 'qwen-max', tier: 'MID', displayName: 'Qwen Max', health: 'healthy', capabilities: ['chat', 'code'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...ds' },
      rateLimits: { rpm: 20, rpd: 480, remaining: { rpm: 17, rpd: 422 }, isCooldown: false, cooldownRemainingMs: 0, description: '20 RPM / 480 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: true, tools: false, completion: true },
    },
    {
      provider: 'bitdeer', label: 'BitDeer AI', isAvailable: true, activeModels: 1, totalModels: 1, health: 'healthy',
      rateLimitRemaining: 92, avgLatencyMs: 350,
      models: [
        { id: 'deepseek-r1', tier: 'MID', displayName: 'DeepSeek R1', health: 'healthy', capabilities: ['chat', 'code'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...bd' },
      rateLimits: { rpm: 10, rpd: 240, remaining: { rpm: 9, rpd: 220 }, isCooldown: false, cooldownRemainingMs: 0, description: '10 RPM / 240 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: true, tools: false, completion: true },
    },
    {
      provider: 'nvidia', label: 'NVIDIA NIM Free', isAvailable: true, activeModels: 2, totalModels: 2, health: 'healthy',
      rateLimitRemaining: 70, avgLatencyMs: 156,
      models: [
        { id: 'llama-3.3-70b-instruct', tier: 'MID', displayName: 'Llama 3.3 70B Instruct', health: 'healthy', capabilities: ['chat', 'completion'] },
        { id: 'nemotron-4-340b-instruct', tier: 'PREMIUM', displayName: 'Nemotron 4 340B', health: 'healthy', capabilities: ['chat', 'code'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'nvapi-...nim' },
      rateLimits: { rpm: 40, rpd: 960, remaining: { rpm: 28, rpd: 672 }, isCooldown: false, cooldownRemainingMs: 0, description: '40 RPM / 960 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: true, tools: false, completion: true },
    },
    {
      provider: 'sambanova', label: 'SambaNova Free', isAvailable: true, activeModels: 1, totalModels: 1, health: 'healthy',
      rateLimitRemaining: 85, avgLatencyMs: 198,
      models: [
        { id: 'DeepSeek-V3', tier: 'MID', displayName: 'DeepSeek V3', health: 'healthy', capabilities: ['chat', 'code'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...smb' },
      rateLimits: { rpm: 20, rpd: 480, remaining: { rpm: 17, rpd: 408 }, isCooldown: false, cooldownRemainingMs: 0, description: '20 RPM / 480 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: true, tools: false, completion: true },
    },
    {
      provider: 'siliconflow', label: 'SiliconFlow Free', isAvailable: true, activeModels: 1, totalModels: 1, health: 'degraded',
      rateLimitRemaining: 40, avgLatencyMs: 380,
      models: [
        { id: 'deepseek-v3', tier: 'MID', displayName: 'DeepSeek V3 (SF)', health: 'degraded', capabilities: ['chat'] },
      ],
      keyStatus: { totalKeys: 1, healthyKeys: 1, hasAvailableKey: true, activeKeyMasked: 'sk-...sf' },
      rateLimits: { rpm: 10, rpd: 240, remaining: { rpm: 4, rpd: 96 }, isCooldown: true, cooldownRemainingMs: 30000, description: '10 RPM / 240 RPD' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: false, tools: false, completion: false },
    },
    {
      provider: 'opencode', label: 'OpenCode', isAvailable: false, activeModels: 0, totalModels: 1, health: 'down',
      rateLimitRemaining: 0, avgLatencyMs: 0,
      models: [
        { id: 'opencode-chat', tier: 'FAST', displayName: 'OpenCode Chat', health: 'down', capabilities: ['chat'] },
      ],
      keyStatus: { totalKeys: 0, healthyKeys: 0, hasAvailableKey: false, activeKeyMasked: null },
      rateLimits: { rpm: 0, rpd: 0, remaining: { rpm: 0, rpd: 0 }, isCooldown: false, cooldownRemainingMs: 0, description: 'Not configured' },
      costEstimate: { inputPer1k: 0, outputPer1k: 0, currency: 'USD', note: 'Free tier' },
      capabilities: { chat: true, vision: false, embedding: false, code: false, tools: false, completion: false },
    },
  ]

  return {
    providers,
    summary: {
      totalProviders: providers.length,
      availableProviders: providers.filter(p => p.isAvailable).length,
      totalModels: providers.reduce((sum, p) => sum + p.totalModels, 0),
      healthyModels: providers.reduce((sum, p) => sum + p.models.filter(m => m.health === 'healthy').length, 0),
    },
  }
}

// ─── Custom recharts tooltip ──────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border/50 bg-card px-3 py-2 shadow-xl text-xs">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-muted-foreground">
          <span className="inline-block h-2 w-2 rounded-full mr-1.5" style={{ backgroundColor: p.color }} />
          {p.name}: <span className="font-mono font-medium text-foreground">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

export function ProviderTab() {
  const [data, setData] = useState<ProvidersResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; latencyMs: number; error?: string }>>({})
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set())
  const [testingAll, setTestingAll] = useState(false)
  const [testingAllProgress, setTestingAllProgress] = useState(0)

  // Client-side data — no API call needed
  const loadProviders = useCallback(() => {
    setLoading(true)
    setError(null)
    // Simulate a small delay for UX, then use mock data
    setTimeout(() => {
      try {
        setData(getMockProviders())
      } catch {
        setError('Failed to load providers')
      } finally {
        setLoading(false)
      }
    }, 300)
  }, [])

  // Load on mount
  useEffect(() => {
    loadProviders()
  }, [loadProviders])

  const testConnection = useCallback(async (provider: string) => {
    setTestingProvider(provider)
    // Client-side data — no API call needed — simulated test result
    setTimeout(() => {
      const mockProvider = getMockProviders().providers.find(p => p.provider === provider)
      const isAvailable = mockProvider?.isAvailable ?? false
      const latency = mockProvider?.avgLatencyMs ?? -1
      setTestResults(prev => ({
        ...prev,
        [provider]: {
          success: isAvailable,
          latencyMs: isAvailable ? latency : -1,
          error: isAvailable ? undefined : 'Provider not available',
        },
      }))
      setTestingProvider(null)
    }, 800 + Math.random() * 1200)
  }, [])

  const testAllConnections = useCallback(async () => {
    if (!data?.providers) return
    setTestingAll(true)
    setTestingAllProgress(0)
    const providers = data.providers
    for (let i = 0; i < providers.length; i++) {
      await testConnection(providers[i].provider)
      setTestingAllProgress(Math.round(((i + 1) / providers.length) * 100))
    }
    setTestingAll(false)
  }, [data, testConnection])

  const toggleProvider = useCallback((provider: string) => {
    setExpandedProviders(prev => {
      const next = new Set(prev)
      if (next.has(provider)) {
        next.delete(provider)
      } else {
        next.add(provider)
      }
      return next
    })
  }, [])

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
            <Button size="sm" variant="outline" className="mt-3 gap-1.5" onClick={loadProviders}>
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

  // ─── Chart Data ────────────────────────────────────────────────────────

  // Latency Comparison data
  const latencyData = providers
    .filter(p => p.avgLatencyMs > 0)
    .map(p => ({
      name: p.label.length > 12 ? p.label.slice(0, 12) + '…' : p.label,
      latency: p.avgLatencyMs,
      health: p.health,
    }))
    .sort((a, b) => a.latency - b.latency)

  // Cost Analysis by tier
  const costTierMap: Record<string, number> = {}
  providers.forEach(p => {
    const tier = p.costEstimate.inputPer1k === 0 && p.costEstimate.outputPer1k === 0
      ? 'FREE'
      : p.costEstimate.inputPer1k <= 0.5 ? 'FREEMIUM' : 'PAID'
    costTierMap[tier] = (costTierMap[tier] || 0) + 1
  })
  const costPieData = Object.entries(costTierMap).map(([name, value]) => ({ name, value }))
  const COST_COLORS: Record<string, string> = { FREE: '#10b981', FREEMIUM: '#f59e0b', PAID: '#ef4444' }

  // Capabilities Matrix data
  const capColumns = ['chat', 'code', 'vision', 'tools', 'completion'] as const
  const capLabels: Record<string, string> = { chat: 'Chat', code: 'Code', vision: 'Vision', tools: 'Tools', completion: 'Streaming' }

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
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10"
            onClick={testAllConnections}
            disabled={testingAll}
          >
            {testingAll ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Testing... {testingAllProgress}%
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5" />
                Test All
              </>
            )}
          </Button>
          <Button size="sm" variant="outline" className="gap-1.5" onClick={loadProviders} disabled={loading}>
            <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Testing All Progress Bar */}
      <AnimatePresence>
        {testingAll && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Card className="bg-emerald-500/5 border-emerald-500/20">
              <CardContent className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Testing all providers...</span>
                  <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400">{testingAllProgress}%</span>
                </div>
                <Progress value={testingAllProgress} className="h-1.5" />
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Provider Health Overview Summary Card */}
      <Card className="bg-card/50 border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-transparent">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-sm font-semibold">Provider Health Overview</span>
            </div>
            <Badge variant="outline" className="text-[9px] bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 border-emerald-600/30">
              {Math.round((summary.healthyModels / Math.max(summary.totalModels, 1)) * 100)}% Healthy
            </Badge>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="bg-gradient-to-br from-emerald-600/10 to-transparent p-2.5 rounded-lg border border-emerald-600/20">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Active</div>
              <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{activeCount}</div>
            </div>
            <div className="bg-gradient-to-br from-yellow-600/10 to-transparent p-2.5 rounded-lg border border-yellow-600/20">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Warning</div>
              <div className="text-xl font-bold text-yellow-600 dark:text-yellow-400">{warningCount}</div>
            </div>
            <div className="bg-gradient-to-br from-red-600/10 to-transparent p-2.5 rounded-lg border border-red-600/20">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Inactive</div>
              <div className="text-xl font-bold text-red-600 dark:text-red-400">{inactiveCount}</div>
            </div>
            <div className="bg-gradient-to-br from-emerald-600/5 to-transparent p-2.5 rounded-lg border border-border/30">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Total Models</div>
              <div className="text-xl font-bold">{summary.totalModels}</div>
            </div>
            <div className="bg-gradient-to-br from-emerald-600/5 to-transparent p-2.5 rounded-lg border border-border/30">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Healthy Models</div>
              <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{summary.healthyModels}</div>
            </div>
          </div>
          <div className="mt-3 h-2 rounded-full bg-muted overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-emerald-500"
              initial={{ width: 0 }}
              animate={{ width: `${Math.round((summary.healthyModels / Math.max(summary.totalModels, 1)) * 100)}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </div>
          <div className="text-[9px] text-muted-foreground mt-1">{summary.healthyModels} of {summary.totalModels} models healthy across {providers.length} providers</div>
        </CardContent>
      </Card>

      {/* ─── Provider Health Grid ─────────────────────────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Grid3x3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Provider Health Grid
            <Badge variant="outline" className="text-[9px] ml-1">{providers.length} providers</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="flex flex-wrap gap-2">
            {providers.map((provider) => {
              const color = provider.isAvailable
                ? healthColorMap[provider.health] || 'bg-gray-400'
                : 'bg-red-500'
              const statusLabel = provider.isAvailable
                ? healthLabelMap[provider.health] || 'Unknown'
                : 'Inactive'
              return (
                <Tooltip key={provider.provider}>
                  <TooltipTrigger asChild>
                    <motion.div
                      whileHover={{ scale: 1.3 }}
                      className={cn(
                        'h-8 w-8 rounded-md cursor-pointer transition-shadow hover:shadow-lg',
                        color,
                        provider.health === 'degraded' && 'animate-pulse'
                      )}
                    />
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    <div className="text-xs">
                      <p className="font-semibold">{provider.label}</p>
                      <p className="text-muted-foreground">Status: {statusLabel}</p>
                      <p className="text-muted-foreground">Latency: {provider.avgLatencyMs > 0 ? `${provider.avgLatencyMs}ms` : 'N/A'}</p>
                      <p className="text-muted-foreground">Models: {provider.activeModels}/{provider.totalModels}</p>
                    </div>
                  </TooltipContent>
                </Tooltip>
              )
            })}
          </div>
          <div className="flex items-center gap-4 mt-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" /> Healthy</span>
            <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-yellow-500" /> Degraded</span>
            <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-red-500" /> Down/Inactive</span>
            <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-sm bg-gray-400" /> Unknown</span>
          </div>
        </CardContent>
      </Card>

      {/* ─── Charts Row: Latency Comparison + Cost Analysis ───────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Latency Comparison Bar Chart */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Latency Comparison
              <Badge variant="outline" className="text-[9px] ml-1">ms</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {latencyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={latencyData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }}
                    angle={-35}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                    tickFormatter={(v: number) => `${v}ms`}
                  />
                  <RechartsTooltip content={<CustomTooltip />} />
                  <Bar dataKey="latency" name="Latency" radius={[4, 4, 0, 0]} maxBarSize={32}>
                    {latencyData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.health === 'healthy' ? '#10b981' : entry.health === 'degraded' ? '#f59e0b' : '#ef4444'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[260px] flex items-center justify-center text-sm text-muted-foreground">
                No latency data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cost Analysis Pie Chart */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <PieChartIcon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Cost Distribution
              <Badge variant="outline" className="text-[9px] ml-1">by tier</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={costPieData}
                  cx="50%"
                  cy="45%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                  stroke="none"
                >
                  {costPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COST_COLORS[entry.name] || '#6b7280'} />
                  ))}
                </Pie>
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend
                  verticalAlign="bottom"
                  iconType="circle"
                  iconSize={8}
                  formatter={(value: string) => (
                    <span className="text-xs text-foreground">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* ─── Provider Capabilities Matrix ──────────────────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Provider Capabilities Matrix
            <Badge variant="outline" className="text-[9px] ml-1">{capColumns.length} capabilities</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/40">
                  <th className="text-left py-2 pr-3 text-muted-foreground font-medium min-w-[100px]">Provider</th>
                  {capColumns.map(cap => (
                    <th key={cap} className="text-center py-2 px-2 text-muted-foreground font-medium">
                      {capLabels[cap]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {providers.map((provider) => (
                  <tr key={provider.provider} className="border-b border-border/20 hover:bg-muted/30 transition-colors">
                    <td className="py-1.5 pr-3">
                      <div className="flex items-center gap-1.5">
                        <span className={cn('h-2 w-2 rounded-full shrink-0', healthColorMap[provider.health] || 'bg-gray-400')} />
                        <span className="font-medium truncate max-w-[90px]">{provider.label}</span>
                      </div>
                    </td>
                    {capColumns.map(cap => (
                      <td key={cap} className="text-center py-1.5 px-2">
                        {provider.capabilities[cap] ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mx-auto" />
                        ) : (
                          <XCircle className="h-3.5 w-3.5 text-muted-foreground/30 mx-auto" />
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ─── Provider Cards (Collapsible) ──────────────────────────────────── */}
      <div className="space-y-3">
        {providers.map((provider) => {
          const keyStatus = getKeyStatus(provider)
          const keyConfig = keyStatusConfig[keyStatus]
          const KeyIcon = keyConfig.icon
          const testResult = testResults[provider.provider]
          const isExpanded = expandedProviders.has(provider.provider)

          return (
            <Collapsible
              key={provider.provider}
              open={isExpanded}
              onOpenChange={() => toggleProvider(provider.provider)}
            >
              <Card className={cn(
                "bg-card/50 transition-all duration-200",
                // Gradient border based on status
                provider.health === 'healthy' && 'border-l-2 border-l-emerald-500 border-border/50',
                provider.health === 'degraded' && 'border-l-2 border-l-yellow-500 border-border/50 bg-gradient-to-r from-yellow-600/5 to-transparent',
                (provider.health === 'down' || !provider.isAvailable) && 'border-l-2 border-l-red-500 border-border/50 bg-gradient-to-r from-red-600/5 to-transparent',
                provider.health === 'unknown' && provider.isAvailable && 'border-l-2 border-l-gray-400 border-border/50',
                isExpanded && 'shadow-sm shadow-emerald-500/5'
              )}>
                <CardContent className="p-4">
                  {/* Summary Row (always visible) */}
                  <CollapsibleTrigger asChild>
                    <div className="flex items-center justify-between cursor-pointer select-none">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'h-2.5 w-2.5 rounded-full shrink-0',
                          healthColorMap[provider.health] || 'bg-gray-400',
                          !provider.isAvailable && 'bg-red-500'
                        )} />
                        <span className="text-sm font-bold">{provider.label}</span>
                        <Badge
                          variant="outline"
                          className={cn('text-[10px]', {
                            'border-emerald-600/30 text-emerald-600 dark:text-emerald-400 bg-emerald-600/5': provider.health === 'healthy',
                            'border-yellow-600/30 text-yellow-600 dark:text-yellow-400 bg-yellow-600/5': provider.health === 'degraded',
                            'border-red-600/30 text-red-600 dark:text-red-400 bg-red-600/5': provider.health === 'down' || (!provider.isAvailable && keyStatus === 'missing'),
                            'border-gray-600/30 text-gray-600 dark:text-gray-400 bg-gray-600/5': provider.health === 'unknown' && provider.isAvailable,
                          })}
                        >
                          {provider.isAvailable
                            ? provider.health === 'degraded' ? 'DEGRADED' : provider.health.toUpperCase()
                            : 'INACTIVE'}
                        </Badge>
                        <KeyIcon className={cn('h-4 w-4', keyConfig.color)} />
                        <span className={cn('text-xs', keyConfig.color)}>{keyConfig.label}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground">
                          {/* Latency bar indicator */}
                          {provider.avgLatencyMs > 0 && (
                            <span className="flex items-center gap-1.5">
                              <Gauge className="h-3 w-3" />
                              <div className="w-12 h-1.5 rounded-full bg-muted overflow-hidden">
                                <div className={cn(
                                  'h-full rounded-full',
                                  provider.avgLatencyMs < 100 ? 'bg-emerald-500' :
                                  provider.avgLatencyMs < 250 ? 'bg-yellow-500' : 'bg-red-500'
                                )} style={{ width: `${Math.min((provider.avgLatencyMs / 500) * 100, 100)}%` }} />
                              </div>
                              <span>{provider.avgLatencyMs}ms</span>
                            </span>
                          )}
                          <span className="flex items-center gap-1"><Server className="h-3 w-3" /> {provider.activeModels}/{provider.totalModels}</span>
                          <span className="flex items-center gap-1"><DollarSign className="h-3 w-3" /> {provider.costEstimate.inputPer1k === 0 && provider.costEstimate.outputPer1k === 0 ? 'FREE' : `$${provider.costEstimate.inputPer1k}/$${provider.costEstimate.outputPer1k}`}</span>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                    </div>
                  </CollapsibleTrigger>

                  {/* Expanded Details */}
                  <CollapsibleContent>
                    <div className="mt-4 space-y-3">
                      {/* Key Status & Models Row */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
                      <div>
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
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                          <AlertTriangle className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
                          <span className="text-[10px] text-yellow-600 dark:text-yellow-400">
                            Cooldown active — {Math.ceil(provider.rateLimits.cooldownRemainingMs / 1000)}s remaining
                          </span>
                        </div>
                      )}

                      {/* Models List */}
                      {provider.models && provider.models.length > 0 && (
                        <div>
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
                            onClick={(e) => { e.stopPropagation(); testConnection(provider.provider) }}
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
                    </div>
                  </CollapsibleContent>
                </CardContent>
              </Card>
            </Collapsible>
          )
        })}
      </div>
    </div>
  )
}
