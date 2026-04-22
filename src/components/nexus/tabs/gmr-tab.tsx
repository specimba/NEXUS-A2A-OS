'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'
import { useApiData } from '@/hooks/use-api-data'
import { Activity, Zap, Wifi, WifiOff, RefreshCw, Gauge, RotateCcw, ArrowRightLeft, AlertTriangle, TrendingUp, TrendingDown, BarChart3, HeartPulse, Play, Clock, Hash, CheckCircle2, XCircle, Loader2, Terminal, Trash2, Timer, ListOrdered, ShieldCheck, Ban, CircleDot, Signal, Hourglass, Rocket, Cpu, Eye, Server, ChevronRight, Sparkles, ArrowRight, Send, MessageSquare, Braces, Lightbulb } from 'lucide-react'
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

// ── AI Provider Bridge Mock Data ─────────────────────────────────
interface ProviderRoute {
  id: string
  tier: 'reasoning' | 'balanced' | 'fast' | 'free'
  displayName: string
  actualModel: string
  provider: string
  providerLabel: string
  isFree: boolean
  rateLimitPerMin: number
  contextWindow: number
  capabilities: string[]
  health: 'healthy' | 'degraded' | 'down'
  latencyMs: number
  totalCalls: number
  successRate: number
  fallbackModel?: string
  fallbackProvider?: string
}

interface ProviderInfo {
  provider: string
  label: string
  isAvailable: boolean
  activeModels: number
  totalModels: number
  health: 'healthy' | 'degraded' | 'down'
  rateLimitRemaining: number
  avgLatencyMs: number
}

interface BridgeData {
  routes: ProviderRoute[]
  providers: ProviderInfo[]
}

const MOCK_BRIDGE_DATA: BridgeData = {
  routes: [
    {
      id: 'reasoning-1',
      tier: 'reasoning',
      displayName: 'GLM-4.7 (NIM Free)',
      actualModel: 'z-ai/glm-4.7',
      provider: 'z-ai',
      providerLabel: 'z-ai SDK',
      isFree: true,
      rateLimitPerMin: 40,
      contextWindow: 131072,
      capabilities: ['code', 'reasoning', 'tools'],
      health: 'healthy',
      latencyMs: 1200,
      totalCalls: 342,
      successRate: 97.2,
      fallbackModel: 'DeepSeek-R1-0528 (OpenRouter)',
      fallbackProvider: 'openrouter',
    },
    {
      id: 'balanced-1',
      tier: 'balanced',
      displayName: 'Qwen3-Coder (z-ai)',
      actualModel: 'z-ai/qwen3-coder',
      provider: 'z-ai',
      providerLabel: 'z-ai SDK',
      isFree: true,
      rateLimitPerMin: 40,
      contextWindow: 131072,
      capabilities: ['code', 'analysis', 'chat'],
      health: 'healthy',
      latencyMs: 890,
      totalCalls: 1287,
      successRate: 98.1,
      fallbackModel: 'GLM-4.7 (NIM Free)',
      fallbackProvider: 'z-ai',
    },
    {
      id: 'fast-1',
      tier: 'fast',
      displayName: 'Gemma-3-27B (NIM Free)',
      actualModel: 'nvidia/gemma-3-27b',
      provider: 'nvidia',
      providerLabel: 'NVIDIA NIM Free',
      isFree: true,
      rateLimitPerMin: 40,
      contextWindow: 131072,
      capabilities: ['chat', 'code', 'fast'],
      health: 'healthy',
      latencyMs: 340,
      totalCalls: 2841,
      successRate: 99.3,
      fallbackModel: 'Qwen3-Coder (z-ai)',
      fallbackProvider: 'z-ai',
    },
    {
      id: 'free-1',
      tier: 'free',
      displayName: 'DeepSeek-V3 (OpenRouter Free)',
      actualModel: 'openrouter/deepseek/deepseek-chat-v3-0324:free',
      provider: 'openrouter',
      providerLabel: 'OpenRouter Free',
      isFree: true,
      rateLimitPerMin: 20,
      contextWindow: 65536,
      capabilities: ['chat', 'code'],
      health: 'degraded',
      latencyMs: 2100,
      totalCalls: 856,
      successRate: 92.4,
      fallbackModel: 'Gemma-3-27B (NIM Free)',
      fallbackProvider: 'nvidia',
    },
  ],
  providers: [
    {
      provider: 'z-ai',
      label: 'z-ai SDK',
      isAvailable: true,
      activeModels: 2,
      totalModels: 2,
      health: 'healthy',
      rateLimitRemaining: 35,
      avgLatencyMs: 1100,
    },
    {
      provider: 'nvidia',
      label: 'NVIDIA NIM Free',
      isAvailable: true,
      activeModels: 1,
      totalModels: 1,
      health: 'healthy',
      rateLimitRemaining: 38,
      avgLatencyMs: 340,
    },
    {
      provider: 'openrouter',
      label: 'OpenRouter Free',
      isAvailable: true,
      activeModels: 1,
      totalModels: 1,
      health: 'degraded',
      rateLimitRemaining: 18,
      avgLatencyMs: 2100,
    },
  ],
}

const TIER_CONFIG: Record<string, { icon: string; label: string; color: string; gradient: string; borderColor: string; textColor: string; bgColor: string }> = {
  reasoning: {
    icon: '🧠',
    label: 'Reasoning',
    color: '#a78bfa',
    gradient: 'from-purple-600/10',
    borderColor: 'border-purple-600/20',
    textColor: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-600/15',
  },
  balanced: {
    icon: '⚖️',
    label: 'Balanced',
    color: '#3b82f6',
    gradient: 'from-blue-600/10',
    borderColor: 'border-blue-600/20',
    textColor: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-600/15',
  },
  fast: {
    icon: '⚡',
    label: 'Fast',
    color: '#f59e0b',
    gradient: 'from-amber-600/10',
    borderColor: 'border-amber-600/20',
    textColor: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-600/15',
  },
  free: {
    icon: '🆓',
    label: 'Free',
    color: '#34d399',
    gradient: 'from-emerald-600/10',
    borderColor: 'border-emerald-600/20',
    textColor: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-600/15',
  },
}

const OPTIMIZATION_STATS = [
  { category: 'Quota Checks', count: 1247, saved: '~4.2k calls', icon: ShieldCheck },
  { category: 'Title Generation', count: 892, saved: '~2.1k calls', icon: Braces },
  { category: 'Prefix Detection', count: 3451, saved: '~8.7k calls', icon: Eye },
  { category: 'Suggestion Mode', count: 623, saved: '~1.5k calls', icon: Lightbulb },
]

// ── Rate Limit Constants ────────────────────────────────────────
const RATE_LIMIT_THRESHOLD = 8 // max calls per minute for z-ai-sdk
const MIN_CALL_DELAY_MS = 2000 // minimum 2-second delay between API calls

const latencyHistory = [
  { name: '10m', qwen: 1200, trinity: 1350, gemma: 340 },
  { name: '8m', qwen: 1180, trinity: 1290, gemma: 350 },
  { name: '6m', qwen: 1240, trinity: 1410, gemma: 330 },
  { name: '4m', qwen: 1190, trinity: 1320, gemma: 360 },
  { name: '2m', qwen: 1210, trinity: 1380, gemma: 345 },
  { name: 'now', qwen: 1200, trinity: 1350, gemma: 340 },
]

// Failover log data
const failoverLog = [
  { time: '14:22:45', from: 'gemma-fast', to: 'qwen3-coder', reason: 'Health fallback: 88%', severity: 'warning' },
  { time: '14:20:55', from: 'gemma-fast', to: 'kimi-k2.5', reason: 'Health fallback: 88%', severity: 'warning' },
  { time: '14:20:12', from: 'nemotron-3-super', to: 'gpt-oss-120b', reason: 'Rate limit backoff', severity: 'info' },
  { time: '13:58:30', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Latency spike: 2400ms', severity: 'warning' },
  { time: '13:45:12', from: 'dolphin-mistral-venice', to: 'trinity-large-preview', reason: 'Model disabled by admin', severity: 'critical' },
]

// Rotation analytics data
const rotationAnalytics = {
  mostRotatedTo: [
    { model: 'trinity-large-preview', count: 23 },
    { model: 'qwen3-coder', count: 18 },
    { model: 'kimi-k2.5', count: 12 },
  ],
  mostRotatedFrom: [
    { model: 'gemma-fast', count: 19 },
    { model: 'dolphin-mistral-venice', count: 15 },
    { model: 'nemotron-3-super', count: 11 },
  ],
}

// Generate per-model sparkline data based on model health from DB
// Uses a seeded pseudo-random function for consistent variation around health value
function generateSparkline(health: number, seed: number): { name: string; value: number }[] {
  const points = 6
  return Array.from({ length: points }, (_, i) => {
    const variation = Math.sin(seed * (i + 1) * 7.3) * 4
    return { name: String(i + 1), value: Math.round(Math.min(100, Math.max(50, health + variation))) }
  })
}

function getModelSparklines(models: ModelData[]): Record<string, { name: string; value: number }[]> {
  const result: Record<string, { name: string; value: number }[]> = {}
  models.forEach((m, idx) => {
    result[m.name] = generateSparkline(m.health, idx + 1)
  })
  return result
}

const poolDefinitions = [
  {
    name: 'PREMIUM',
    desc: 'Tier 90+ · Complex reasoning & security',
    modelNames: ['trinity-large-preview', 'minimax-m2.5'],
    tierRange: '90+',
    color: COLORS.emerald,
    gradient: 'from-emerald-600/10',
  },
  {
    name: 'MID',
    desc: 'Tier 60-89 · Code & research',
    modelNames: ['qwen3-coder', 'kimi-k2.5', 'gpt-oss-120b'],
    tierRange: '60-89',
    color: COLORS.blue,
    gradient: 'from-blue-600/10',
  },
  {
    name: 'FAST',
    desc: 'Tier <60 · Quick responses',
    modelNames: ['gemma-fast', 'nemotron-3-super'],
    tierRange: '<60',
    color: COLORS.orange,
    gradient: 'from-orange-600/10',
  },
  {
    name: 'FREE_RESEARCH',
    desc: 'StressLab + heretic control group',
    modelNames: ['dolphin-mistral-venice', 'qwen3-coder', 'trinity-large-preview'],
    tierRange: 'any',
    color: COLORS.purple,
    gradient: 'from-purple-600/10',
  },
]

const rotationLog = [
  { time: '14:23:01', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Domain: reason', tokens: 0 },
  { time: '14:22:45', from: 'gemma-fast', to: 'qwen3-coder', reason: 'Domain: code', tokens: 340 },
  { time: '14:22:12', from: '-', to: 'gemma-fast', reason: 'New request: fast', tokens: 340 },
  { time: '14:21:58', from: 'trinity-large-preview', to: 'nemotron-3-super', reason: 'Domain: research', tokens: 1280 },
  { time: '14:21:30', from: 'qwen3-coder', to: 'trinity-large-preview', reason: 'Escalation: sec domain', tokens: 890 },
  { time: '14:20:55', from: 'gemma-fast', to: 'kimi-k2.5', reason: 'Health fallback: 88%', tokens: 450 },
  { time: '14:20:12', from: 'nemotron-3-super', to: 'gpt-oss-120b', reason: 'Rate limit backoff', tokens: 220 },
  { time: '14:19:45', from: 'trinity-large-preview', to: 'minimax-m2.5', reason: 'Domain: general', tokens: 560 },
]

interface ModelData {
  id: string
  name: string
  provider: string
  tier: number
  domain: string
  health: number
  latencyMs: number
  isFree: boolean
  isActive: boolean
  totalCalls: number
  successRate: number
}

// ── Test Console Types ──────────────────────────────────────────
type TestType = 'simple' | 'reasoning' | 'code' | 'json' | 'domain'

interface TestResult {
  id: string
  model: string
  testType: TestType
  prompt: string
  response: string
  responseTimeMs: number
  tokenCount: number
  qualityScore: number
  passed: boolean
  timestamp: Date
}

const testTypeConfig: Record<TestType, { label: string; description: string; defaultPrompt: string }> = {
  simple: {
    label: 'Simple',
    description: 'Basic Q&A response test',
    defaultPrompt: 'What is the capital of France? Answer in one sentence.',
  },
  reasoning: {
    label: 'Reasoning',
    description: 'Logical reasoning & analysis',
    defaultPrompt: 'If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly? Explain your reasoning step by step.',
  },
  code: {
    label: 'Code',
    description: 'Code generation test',
    defaultPrompt: 'Write a TypeScript function that takes an array of numbers and returns the median value. Handle edge cases for empty arrays and even-length arrays.',
  },
  json: {
    label: 'JSON',
    description: 'Structured JSON output',
    defaultPrompt: 'Return a JSON object with exactly these fields: {"status": "ok", "timestamp": current ISO string, "items": array of 3 random color names, "count": number of items}. Return ONLY valid JSON, no markdown.',
  },
  domain: {
    label: 'Domain',
    description: 'Domain-specific knowledge',
    defaultPrompt: 'Explain the difference between HMAC and RSA signatures for API authentication. What are the trade-offs in terms of security, performance, and key management?',
  },
}

// Quality scoring heuristics
function scoreResponse(response: string, testType: TestType, responseTimeMs: number): { score: number; passed: boolean; details: string[] } {
  const details: string[] = []
  let score = 0

  // Response time scoring (0-25 points)
  if (responseTimeMs < 2000) { score += 25; details.push('Fast response (<2s)') }
  else if (responseTimeMs < 5000) { score += 18; details.push('Acceptable response time (<5s)') }
  else if (responseTimeMs < 10000) { score += 10; details.push('Slow response (<10s)') }
  else { score += 3; details.push('Very slow response (>10s)') }

  // Length scoring (0-25 points)
  const wordCount = response.split(/\s+/).length
  if (testType === 'simple') {
    if (wordCount >= 5 && wordCount <= 50) { score += 25; details.push('Concise answer') }
    else if (wordCount > 50) { score += 15; details.push('Verbose for simple question') }
    else { score += 5; details.push('Very short response') }
  } else {
    if (wordCount >= 30) { score += 25; details.push('Substantial response') }
    else if (wordCount >= 10) { score += 15; details.push('Adequate length') }
    else { score += 5; details.push('Short response') }
  }

  // Type-specific scoring (0-25 points)
  if (testType === 'json') {
    try {
      JSON.parse(response)
      score += 25
      details.push('Valid JSON output')
    } catch {
      // Try to extract JSON from response
      const jsonMatch = response.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        try {
          JSON.parse(jsonMatch[0])
          score += 18
          details.push('JSON found in response (with extra text)')
        } catch {
          score += 5
          details.push('Invalid JSON structure')
        }
      } else {
        score += 2
        details.push('No JSON found in response')
      }
    }
  } else if (testType === 'code') {
    if (/function|const|let|=>|return/.test(response)) { score += 25; details.push('Code syntax detected') }
    else if (/\{|\}|=|;/.test(response)) { score += 15; details.push('Partial code structure') }
    else { score += 5; details.push('No code structure detected') }
  } else if (testType === 'reasoning') {
    if (/because|therefore|thus|since|however/i.test(response)) { score += 25; details.push('Logical connectors found') }
    else if (/step|first|second|then/i.test(response)) { score += 15; details.push('Step-by-step reasoning') }
    else { score += 8; details.push('Limited reasoning structure') }
  } else {
    // simple/domain — check for relevant content
    if (wordCount >= 10) { score += 20; details.push('Informative response') }
    else { score += 10; details.push('Brief response') }
  }

  // Basic validation (0-25 points)
  if (response.length > 0 && !/^(error|failed|sorry)/i.test(response.trim())) {
    score += 20
    details.push('No error indicators')
  } else {
    score += 0
    details.push('Response contains error indicators')
  }

  // Bonus for no repetition
  const uniqueWords = new Set(response.toLowerCase().split(/\s+/)).size
  const diversity = uniqueWords / Math.max(wordCount, 1)
  if (diversity > 0.6) { score += 5; details.push('Good vocabulary diversity') }

  score = Math.min(100, Math.max(0, score))
  return { score, passed: score >= 50, details }
}

// ── Rate Limit Dashboard Component ─────────────────────────────
function RateLimitDashboard({ apiCallTimestamps, lastCallTime }: {
  apiCallTimestamps: number[]
  lastCallTime: number | null
}) {
  const [now, setNow] = useState(0)

  // Tick every 200ms for smooth countdown — start from 0 on SSR, first rAF sets real time
  useEffect(() => {
    const raf = requestAnimationFrame(() => setNow(Date.now()))
    const interval = setInterval(() => setNow(Date.now()), 200)
    return () => {
      cancelAnimationFrame(raf)
      clearInterval(interval)
    }
  }, [])

  // Calculate calls in the last 60 seconds
  const callsInLastMinute = useMemo(() => {
    const cutoff = now - 60000
    return apiCallTimestamps.filter(t => t > cutoff).length
  }, [apiCallTimestamps, now])

  const ratePercent = Math.min(100, (callsInLastMinute / RATE_LIMIT_THRESHOLD) * 100)

  // Calculate backoff time remaining
  const backoffRemaining = useMemo(() => {
    if (!lastCallTime) return 0
    const elapsed = now - lastCallTime
    return Math.max(0, MIN_CALL_DELAY_MS - elapsed)
  }, [lastCallTime, now])

  // Color coding: green (<5), yellow (5-7), red (8+)
  const statusColor = callsInLastMinute >= RATE_LIMIT_THRESHOLD
    ? 'red'
    : callsInLastMinute >= 5
      ? 'yellow'
      : 'emerald'

  const statusLabel = callsInLastMinute >= RATE_LIMIT_THRESHOLD
    ? 'RATE LIMITED'
    : callsInLastMinute >= 5
      ? 'CAUTION'
      : 'SAFE'

  const barColorClass = statusColor === 'red'
    ? 'bg-red-500'
    : statusColor === 'yellow'
      ? 'bg-yellow-500'
      : 'bg-emerald-500'

  const textColorClass = statusColor === 'red'
    ? 'text-red-600 dark:text-red-400'
    : statusColor === 'yellow'
      ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-emerald-600 dark:text-emerald-400'

  const glowClass = statusColor === 'red'
    ? 'shadow-red-500/20'
    : statusColor === 'yellow'
      ? 'shadow-yellow-500/20'
      : 'shadow-emerald-500/20'

  return (
    <Card className={`relative overflow-hidden border-${statusColor === 'red' ? 'red' : statusColor === 'yellow' ? 'yellow' : 'emerald'}-600/20 hover-lift shadow-lg ${glowClass}`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${
        statusColor === 'red' ? 'from-red-600/8' : statusColor === 'yellow' ? 'from-yellow-600/8' : 'from-emerald-600/8'
      } via-transparent to-transparent`} />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Signal className={`h-4 w-4 ${textColorClass}`} />
            Rate Limit Dashboard
          </CardTitle>
          <Badge className={`border-0 text-[9px] px-2 ${
            statusColor === 'red' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
            statusColor === 'yellow' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
            'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
          }`}>
            {statusLabel}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-4">
        <div className="grid grid-cols-3 gap-4">
          {/* Current Rate */}
          <div className="rounded-lg bg-accent/30 p-3 text-center">
            <Signal className={`h-4 w-4 ${textColorClass} mx-auto mb-1`} />
            <p className={`text-2xl font-bold tabular-nums ${textColorClass}`}>{callsInLastMinute}</p>
            <p className="text-[9px] text-muted-foreground">calls/min</p>
          </div>
          {/* Threshold */}
          <div className="rounded-lg bg-accent/30 p-3 text-center">
            <ShieldCheck className="h-4 w-4 text-blue-600 dark:text-blue-400 mx-auto mb-1" />
            <p className="text-2xl font-bold tabular-nums text-blue-600 dark:text-blue-400">{RATE_LIMIT_THRESHOLD}</p>
            <p className="text-[9px] text-muted-foreground">rpm limit</p>
          </div>
          {/* Backoff Timer */}
          <div className="rounded-lg bg-accent/30 p-3 text-center">
            <Hourglass className={`h-4 w-4 ${backoffRemaining > 0 ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'} mx-auto mb-1`} />
            <p className={`text-2xl font-bold tabular-nums ${backoffRemaining > 0 ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
              {backoffRemaining > 0 ? `${(backoffRemaining / 1000).toFixed(1)}s` : '0.0s'}
            </p>
            <p className="text-[9px] text-muted-foreground">backoff</p>
          </div>
        </div>

        {/* Rate Progress Bar */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-medium text-muted-foreground">API Call Rate</span>
            <span className={`text-[10px] font-bold tabular-nums ${textColorClass}`}>{callsInLastMinute}/{RATE_LIMIT_THRESHOLD} rpm</span>
          </div>
          <div className="relative h-3 rounded-full bg-muted/30 overflow-hidden">
            {/* Threshold marker */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-red-400/60 z-10"
              style={{ left: '100%' }}
            />
            <div
              className={`h-full rounded-full transition-all duration-500 ${barColorClass}`}
              style={{ width: `${ratePercent}%`, opacity: 0.8 }}
            />
          </div>
          {/* Zone indicators */}
          <div className="flex justify-between mt-1 text-[8px] text-muted-foreground">
            <span className="text-emerald-600 dark:text-emerald-400">Safe (0-4)</span>
            <span className="text-yellow-600 dark:text-yellow-400">Caution (5-7)</span>
            <span className="text-red-600 dark:text-red-400">Limited (8+)</span>
          </div>
        </div>

        {/* Can Call Indicator */}
        <div className={`flex items-center gap-2 rounded-md px-3 py-2 text-xs ${
          backoffRemaining > 0
            ? 'bg-yellow-600/10 border border-yellow-600/20 text-yellow-600 dark:text-yellow-400'
            : callsInLastMinute >= RATE_LIMIT_THRESHOLD
              ? 'bg-red-600/10 border border-red-600/20 text-red-600 dark:text-red-400'
              : 'bg-emerald-600/10 border border-emerald-600/20 text-emerald-600 dark:text-emerald-400'
        }`}>
          {backoffRemaining > 0 ? (
            <>
              <Hourglass className="h-3.5 w-3.5 animate-pulse" />
              <span>Backoff active — {(backoffRemaining / 1000).toFixed(1)}s until next call allowed</span>
            </>
          ) : callsInLastMinute >= RATE_LIMIT_THRESHOLD ? (
            <>
              <Ban className="h-3.5 w-3.5" />
              <span>Rate limit reached — wait before making more calls</span>
            </>
          ) : (
            <>
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Ready — {RATE_LIMIT_THRESHOLD - callsInLastMinute} calls remaining this minute</span>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// Pool Health Overview Component - compact horizontal stacked bar
function PoolHealthOverview({ models }: { models: ModelData[] }) {
  const poolHealthData = useMemo(() => {
    return poolDefinitions.map(pool => {
      const poolModels = models.filter(m => pool.modelNames.includes(m.name))
      const activeCount = poolModels.filter(m => m.isActive).length
      const totalHealth = poolModels.reduce((s, m) => s + m.health, 0)
      const avgHealth = poolModels.length ? Math.round(totalHealth / poolModels.length) : 0
      return {
        name: pool.name,
        color: pool.color,
        total: poolModels.length,
        active: activeCount,
        avgHealth,
        segments: poolModels.map(m => ({
          name: m.name.split('-')[0].substring(0, 8),
          health: m.health,
          active: m.isActive,
        })),
      }
    })
  }, [models])

  return (
    <Card className="relative overflow-hidden border-emerald-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          Pool Health Overview
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-3">
        {poolHealthData.map((pool) => (
          <div key={pool.name}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: pool.color }} />
                <span className="text-xs font-medium">{pool.name}</span>
                <span className="text-[10px] text-muted-foreground">{pool.active}/{pool.total} active</span>
              </div>
              <span className={`text-[10px] font-bold tabular-nums ${
                pool.avgHealth >= 95 ? 'text-emerald-600 dark:text-emerald-400' :
                pool.avgHealth >= 85 ? 'text-yellow-600 dark:text-yellow-400' :
                'text-red-600 dark:text-red-400'
              }`}>{pool.avgHealth}% avg</span>
            </div>
            {/* Horizontal stacked bar */}
            <div className="flex h-4 rounded-full overflow-hidden bg-muted/30">
              {pool.segments.map((seg, i) => (
                <div
                  key={`${pool.name}-${seg.name}-${i}`}
                  className={`h-full flex items-center justify-center text-[8px] font-bold transition-all duration-300 ${
                    !seg.active ? 'opacity-30' : ''
                  } ${i === 0 ? 'rounded-l-full' : ''} ${i === pool.segments.length - 1 ? 'rounded-r-full' : ''}`}
                  style={{
                    width: `${100 / pool.segments.length}%`,
                    backgroundColor: seg.active
                      ? (seg.health >= 95 ? '#34d399' : seg.health >= 85 ? '#facc15' : '#f87171')
                      : '#6b7280',
                    opacity: seg.active ? 0.7 : 0.2,
                  }}
                >
                  {seg.health}%
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// Rotation Analytics Component
function RotationAnalyticsCard() {
  return (
    <Card className="relative overflow-hidden border-blue-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <ArrowRightLeft className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          Rotation Analytics
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="grid grid-cols-2 gap-4">
          {/* Most Rotated To */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
              <span className="text-[10px] font-medium uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Most Rotated To</span>
            </div>
            <div className="space-y-1.5">
              {rotationAnalytics.mostRotatedTo.map((item, i) => (
                <div key={item.model} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-600/10 text-[9px] font-bold text-emerald-600 dark:text-emerald-400">
                    {i + 1}
                  </span>
                  <span className="text-xs truncate flex-1">{item.model.split('-')[0]}</span>
                  <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Most Rotated From */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingDown className="h-3 w-3 text-red-600 dark:text-red-400" />
              <span className="text-[10px] font-medium uppercase tracking-wider text-red-600 dark:text-red-400">Most Rotated From</span>
            </div>
            <div className="space-y-1.5">
              {rotationAnalytics.mostRotatedFrom.map((item, i) => (
                <div key={item.model} className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-600/10 text-[9px] font-bold text-red-600 dark:text-red-400">
                    {i + 1}
                  </span>
                  <span className="text-xs truncate flex-1">{item.model.split('-')[0]}</span>
                  <span className="text-[10px] font-bold text-red-600 dark:text-red-400 tabular-nums">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Failover Log Component
function FailoverLogCard() {
  return (
    <Card className="relative overflow-hidden border-red-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-red-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
            Failover Log
          </CardTitle>
          <Badge variant="outline" className="text-[9px]">{failoverLog.length} events</Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-3 pt-0">
        <div className="max-h-48 space-y-1.5 overflow-y-auto custom-scrollbar">
          {failoverLog.map((entry, i) => (
            <div
              key={`failover-${i}`}
              className="flex items-center gap-2 rounded-md bg-accent/20 px-2.5 py-2 text-xs hover:bg-accent/40 transition-colors"
            >
              <span className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">{entry.time}</span>
              <Badge className={`shrink-0 border-0 text-[8px] px-1.5 py-0 ${
                entry.severity === 'critical' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                entry.severity === 'warning' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
                'bg-blue-600/15 text-blue-600 dark:text-blue-400'
              }`}>
                {entry.severity === 'critical' ? 'CRIT' : entry.severity === 'warning' ? 'WARN' : 'INFO'}
              </Badge>
              <span className="text-muted-foreground shrink-0">{entry.from.split('-')[0]}</span>
              <span className="text-emerald-600 dark:text-emerald-400">→</span>
              <span className="truncate">{entry.to.split('-')[0]}</span>
              <span className="ml-auto text-[10px] text-muted-foreground/60 shrink-0 truncate max-w-[120px]">{entry.reason}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Model Performance Comparison Card with grouped bar chart
function ModelPerformanceComparison({ models }: { models: ModelData[] }) {
  const chartData = useMemo(() => {
    return models.map(m => ({
      name: m.name.split('-')[0].substring(0, 8),
      health: Math.round(m.health),
      successRate: Math.round(m.successRate),
      latency: Math.round(Math.max(0, 100 - (m.latencyMs / 50))),
    }))
  }, [models])

  return (
    <Card className="relative overflow-hidden border-purple-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-purple-600 dark:text-purple-400" />
          Model Performance Comparison
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="h-[180px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} domain={[0, 100]} />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '11px',
                  color: 'hsl(var(--foreground))',
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
                itemStyle={{ color: 'hsl(var(--muted-foreground))' }}
                formatter={(value: number, name: string) => [`${value}%`, name]}
              />
              <Legend wrapperStyle={{ fontSize: '10px', color: 'hsl(var(--muted-foreground))' }} iconType="circle" iconSize={8} />
              <Bar dataKey="health" name="Health" fill={COLORS.emerald} fillOpacity={0.7} radius={[2, 2, 0, 0]} />
              <Bar dataKey="successRate" name="Success" fill={COLORS.blue} fillOpacity={0.7} radius={[2, 2, 0, 0]} />
              <Bar dataKey="latency" name="Latency Score" fill={COLORS.orange} fillOpacity={0.7} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Model Test Console Component ────────────────────────────────
function ModelTestConsole({ models }: { models: ModelData[] }) {
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [testType, setTestType] = useState<TestType>('simple')
  const [prompt, setPrompt] = useState(testTypeConfig.simple.defaultPrompt)
  const [running, setRunning] = useState(false)
  const [currentResult, setCurrentResult] = useState<TestResult | null>(null)
  const [testHistory, setTestHistory] = useState<TestResult[]>([])
  const [error, setError] = useState<string | null>(null)

  // Update prompt when test type changes
  const handleTestTypeChange = useCallback((type: TestType) => {
    setTestType(type)
    setPrompt(testTypeConfig[type].defaultPrompt)
  }, [])

  // Run the test
  const runTest = useCallback(async () => {
    if (!selectedModel) {
      toast.error('Please select a model first')
      return
    }
    if (!prompt.trim()) {
      toast.error('Please enter a prompt')
      return
    }

    setRunning(true)
    setError(null)
    setCurrentResult(null)

    const startTime = Date.now()

    try {
      const res = await globalThis.fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: prompt }],
          systemPrompt: `You are being tested. Respond to the following prompt as accurately and helpfully as possible. ${testType === 'json' ? 'Return ONLY valid JSON with no markdown formatting.' : ''} ${testType === 'code' ? 'Return working code with proper syntax.' : ''}`,
        }),
      })

      const responseTimeMs = Date.now() - startTime

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.error || `HTTP ${res.status}`)
      }

      const data = await res.json()
      const responseText = data.response || ''
      const tokenCount = responseText.split(/\s+/).length * 1.3 // rough estimate

      const { score, passed, details } = scoreResponse(responseText, testType, responseTimeMs)

      const result: TestResult = {
        id: `TEST-${Date.now()}`,
        model: selectedModel,
        testType,
        prompt,
        response: responseText,
        responseTimeMs,
        tokenCount: Math.round(tokenCount),
        qualityScore: score,
        passed,
        timestamp: new Date(),
      }

      setCurrentResult(result)
      setTestHistory(prev => [result, ...prev].slice(0, 20)) // Keep last 20
      toast[passed ? 'success' : 'warning'](
        passed ? 'Test passed' : 'Test needs improvement',
        { description: `Quality score: ${score}/100 · ${responseTimeMs}ms` }
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      toast.error('Test failed', { description: msg })
    } finally {
      setRunning(false)
    }
  }, [selectedModel, testType, prompt])

  const activeModels = models.filter(m => m.isActive)

  return (
    <div className="space-y-4">
      {/* Test Configuration */}
      <Card className="relative overflow-hidden border-emerald-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Terminal className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Test Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground">Model</Label>
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue placeholder="Select a model..." />
                </SelectTrigger>
                <SelectContent>
                  {activeModels.map(m => (
                    <SelectItem key={m.id} value={m.name}>
                      {m.name} (Tier {m.tier})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground">Test Type</Label>
              <Select value={testType} onValueChange={(v) => handleTestTypeChange(v as TestType)}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.entries(testTypeConfig) as [TestType, typeof testTypeConfig.simple][]).map(([key, cfg]) => (
                    <SelectItem key={key} value={key}>
                      {cfg.label} — {cfg.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Prompt</Label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Enter your test prompt..."
              rows={3}
              className="text-xs resize-none"
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={runTest}
              disabled={running || !selectedModel}
              className="bg-emerald-600 hover:bg-emerald-700 gap-2"
              size="sm"
            >
              {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              {running ? 'Running Test...' : 'Run Test'}
            </Button>
            {running && (
              <span className="text-xs text-muted-foreground animate-pulse">
                Sending prompt to {selectedModel}...
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Current Result */}
      {(currentResult || error) && (
        <Card className={`relative overflow-hidden ${error ? 'border-red-600/20' : currentResult?.passed ? 'border-emerald-600/20' : 'border-yellow-600/20'}`}>
          <div className={`absolute inset-0 bg-gradient-to-br ${
            error ? 'from-red-600/5' : currentResult?.passed ? 'from-emerald-600/5' : 'from-yellow-600/5'
          } via-transparent to-transparent`} />
          <CardHeader className="relative pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                {error ? (
                  <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                ) : currentResult?.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                )}
                Test Result
              </CardTitle>
              {currentResult && (
                <div className="flex items-center gap-2">
                  <Badge className={`border-0 text-[10px] ${currentResult.passed ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' : 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'}`}>
                    {currentResult.passed ? 'PASSED' : 'NEEDS WORK'}
                  </Badge>
                  <Badge variant="outline" className="text-[9px]">{currentResult.model}</Badge>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="relative p-4 pt-0 space-y-3">
            {error && (
              <div className="rounded-md bg-red-600/10 border border-red-600/20 px-3 py-2 text-xs text-red-600 dark:text-red-400">
                {error}
              </div>
            )}
            {currentResult && (
              <>
                {/* Metrics */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg bg-accent/30 p-2.5 text-center">
                    <Clock className="h-3 w-3 text-blue-600 dark:text-blue-400 mx-auto mb-1" />
                    <p className="text-lg font-bold tabular-nums">{currentResult.responseTimeMs.toLocaleString()}ms</p>
                    <p className="text-[9px] text-muted-foreground">Response Time</p>
                  </div>
                  <div className="rounded-lg bg-accent/30 p-2.5 text-center">
                    <Hash className="h-3 w-3 text-orange-600 dark:text-orange-400 mx-auto mb-1" />
                    <p className="text-lg font-bold tabular-nums">~{currentResult.tokenCount}</p>
                    <p className="text-[9px] text-muted-foreground">Token Count</p>
                  </div>
                  <div className="rounded-lg bg-accent/30 p-2.5 text-center">
                    <Activity className="h-3 w-3 text-emerald-600 dark:text-emerald-400 mx-auto mb-1" />
                    <p className={`text-lg font-bold tabular-nums ${currentResult.qualityScore >= 70 ? 'text-emerald-600 dark:text-emerald-400' : currentResult.qualityScore >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                      {currentResult.qualityScore}/100
                    </p>
                    <p className="text-[9px] text-muted-foreground">Quality Score</p>
                  </div>
                </div>

                {/* Quality Progress Bar */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-muted-foreground">Quality</span>
                    <span className="text-[10px] font-medium tabular-nums">{currentResult.qualityScore}%</span>
                  </div>
                  <Progress value={currentResult.qualityScore} className="h-2" />
                </div>

                {/* Response */}
                <div>
                  <p className="text-[10px] font-medium text-muted-foreground mb-1">Model Response</p>
                  <div className="max-h-48 overflow-y-auto rounded-md bg-accent/20 border border-border/50 p-3 text-xs leading-relaxed custom-scrollbar whitespace-pre-wrap">
                    {currentResult.response}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Test History */}
      {testHistory.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                Test History
                <Badge variant="outline" className="text-[9px]">{testHistory.length} tests</Badge>
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[10px] gap-1 text-muted-foreground hover:text-red-600 dark:text-red-400"
                onClick={() => {
                  setTestHistory([])
                  toast.success('Test history cleared')
                }}
              >
                <Trash2 className="h-3 w-3" /> Clear
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-3 pt-0">
            <div className="max-h-64 space-y-1.5 overflow-y-auto custom-scrollbar">
              {testHistory.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center gap-2 rounded-md bg-accent/20 px-2.5 py-2 text-xs hover:bg-accent/40 transition-colors cursor-pointer"
                  onClick={() => setCurrentResult(t)}
                >
                  {t.passed ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 shrink-0 text-yellow-600 dark:text-yellow-400" />
                  )}
                  <span className="font-medium truncate max-w-[120px]">{t.model.split('-')[0]}</span>
                  <Badge variant="outline" className="text-[8px] shrink-0">{testTypeConfig[t.testType].label}</Badge>
                  <span className="text-muted-foreground shrink-0 tabular-nums">{t.responseTimeMs}ms</span>
                  <span className={`shrink-0 font-bold tabular-nums ${t.qualityScore >= 70 ? 'text-emerald-600 dark:text-emerald-400' : t.qualityScore >= 50 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                    {t.qualityScore}%
                  </span>
                  <span className="ml-auto text-[10px] text-muted-foreground/50 shrink-0 tabular-nums">
                    {t.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ── AI Provider Bridge Sub-Components ────────────────────────────

function ProviderStatusCards({ providers }: { providers: ProviderInfo[] }) {
  const providerIcons: Record<string, typeof Cpu> = { 'z-ai': Cpu, 'nvidia': Server, 'openrouter': Sparkles }
  const providerDescs: Record<string, string> = {
    'z-ai': 'Built-in SDK · Fast local routing',
    'nvidia': '40 req/min free · GPU inference',
    'openrouter': 'Free tier active · Multi-model',
  }

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {providers.map((p) => {
        const IconComp = providerIcons[p.provider] ?? Cpu
        const desc = providerDescs[p.provider] ?? ''
        const healthColor = p.health === 'healthy'
          ? 'text-emerald-600 dark:text-emerald-400'
          : p.health === 'degraded'
            ? 'text-yellow-600 dark:text-yellow-400'
            : 'text-red-600 dark:text-red-400'
        const healthDot = p.health === 'healthy'
          ? 'bg-emerald-500'
          : p.health === 'degraded'
            ? 'bg-yellow-500'
            : 'bg-red-500'
        const borderAccent = p.provider === 'z-ai'
          ? 'border-emerald-600/20'
          : p.provider === 'nvidia'
            ? 'border-amber-600/20'
            : 'border-purple-600/20'
        const gradientFrom = p.provider === 'z-ai'
          ? 'from-emerald-600/8'
          : p.provider === 'nvidia'
            ? 'from-amber-600/8'
            : 'from-purple-600/8'
        const iconBg = p.provider === 'z-ai'
          ? 'bg-emerald-600/15'
          : p.provider === 'nvidia'
            ? 'bg-amber-600/15'
            : 'bg-purple-600/15'
        const iconColor = p.provider === 'z-ai'
          ? 'text-emerald-600 dark:text-emerald-400'
          : p.provider === 'nvidia'
            ? 'text-amber-600 dark:text-amber-400'
            : 'text-purple-600 dark:text-purple-400'

        return (
          <Card key={p.provider} className={`relative overflow-hidden ${borderAccent} hover-lift`}>
            <div className={`absolute inset-0 bg-gradient-to-br ${gradientFrom} via-transparent to-transparent`} />
            <CardContent className="relative p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg} shadow-lg`}>
                    <IconComp className={`h-5 w-5 ${iconColor}`} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{p.label}</p>
                    <p className="text-[10px] text-muted-foreground">{desc}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${healthDot} ${p.health === 'degraded' ? 'animate-pulse' : ''}`} />
                  <span className={`text-[10px] font-medium ${healthColor}`}>
                    {p.health === 'healthy' ? 'Healthy' : p.health === 'degraded' ? 'Degraded' : 'Down'}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-md bg-accent/30 py-1.5 text-center">
                  <p className="text-lg font-bold tabular-nums">{p.activeModels}</p>
                  <p className="text-[9px] text-muted-foreground">Models</p>
                </div>
                <div className="rounded-md bg-accent/30 py-1.5 text-center">
                  <p className="text-lg font-bold tabular-nums">{p.rateLimitRemaining}</p>
                  <p className="text-[9px] text-muted-foreground">Req Left</p>
                </div>
                <div className="rounded-md bg-accent/30 py-1.5 text-center">
                  <p className="text-lg font-bold tabular-nums">{p.avgLatencyMs}</p>
                  <p className="text-[9px] text-muted-foreground">Avg ms</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function ModelTierRouter({ routes }: { routes: ProviderRoute[] }) {
  const [expandedTier, setExpandedTier] = useState<string | null>(null)

  const healthDot = (health: string) =>
    health === 'healthy' ? 'bg-emerald-500' : health === 'degraded' ? 'bg-yellow-500 animate-pulse' : 'bg-red-500 animate-pulse'

  return (
    <Card className="relative overflow-hidden border-emerald-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent grid-pattern" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <ArrowRight className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          Model Tier Router
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="space-y-2">
          {routes.map((route) => {
            const cfg = TIER_CONFIG[route.tier]
            const isExpanded = expandedTier === route.id
            return (
              <div key={route.id}>
                <button
                  type="button"
                  onClick={() => setExpandedTier(isExpanded ? null : route.id)}
                  className={`w-full text-left rounded-lg border ${cfg.borderColor} bg-accent/10 hover:bg-accent/20 transition-all duration-200 overflow-hidden`}
                >
                  <div className="flex items-center gap-3 px-4 py-3">
                    {/* Tier Icon + Name */}
                    <span className="text-lg shrink-0">{cfg.icon}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-semibold ${cfg.textColor}`}>{cfg.label}</span>
                        <Badge className={`border-0 text-[9px] px-1.5 ${cfg.bgColor} ${cfg.textColor}`}>
                          {route.isFree ? 'FREE' : 'PAID'}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-foreground font-medium truncate">{route.displayName}</p>
                    </div>

                    {/* Health Dot */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`h-2 w-2 rounded-full ${healthDot(route.health)}`} />
                    </div>

                    {/* Latency Badge */}
                    <Badge variant="outline" className={`text-[9px] shrink-0 tabular-nums ${
                      route.latencyMs < 500 ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' :
                      route.latencyMs < 1500 ? 'border-amber-600/30 text-amber-600 dark:text-amber-400' :
                      'border-red-600/30 text-red-600 dark:text-red-400'
                    }`}>
                      {route.latencyMs}ms
                    </Badge>

                    {/* Success Rate Badge */}
                    <Badge variant="outline" className={`text-[9px] shrink-0 tabular-nums ${
                      route.successRate >= 98 ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' :
                      route.successRate >= 95 ? 'border-amber-600/30 text-amber-600 dark:text-amber-400' :
                      'border-red-600/30 text-red-600 dark:text-red-400'
                    }`}>
                      {route.successRate}%
                    </Badge>

                    {/* Expand Chevron */}
                    <ChevronRight className={`h-4 w-4 text-muted-foreground shrink-0 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
                  </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="mt-1.5 ml-4 rounded-lg border border-border/50 bg-accent/10 p-3 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-[9px] text-muted-foreground uppercase tracking-wider">Actual Model</p>
                        <p className="text-xs font-mono mt-0.5">{route.actualModel}</p>
                      </div>
                      <div>
                        <p className="text-[9px] text-muted-foreground uppercase tracking-wider">Provider</p>
                        <p className="text-xs font-medium mt-0.5">{route.providerLabel}</p>
                      </div>
                      <div>
                        <p className="text-[9px] text-muted-foreground uppercase tracking-wider">Fallback Model</p>
                        <p className="text-xs font-medium mt-0.5">{route.fallbackModel ?? 'None'}</p>
                      </div>
                      <div>
                        <p className="text-[9px] text-muted-foreground uppercase tracking-wider">Context Window</p>
                        <p className="text-xs font-medium tabular-nums mt-0.5">{(route.contextWindow / 1024).toFixed(0)}K tokens</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Capabilities</p>
                      <div className="flex flex-wrap gap-1">
                        {route.capabilities.map(cap => (
                          <Badge key={cap} variant="outline" className="text-[9px]">{cap}</Badge>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-muted-foreground">Rate Limit: <span className="font-bold tabular-nums">{route.rateLimitPerMin}</span> req/min</span>
                      <span className="text-[10px] text-muted-foreground">Total Calls: <span className="font-bold tabular-nums">{route.totalCalls.toLocaleString()}</span></span>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

function RequestOptimizationStats() {
  return (
    <Card className="relative overflow-hidden border-emerald-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Zap className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          Request Optimization
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-2">
        {OPTIMIZATION_STATS.map((stat) => {
          const IconComp = stat.icon
          return (
            <div key={stat.category} className="flex items-center gap-3 rounded-md bg-accent/20 px-3 py-2">
              <IconComp className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span className="text-xs flex-1">{stat.category}</span>
              <span className="text-xs font-bold tabular-nums">{stat.count.toLocaleString()}</span>
              <Badge className="border-0 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 text-[9px] px-1.5">
                {stat.saved} saved
              </Badge>
            </div>
          )
        })}
        <div className="flex items-center justify-between pt-1 border-t border-border/30">
          <span className="text-[10px] text-muted-foreground">Total optimized locally</span>
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
            {OPTIMIZATION_STATS.reduce((s, o) => s + o.count, 0).toLocaleString()} requests
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

function TestRequestDialog({ routes }: { routes: ProviderRoute[] }) {
  const [open, setOpen] = useState(false)
  const [selectedTier, setSelectedTier] = useState<string>('reasoning')
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<{
    response: string
    model: string
    latencyMs: number
    provider: string
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSend = useCallback(async () => {
    if (!message.trim()) {
      toast.error('Please enter a test message')
      return
    }
    setSending(true)
    setError(null)
    setResult(null)

    const startTime = Date.now()

    try {
      // Try the AI bridge endpoint first
      const res = await globalThis.fetch('/api/ai-bridge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier: selectedTier, message }),
      })

      const responseTimeMs = Date.now() - startTime

      if (!res.ok) {
        // Fallback to chat endpoint if bridge isn't available yet
        const fallbackRes = await globalThis.fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [{ role: 'user', content: message }],
            systemPrompt: 'You are a helpful AI assistant. Respond concisely.',
          }),
        })

        if (!fallbackRes.ok) {
          throw new Error(`Both endpoints unavailable (HTTP ${fallbackRes.status})`)
        }

        const fallbackData = await fallbackRes.json()
        const selectedRoute = routes.find(r => r.tier === selectedTier)
        setResult({
          response: fallbackData.response || fallbackData.content || 'No response received',
          model: selectedRoute?.displayName ?? 'Unknown',
          latencyMs: Date.now() - startTime,
          provider: selectedRoute?.providerLabel ?? 'N/A',
        })
      } else {
        const data = await res.json()
        setResult({
          response: data.response || data.content || 'No response received',
          model: data.model || data.displayName || 'Unknown',
          latencyMs: responseTimeMs,
          provider: data.providerLabel || data.provider || 'N/A',
        })
      }

      toast.success('Test request completed')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      toast.error('Test request failed', { description: msg })
    } finally {
      setSending(false)
    }
  }, [selectedTier, message, routes])

  const selectedRoute = routes.find(r => r.tier === selectedTier)
  const selectedCfg = selectedTier ? TIER_CONFIG[selectedTier] : null

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-emerald-600 hover:bg-emerald-700 gap-2" size="sm">
          <Send className="h-3.5 w-3.5" />
          Send Test Request
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            AI Bridge Test Request
          </DialogTitle>
          <DialogDescription>
            Send a test request through the AI Provider Bridge to verify routing and model response.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Tier Selection */}
          <div className="space-y-2">
            <Label className="text-xs font-medium">Select Tier</Label>
            <div className="grid grid-cols-4 gap-2">
              {routes.map((route) => {
                const cfg = TIER_CONFIG[route.tier]
                const isSelected = selectedTier === route.tier
                return (
                  <button
                    key={route.id}
                    type="button"
                    onClick={() => setSelectedTier(route.tier)}
                    className={`rounded-lg border p-2 text-center transition-all duration-200 ${
                      isSelected
                        ? `${cfg.borderColor} ${cfg.bgColor} shadow-md`
                        : 'border-border/50 bg-accent/20 hover:bg-accent/40'
                    }`}
                  >
                    <span className="text-lg">{cfg.icon}</span>
                    <p className={`text-[10px] font-semibold mt-0.5 ${isSelected ? cfg.textColor : 'text-muted-foreground'}`}>
                      {cfg.label}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Selected Model Info */}
          {selectedRoute && selectedCfg && (
            <div className={`rounded-md border ${selectedCfg.borderColor} ${selectedCfg.bgColor} px-3 py-2`}>
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${selectedRoute.health === 'healthy' ? 'bg-emerald-500' : selectedRoute.health === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'}`} />
                <span className="text-xs font-medium">{selectedRoute.displayName}</span>
                <Badge className="border-0 text-[8px] px-1 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400">FREE</Badge>
                <span className="ml-auto text-[10px] text-muted-foreground">{selectedRoute.providerLabel}</span>
              </div>
              {selectedRoute.fallbackModel && (
                <p className="text-[10px] text-muted-foreground mt-1">
                  Fallback: {selectedRoute.fallbackModel}
                </p>
              )}
            </div>
          )}

          {/* Message Input */}
          <div className="space-y-2">
            <Label className="text-xs font-medium">Test Message</Label>
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your test message here..."
              rows={3}
              className="text-xs resize-none"
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="rounded-md bg-red-600/10 border border-red-600/20 px-3 py-2 text-xs text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Result Display */}
          {result && (
            <div className="rounded-md border border-emerald-600/20 bg-emerald-600/5 overflow-hidden">
              <div className="flex items-center gap-3 px-3 py-2 bg-emerald-600/10 border-b border-emerald-600/20">
                <Badge className="border-0 bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 text-[9px]">
                  {result.model}
                </Badge>
                <Badge variant="outline" className="text-[9px] tabular-nums">
                  {result.latencyMs}ms
                </Badge>
                <Badge variant="outline" className="text-[9px]">
                  {result.provider}
                </Badge>
              </div>
              <div className="p-3 max-h-40 overflow-y-auto custom-scrollbar">
                <p className="text-xs leading-relaxed whitespace-pre-wrap">{result.response}</p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
            Close
          </Button>
          <Button
            onClick={handleSend}
            disabled={sending || !message.trim()}
            className="bg-emerald-600 hover:bg-emerald-700 gap-2"
            size="sm"
          >
            {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            {sending ? 'Sending...' : 'Send Request'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function GmrTab() {
  const { data: modelsData, loading, refetch } = useApiData<{ models: ModelData[] }>('/api/models', 15000)
  const baseModels = useMemo(() => modelsData?.models ?? [], [modelsData])
  const [healthPulse, setHealthPulse] = useState(0)

  // Track user overrides for active/inactive state per model ID (optimistic updates)
  // Empty = use base data; populated = user has toggled that model
  const [overrides, setOverrides] = useState<Record<string, boolean>>({})

  // Simulate health fluctuations on top of base data
  const models = useMemo(() => {
    return baseModels.map(m => {
      const isActive = m.id in overrides ? overrides[m.id] : m.isActive
      return {
        ...m,
        isActive,
        health: isActive
          ? Math.min(100, Math.max(80, m.health + (healthPulse % 5 === 0 ? 0 : (healthPulse % 2 === 0 ? 1 : -1))))
          : m.health,
      }
    })
  }, [baseModels, healthPulse, overrides])

  // Find which pool(s) a model belongs to
  const getModelPools = useCallback((modelName: string) => {
    return poolDefinitions.filter(pool => pool.modelNames.includes(modelName))
  }, [])

  // Check if a model is the last active one in any of its pools
  const isLastActiveInPool = useCallback((modelId: string) => {
    const model = models.find(m => m.id === modelId)
    if (!model) return false
    const pools = getModelPools(model.name)
    return pools.some(pool => {
      const poolModels = models.filter(m => pool.modelNames.includes(m.name))
      const activeInPool = poolModels.filter(m => m.isActive)
      return activeInPool.length === 1 && activeInPool[0].id === modelId
    })
  }, [models, getModelPools])

  // Handle model toggle — calls API to persist change
  const handleToggle = useCallback(async (modelId: string) => {
    const model = models.find(m => m.id === modelId)
    if (!model) return

    const newState = !model.isActive

    // If deactivating, check if it's the last active model in any pool
    if (!newState && isLastActiveInPool(modelId)) {
      toast.warning(`Cannot deactivate ${model.name} — it's the last active model in its pool`)
      return
    }

    // Optimistic update via override
    setOverrides(prev => ({ ...prev, [modelId]: newState }))
    toast.success(`Model ${model.name} ${newState ? 'activated' : 'deactivated'}`)

    // Call API to persist the toggle
    try {
      const res = await globalThis.fetch('/api/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'toggle', modelId }),
      })
      if (!res.ok) {
        toast.error(`Failed to toggle ${model.name}`)
        // Revert optimistic update
        setOverrides(prev => {
          const next = { ...prev }
          delete next[modelId]
          return next
        })
      } else {
        refetch()
      }
    } catch {
      toast.error(`Failed to toggle ${model.name}`)
      // Revert optimistic update
      setOverrides(prev => {
        const next = { ...prev }
        delete next[modelId]
        return next
      })
    }
  }, [models, isLastActiveInPool, refetch])

  // Reset all models to their original isActive state (clear overrides + refetch)
  const handleReset = useCallback(() => {
    setOverrides({})
    refetch()
    toast.info('All models reset to default state')
  }, [refetch])

  // Run health check on all models
  const [healthCheckRunning, setHealthCheckRunning] = useState(false)
  const handleHealthCheck = useCallback(async () => {
    setHealthCheckRunning(true)
    toast.info('Running health check on all models...')
    let successCount = 0
    let failCount = 0
    for (const m of models) {
      try {
        const res = await globalThis.fetch('/api/models', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'health_check', modelId: m.id }),
        })
        if (res.ok) successCount++
        else failCount++
      } catch {
        failCount++
      }
    }
    refetch()
    setHealthCheckRunning(false)
    if (failCount === 0) {
      toast.success(`Health check completed for ${successCount} models`)
    } else {
      toast.warning(`Health check: ${successCount} succeeded, ${failCount} failed`)
    }
  }, [models, refetch])

  // Timer for health simulation pulse
  useEffect(() => {
    const interval = setInterval(() => {
      setHealthPulse(p => p + 1)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const activeModels = models.filter(m => m.isActive)
  const avgHealth = activeModels.length ? Math.round(activeModels.reduce((s, m) => s + m.health, 0) / activeModels.length) : 0
  const totalCalls = models.reduce((s, m) => s + m.totalCalls, 0)
  const freeActiveCount = models.filter(m => m.isActive && m.isFree).length
  const modelSparklines = useMemo(() => getModelSparklines(models), [models])

  // Fetch AI Provider Bridge data (with mock fallback)
  const [bridgeData, setBridgeData] = useState<BridgeData>(MOCK_BRIDGE_DATA)
  useEffect(() => {
    let mounted = true
    globalThis.fetch('/api/ai-bridge')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (mounted && data?.routes && data?.providers) {
          setBridgeData(data)
        }
      })
      .catch(() => {
        // Use mock data if endpoint doesn't exist yet
      })
    return () => { mounted = false }
  }, [])

  return (
    <div className="space-y-6 p-6 grid-pattern-animated">
      {/* ── AI Provider Bridge Section ─────────────────────────── */}
      <div className="space-y-4">
        {/* Section Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              <ArrowRight className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              AI Provider Bridge — Honest Model Routing
            </h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Transparent model routing — you see exactly which model handles your request
            </p>
          </div>
          <TestRequestDialog routes={bridgeData.routes} />
        </div>

        {/* Provider Status Cards */}
        <ProviderStatusCards providers={bridgeData.providers} />

        {/* Model Tier Router + Request Optimization */}
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ModelTierRouter routes={bridgeData.routes} />
          </div>
          <RequestOptimizationStats />
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Models Online</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{activeModels.length}</p>
                <p className="text-[10px] text-muted-foreground">of {models.length} total</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Wifi className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Avg Health</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{avgHealth}%</p>
                <p className="text-[10px] text-muted-foreground">across active models</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total API Calls</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{totalCalls.toLocaleString()}</p>
                <p className="text-[10px] text-muted-foreground">this session</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                <Zap className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">FREE_RESEARCH Pool</p>
                <p className="mt-1 text-3xl font-bold text-purple-600 dark:text-purple-400 tabular-nums">{freeActiveCount}</p>
                <p className="text-[10px] text-muted-foreground">free-tier models active</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-600/15 shadow-lg shadow-purple-600/10">
                <Gauge className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Latency Chart + Model Performance Comparison */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Gauge className="h-4 w-4" /> Model Latency Over Time
              </CardTitle>
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-400" /> qwen3-coder</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-blue-400" /> trinity</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-orange-400" /> gemma-fast</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <NexusBarChart
              data={latencyHistory}
              dataKey="qwen"
              nameKey="name"
              color={COLORS.emerald}
              height={100}
            />
          </CardContent>
        </Card>
        <ModelPerformanceComparison models={models} />
      </div>

      {/* Pool Health Overview + Rotation Analytics + Failover Log */}
      <div className="grid gap-4 lg:grid-cols-3">
        <PoolHealthOverview models={models} />
        <RotationAnalyticsCard />
        <FailoverLogCard />
      </div>

      <Tabs defaultValue="models" className="space-y-4">
        <TabsList>
          <TabsTrigger value="models">Model Registry</TabsTrigger>
          <TabsTrigger value="pools">Pool Status</TabsTrigger>
          <TabsTrigger value="rotation">Rotation Log</TabsTrigger>
          <TabsTrigger value="test" className="gap-1.5">
            <Terminal className="h-3 w-3" />
            Test Console
          </TabsTrigger>
        </TabsList>

        {/* Model Registry */}
        <TabsContent value="models">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-muted-foreground">{models.length} models registered</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1.5" onClick={() => refetch()}>
                <RefreshCw className="h-3 w-3" /> Refresh Models
              </Button>
              <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1.5" onClick={handleHealthCheck} disabled={healthCheckRunning}>
                <HeartPulse className={`h-3 w-3 ${healthCheckRunning ? 'animate-pulse' : ''}`} /> {healthCheckRunning ? 'Checking...' : 'Health Check'}
              </Button>
              <Button variant="outline" size="sm" className="h-7 text-[11px] gap-1.5" onClick={handleReset}>
                <RotateCcw className="h-3 w-3" /> Reset to Default
              </Button>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {models.map((m) => (
              <Card key={m.id} className={`group relative overflow-hidden transition-all duration-300 hover-lift ${m.isActive ? 'hover:border-emerald-600/20' : 'opacity-50'}`}>
                {m.isActive && <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />}
                <CardContent className="relative p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">{m.name}</p>
                        {m.isFree && (
                          <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px] px-1">FREE</Badge>
                        )}
                        {!m.isActive && (
                          <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px] px-1 animate-in fade-in duration-200">Disabled</Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground">{m.provider} · {m.domain}</p>
                    </div>
                    <div className="shrink-0">
                      {m.isActive ? (
                        <span className="relative flex h-4 w-4">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-30" />
                          <Wifi className="relative h-4 w-4 text-emerald-600 dark:text-emerald-400 status-glow-green" />
                        </span>
                      ) : (
                        <WifiOff className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-md bg-accent/30 py-1">
                      <p className="text-[9px] text-muted-foreground">Tier</p>
                      <p className="text-sm font-bold">{m.tier}</p>
                    </div>
                    <div className="rounded-md bg-accent/30 py-1">
                      <p className="text-[9px] text-muted-foreground">Health</p>
                      <p className={`text-sm font-bold ${m.health >= 95 ? 'text-emerald-600 dark:text-emerald-400' : m.health >= 85 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>{m.health}%</p>
                    </div>
                    <div className="rounded-md bg-accent/30 py-1">
                      <p className="text-[9px] text-muted-foreground">Latency</p>
                      <p className="text-sm font-bold">{m.latencyMs}ms</p>
                    </div>
                  </div>

                  <div className="mt-3">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>Success Rate</span>
                      <span className={m.successRate >= 98 ? 'text-emerald-600 dark:text-emerald-400' : m.successRate >= 90 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}>{m.successRate}%</span>
                    </div>
                    <Progress value={m.successRate} className="mt-1 h-1.5" />
                  </div>

                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{m.totalCalls.toLocaleString()} calls</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-muted-foreground">Active</span>
                      <Switch
                        checked={m.isActive}
                        onCheckedChange={() => handleToggle(m.id)}
                        className="scale-75"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Pool Status - Enhanced with per-model mini sparklines */}
        <TabsContent value="pools">
          <div className="grid gap-4 md:grid-cols-2">
            {poolDefinitions.map((pool) => {
              const poolModels = models.filter(m => pool.modelNames.includes(m.name))
              const poolCalls = poolModels.reduce((s, m) => s + m.totalCalls, 0)
              const poolHealth = poolModels.length ? Math.round(poolModels.reduce((s, m) => s + m.health, 0) / poolModels.length) : 0
              return (
                <Card key={pool.name} className="relative overflow-hidden hover-lift">
                  <div className={`absolute inset-0 bg-gradient-to-br ${pool.gradient} via-transparent to-transparent`} />
                  <CardHeader className="relative pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: pool.color }} />
                        {pool.name} Pool
                      </CardTitle>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="text-[10px]">Tier {pool.tierRange}</Badge>
                        <Badge className="text-[10px] border-0 bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">{poolHealth}% health</Badge>
                      </div>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{pool.desc}</p>
                  </CardHeader>
                  <CardContent className="relative p-4 pt-0">
                    <div className="space-y-2">
                      {poolModels.map((m) => (
                        <div key={m.id} className="flex items-center gap-2 rounded-md bg-accent/20 px-2.5 py-1.5">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${m.isActive ? 'bg-emerald-500 status-glow-green' : 'bg-muted-foreground'}`} />
                            <span className="font-medium text-xs truncate">{m.name}</span>
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-muted-foreground shrink-0">
                            <span>{m.health}%</span>
                            <span>{m.latencyMs}ms</span>
                            <span className="text-emerald-600 dark:text-emerald-400">{m.totalCalls}</span>
                          </div>
                          {/* Per-model mini sparkline */}
                          {modelSparklines[m.name] && (
                            <div className="w-16 shrink-0">
                              <MiniAreaChart
                                data={modelSparklines[m.name]}
                                dataKey="value"
                                color={m.health >= 95 ? COLORS.emerald : m.health >= 85 ? COLORS.yellow : COLORS.red}
                                height={20}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground">{poolCalls.toLocaleString()} total calls</span>
                      <NexusBarChart
                        data={poolModels.map(m => ({ name: m.name.split('-')[0].substring(0, 6), value: m.totalCalls }))}
                        height={40}
                      />
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </TabsContent>

        {/* Rotation Log */}
        <TabsContent value="rotation">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Hermes Router — Rotation Log</CardTitle>
                <Button variant="ghost" size="sm" className="h-7 text-[11px]" onClick={() => refetch()}>
                  <RefreshCw className="mr-1 h-3 w-3" /> Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="max-h-96 space-y-1.5 overflow-y-auto custom-scrollbar">
                {rotationLog.map((r, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg bg-accent/30 px-3 py-2 text-xs hover:bg-accent/50 transition-colors">
                    <span className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">{r.time}</span>
                    <span className="text-muted-foreground">{r.from === '-' ? '—' : r.from}</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">→</span>
                    <span className="font-medium">{r.to}</span>
                    <span className="ml-auto text-[10px] text-muted-foreground shrink-0">{r.reason}</span>
                    {r.tokens > 0 && <Badge variant="outline" className="text-[9px] shrink-0">{r.tokens}tok</Badge>}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Test Console */}
        <TabsContent value="test">
          <ModelTestConsole models={models} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
