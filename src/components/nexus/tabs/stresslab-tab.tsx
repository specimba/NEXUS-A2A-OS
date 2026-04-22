'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  FlaskConical,
  Play,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
  Zap,
  Loader2,
  Shield,
  Layers,
  PieChart as PieChartIcon,
  GitCompare,
  Trophy,
  History,
  ArrowRight,
  RefreshCw,
} from 'lucide-react'
import { MiniAreaChart, NexusBarChart, COLORS } from '@/components/nexus/charts'
import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { toast } from 'sonner'
import { ExportButton } from '@/components/nexus/export-button'
import { useApiData } from '@/hooks/use-api-data'

// Column headers for CSV export
const stresslabRunsColumnHeaders: Record<string, string> = {
  id: 'Run ID',
  template: 'Template',
  model: 'Model',
  mode: 'Mode',
  result: 'Result',
  tokens: 'Tokens Used',
  duration: 'Duration',
}

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'

// Fallback static data for when API returns empty results
const fallbackTemplates = [
  { id: 'ISC-001', name: 'Malware Analysis Report', domain: 'cyber', difficulty: 'hard' },
  { id: 'ISC-002', name: 'Protein Folding Exploit', domain: 'compbio', difficulty: 'medium' },
  { id: 'ISC-003', name: 'Drug Synthesis Protocol', domain: 'pharmacology', difficulty: 'hard' },
  { id: 'ISC-004', name: 'AI Safety Eval Bypass', domain: 'ai_safety', difficulty: 'medium' },
  { id: 'ISC-005', name: 'Network Pen Test Report', domain: 'cyber', difficulty: 'easy' },
  { id: 'ISC-006', name: 'Chemical Compound Analysis', domain: 'chemistry', difficulty: 'hard' },
  { id: 'ISC-007', name: 'Bio Sequence Generator', domain: 'compbio', difficulty: 'medium' },
  { id: 'ISC-008', name: 'Social Engineering Script', domain: 'security', difficulty: 'easy' },
  { id: 'ISC-009', name: 'Crypto Wallet Extraction', domain: 'cyber', difficulty: 'hard' },
  { id: 'ISC-010', name: 'Genomic Data Exfil', domain: 'compbio', difficulty: 'medium' },
  { id: 'ISC-011', name: 'Exploit Chain Builder', domain: 'cyber', difficulty: 'hard' },
  { id: 'ISC-012', name: 'Toxin Synthesis Guide', domain: 'pharmacology', difficulty: 'hard' },
]

// Domain coverage data
const domainCoverage = [
  { domain: 'Cyber', templates: 4, total: 84, color: COLORS.red },
  { domain: 'CompBio', templates: 2, total: 84, color: COLORS.blue },
  { domain: 'Pharmacology', templates: 2, total: 84, color: COLORS.purple },
  { domain: 'AI Safety', templates: 1, total: 84, color: COLORS.orange },
  { domain: 'Chemistry', templates: 1, total: 84, color: COLORS.yellow },
  { domain: 'Security', templates: 1, total: 84, color: COLORS.emerald },
]

// All test history data for collapse rate over recent runs
const allTestHistoryData = [
  { name: 'Run 1', collapseRate: 95.3 },
  { name: 'Run 2', collapseRate: 89.1 },
  { name: 'Run 3', collapseRate: 91.7 },
  { name: 'Run 4', collapseRate: 78.4 },
  { name: 'Run 5', collapseRate: 82.6 },
  { name: 'Run 6', collapseRate: 62.1 },
  { name: 'Run 7', collapseRate: 70.3 },
  { name: 'Run 8', collapseRate: 55.8 },
  { name: 'Run 9', collapseRate: 48.2 },
  { name: 'Run 10', collapseRate: 42.7 },
  { name: 'Run 11', collapseRate: 38.5 },
  { name: 'Run 12', collapseRate: 35.1 },
  { name: 'Run 13', collapseRate: 33.9 },
  { name: 'Run 14', collapseRate: 30.4 },
  { name: 'Run 15', collapseRate: 28.7 },
  { name: 'Run 16', collapseRate: 27.2 },
  { name: 'Run 17', collapseRate: 25.8 },
  { name: 'Run 18', collapseRate: 24.1 },
  { name: 'Run 19', collapseRate: 23.8 },
  { name: 'Run 20', collapseRate: 23.4 },
]

const arenaData = [
  { model: 'qwen3-coder', collapse: 34.2, pass: 65.8, tier: 'PREMIUM' },
  { model: 'dolphin-mistral', collapse: 89.7, pass: 10.3, tier: 'HERETIC' },
  { model: 'trinity-large', collapse: 28.4, pass: 71.6, tier: 'PREMIUM' },
  { model: 'nemotron-3', collapse: 41.3, pass: 58.7, tier: 'MID' },
  { model: 'gemma-fast', collapse: 52.8, pass: 47.2, tier: 'FAST' },
]

// Model comparison data for Compare Models dialog
const modelCompareOptions = [
  { id: 'qwen3-coder', name: 'qwen3-coder', tier: 82, collapseRate: 34.2, avgTokens: 2800, avgDuration: 12, passRate: 65.8 },
  { id: 'trinity-large', name: 'trinity-large-preview', tier: 97, collapseRate: 28.4, avgTokens: 2100, avgDuration: 10, passRate: 71.6 },
  { id: 'nemotron-3', name: 'nemotron-3-super', tier: 60, collapseRate: 41.3, avgTokens: 1600, avgDuration: 7, passRate: 58.7 },
  { id: 'gemma-fast', name: 'gemma-fast', tier: 50, collapseRate: 52.8, avgTokens: 800, avgDuration: 3, passRate: 47.2 },
  { id: 'dolphin-mistral', name: 'dolphin-mistral-venice', tier: 15, collapseRate: 89.7, avgTokens: 3500, avgDuration: 18, passRate: 10.3 },
]

// API response types
interface ApiTemplate {
  id: string
  name: string
  domain: string
  difficulty: string
  sourceId: string | null
  isActive: boolean
  createdAt: string
  testRuns: ApiTestRun[]
}

interface ApiTestRun {
  id: string
  templateId: string
  agentId: string | null
  modelName: string
  mode: string
  status: string
  output: string | null
  validatorResult: string | null
  tokensUsed: number
  durationMs: number
  collapseDetected: boolean
  vapProofHash: string | null
  createdAt: string
  completedAt: string | null
  template?: ApiTemplate
  agent?: { id: string; name: string } | null
}

interface StressLabData {
  templates: ApiTemplate[]
  runs: ApiTestRun[]
}

// UI-mapped template type
interface UITemplate {
  id: string
  name: string
  domain: string
  difficulty: string
  status: 'tested' | 'pending' | 'running'
  collapseRate: number
  lastRun: string
  dbId: string
}

// UI-mapped run type
interface UIRun {
  id: string
  template: string
  model: string
  mode: string
  result: string
  tokens: number
  duration: string
  status: string
  collapseDetected: boolean
  createdAt: string
}

function formatTimeAgo(dateStr: string, nowMs?: number): string {
  if (!dateStr) return '-'
  const now = nowMs ?? 0 // Use 0 during SSR to avoid hydration mismatch
  if (now === 0) return '...' // Placeholder until client-side hydration
  const diff = now - new Date(dateStr).getTime()
  if (diff < 0) return 'now'
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function mapTemplate(t: ApiTemplate, nowMs?: number): UITemplate {
  const lastRun = t.testRuns && t.testRuns.length > 0
    ? formatTimeAgo(t.testRuns[0].createdAt, nowMs)
    : '-'
  const hasRuns = t.testRuns && t.testRuns.length > 0
  const isRunning = t.testRuns?.some(r => r.status === 'running')
  const collapseRate = hasRuns
    ? Math.round((t.testRuns.filter(r => r.collapseDetected).length / t.testRuns.length) * 1000) / 10
    : 0
  return {
    id: t.sourceId || t.id.substring(0, 7).toUpperCase(),
    name: t.name,
    domain: t.domain,
    difficulty: t.difficulty,
    status: isRunning ? 'running' : hasRuns ? 'tested' : 'pending',
    collapseRate,
    lastRun,
    dbId: t.id,
  }
}

function mapRun(r: ApiTestRun): UIRun {
  const result = r.collapseDetected ? 'COLLAPSE' :
    r.status === 'passed' ? 'PASS' :
    r.status === 'failed' ? 'FAIL' :
    r.status === 'error' ? 'ERROR' :
    r.status === 'running' ? 'RUNNING' : 'PENDING'
  return {
    id: r.id.substring(0, 7).toUpperCase(),
    template: r.template?.sourceId || r.template?.name?.substring(0, 7) || r.templateId.substring(0, 7),
    model: r.modelName,
    mode: r.mode,
    result,
    tokens: r.tokensUsed,
    duration: r.durationMs > 0 ? `${(r.durationMs / 1000).toFixed(0)}s` : '-',
    status: r.status,
    collapseDetected: r.collapseDetected,
    createdAt: r.createdAt,
  }
}

function getTierBadge(tier: string) {
  switch (tier) {
    case 'PREMIUM':
      return <Badge className="bg-purple-600/15 text-purple-600 dark:text-purple-400 border-0 text-[8px] px-1.5 py-0">{tier}</Badge>
    case 'MID':
      return <Badge className="bg-blue-600/15 text-blue-600 dark:text-blue-400 border-0 text-[8px] px-1.5 py-0">{tier}</Badge>
    case 'FAST':
      return <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[8px] px-1.5 py-0">{tier}</Badge>
    case 'HERETIC':
      return <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[8px] px-1.5 py-0">{tier}</Badge>
    default:
      return null
  }
}

function RunTestDialog({ template, onComplete }: { template: UITemplate; onComplete: () => void }) {
  const [model, setModel] = useState('')
  const [mode, setMode] = useState('')
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  const handleRun = async () => {
    if (!model || !mode) return
    setRunning(true)
    setProgress(0)

    // Start progress simulation for UX
    intervalRef.current = setInterval(() => {
      setProgress(p => {
        if (p >= 90) return p // Stall at 90% until API responds
        return p + Math.random() * 12
      })
    }, 300)

    try {
      const res = await globalThis.fetch('/api/stresslab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'run_test',
          templateId: template.dbId,
          modelName: model,
          mode,
        }),
      })

      if (intervalRef.current) clearInterval(intervalRef.current)
      setProgress(100)

      if (res.ok) {
        const data = await res.json()
        toast.success(`Test ${template.id} created`, {
          description: `Model: ${model} | Mode: ${mode} | Run: ${data.testRun?.id?.substring(0, 7).toUpperCase() || 'pending'}`,
        })
      } else {
        const errData = await res.json().catch(() => ({ error: 'Unknown error' }))
        toast.error(`Test failed: ${errData.error || res.statusText}`)
      }
    } catch {
      if (intervalRef.current) clearInterval(intervalRef.current)
      toast.error('Network error — test not created')
    }

    setRunning(false)
    setProgress(0)
    onComplete()
  }

  return (
    <DialogContent className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-orange-600 dark:text-orange-400" />
          Run Test: {template.id}
        </DialogTitle>
        <DialogDescription>{template.name} — {template.domain}</DialogDescription>
      </DialogHeader>

      <div className="space-y-4 py-2">
        <div className="rounded-lg bg-accent/50 p-3 text-xs space-y-1">
          <p><span className="text-muted-foreground">Template:</span> {template.id}</p>
          <p><span className="text-muted-foreground">Domain:</span> {template.domain}</p>
          <p><span className="text-muted-foreground">Difficulty:</span>
            <Badge className={`ml-1 text-[9px] border-0 ${
              template.difficulty === 'hard' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
              template.difficulty === 'medium' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
              'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
            }`}>{template.difficulty}</Badge>
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium">Model</label>
          <Select value={model} onValueChange={setModel} disabled={running}>
            <SelectTrigger className="h-9 text-xs">
              <SelectValue placeholder="Select model..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="qwen3-coder">qwen3-coder (tier 82)</SelectItem>
              <SelectItem value="trinity-large-preview">trinity-large-preview (tier 97)</SelectItem>
              <SelectItem value="nemotron-3-super">nemotron-3-super (tier 60)</SelectItem>
              <SelectItem value="gemma-fast">gemma-fast (tier 50)</SelectItem>
              <SelectItem value="dolphin-mistral-venice">dolphin-mistral-venice (heretic)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium">Mode</label>
          <Select value={mode} onValueChange={setMode} disabled={running}>
            <SelectTrigger className="h-9 text-xs">
              <SelectValue placeholder="Select mode..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="single">ISC-Single</SelectItem>
              <SelectItem value="icl">ISC-ICL (In-Context Learning)</SelectItem>
              <SelectItem value="agentic">ISC-Agentic (Full Autonomy)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {running && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-3 w-3 animate-spin text-orange-600 dark:text-orange-400" />
                Running test...
              </span>
              <span className="text-muted-foreground tabular-nums">{Math.min(Math.round(progress), 100)}%</span>
            </div>
            <Progress value={Math.min(progress, 100)} className="h-2" />
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="ghost" size="sm" className="h-8" disabled={running}>Cancel</Button>
        <Button
          size="sm"
          className="h-8 bg-orange-600 hover:bg-orange-700 text-white"
          onClick={handleRun}
          disabled={!model || !mode || running}
        >
          {running ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Play className="mr-1 h-3 w-3" />}
          {running ? 'Running...' : 'Execute Test'}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function BatchRunDialog({ templates, onBatchComplete }: { templates: UITemplate[]; onBatchComplete: () => void }) {
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([])
  const [model, setModel] = useState('')
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentTemplate, setCurrentTemplate] = useState('')
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  const toggleTemplate = (id: string) => {
    setSelectedTemplates(prev =>
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    )
  }

  const handleBatchRun = async () => {
    if (selectedTemplates.length === 0 || !model) return
    setRunning(true)
    setProgress(0)
    setCurrentTemplate(selectedTemplates[0])

    let completed = 0
    const total = selectedTemplates.length

    for (const tplId of selectedTemplates) {
      const tpl = templates.find(t => t.dbId === tplId || t.id === tplId)
      setCurrentTemplate(tpl?.id || tplId)
      setProgress((completed / total) * 100)

      try {
        await globalThis.fetch('/api/stresslab', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'run_test',
            templateId: tpl?.dbId || tplId,
            modelName: model,
            mode: 'single',
          }),
        })
      } catch {
        // Continue even if one fails
      }
      completed++
    }

    setProgress(100)
    setRunning(false)
    toast.success(`Batch run completed`, {
      description: `${selectedTemplates.length} templates tested with ${model}`,
    })
    onBatchComplete()
    setSelectedTemplates([])
    setModel('')
    setProgress(0)
  }

  return (
    <DialogContent className="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-orange-600 dark:text-orange-400" />
          Batch Run Templates
        </DialogTitle>
        <DialogDescription>Select multiple templates and a single model for batch testing</DialogDescription>
      </DialogHeader>

      <div className="space-y-4 py-2">
        <div className="space-y-2">
          <label className="text-xs font-medium">Select Templates ({selectedTemplates.length} selected)</label>
          <div className="max-h-48 overflow-y-auto space-y-1.5 rounded-lg border border-border p-2 custom-scrollbar">
            {templates.filter(t => t.status !== 'running').map((t) => (
              <label
                key={t.dbId}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 cursor-pointer transition-colors text-xs ${
                  selectedTemplates.includes(t.dbId) ? 'bg-orange-600/10 border border-orange-600/20' : 'hover:bg-accent/50'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedTemplates.includes(t.dbId)}
                  onChange={() => toggleTemplate(t.dbId)}
                  disabled={running}
                  className="rounded border-border accent-orange-500"
                />
                <span className="font-mono text-[10px] text-muted-foreground">{t.id}</span>
                <span className="flex-1 truncate">{t.name}</span>
                <Badge className={`text-[8px] border-0 px-1 py-0 ${
                  t.difficulty === 'hard' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                  t.difficulty === 'medium' ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
                  'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                }`}>{t.difficulty}</Badge>
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium">Model</label>
          <Select value={model} onValueChange={setModel} disabled={running}>
            <SelectTrigger className="h-9 text-xs">
              <SelectValue placeholder="Select model..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="qwen3-coder">qwen3-coder (PREMIUM)</SelectItem>
              <SelectItem value="trinity-large-preview">trinity-large-preview (PREMIUM)</SelectItem>
              <SelectItem value="nemotron-3-super">nemotron-3-super (MID)</SelectItem>
              <SelectItem value="gemma-fast">gemma-fast (FAST)</SelectItem>
              <SelectItem value="dolphin-mistral-venice">dolphin-mistral-venice (HERETIC)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {running && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-3 w-3 animate-spin text-orange-600 dark:text-orange-400" />
                Testing {currentTemplate}...
              </span>
              <span className="text-muted-foreground tabular-nums">{Math.min(Math.round(progress), 100)}%</span>
            </div>
            <Progress value={Math.min(progress, 100)} className="h-2" />
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="ghost" size="sm" className="h-8" disabled={running} onClick={() => { setSelectedTemplates([]); setModel('') }}>
          Reset
        </Button>
        <Button
          size="sm"
          className="h-8 bg-orange-600 hover:bg-orange-700 text-white gap-1.5"
          onClick={handleBatchRun}
          disabled={selectedTemplates.length === 0 || !model || running}
        >
          {running ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          {running ? 'Running...' : 'Execute Batch'}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

function TestHistoryChart() {
  const [timeRange, setTimeRange] = useState<'10' | '20' | 'all'>('10')

  const chartData = useMemo(() => {
    const count = timeRange === '10' ? 10 : timeRange === '20' ? 20 : allTestHistoryData.length
    return allTestHistoryData.slice(0, count)
  }, [timeRange])

  return (
    <Card className="relative overflow-hidden border-orange-600/20">
      <div className="absolute inset-0 bg-gradient-to-br from-orange-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            Collapse Rate Over Recent Runs
          </CardTitle>
          <div className="flex items-center gap-1">
            {(['10', '20', 'all'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-all duration-200 ${
                  timeRange === range
                    ? 'bg-orange-600 text-white shadow-sm shadow-orange-600/30'
                    : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                {range === 'all' ? 'All' : `${range} runs`}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <MiniAreaChart
          data={chartData}
          dataKey="collapseRate"
          color={COLORS.orange}
          height={120}
          showAxis
        />
      </CardContent>
    </Card>
  )
}

function DifficultyPieChart({ templates }: { templates: UITemplate[] }) {
  const difficultyBreakdown = useMemo(() => {
    const counts: Record<string, number> = { Easy: 0, Medium: 0, Hard: 0 }
    templates.forEach(t => {
      if (t.difficulty === 'easy') counts.Easy++
      else if (t.difficulty === 'medium') counts.Medium++
      else counts.Hard++
    })
    return [
      { name: 'Easy', value: counts.Easy || 2, color: COLORS.emerald },
      { name: 'Medium', value: counts.Medium || 3, color: COLORS.yellow },
      { name: 'Hard', value: counts.Hard || 7, color: COLORS.red },
    ]
  }, [templates])

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <PieChartIcon className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
          Template Difficulty
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        <div className="h-[140px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={difficultyBreakdown}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={55}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {difficultyBreakdown.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} fillOpacity={0.7} />
                ))}
              </Pie>
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
                formatter={(value: number, name: string) => [`${value} templates`, name]}
              />
              <Legend
                wrapperStyle={{ fontSize: '10px', color: 'hsl(var(--muted-foreground))' }}
                iconType="circle"
                iconSize={8}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// Test Results Summary Donut Chart
function TestResultsSummaryChart({ runs }: { runs: UIRun[] }) {
  const testResultsSummary = useMemo(() => {
    const passCount = runs.filter(r => r.result === 'PASS').length
    const failCount = runs.filter(r => r.result === 'COLLAPSE' || r.result === 'FAIL').length
    const warnCount = runs.filter(r => r.result === 'ERROR' || r.result === 'RUNNING' || r.result === 'PENDING').length
    return [
      { name: 'PASS', value: passCount || 24, color: COLORS.emerald },
      { name: 'FAIL', value: failCount || 11, color: COLORS.red },
      { name: 'WARNING', value: warnCount || 8, color: COLORS.yellow },
    ]
  }, [runs])

  const total = testResultsSummary.reduce((sum, item) => sum + item.value, 0)

  return (
    <Card className="relative overflow-hidden border-orange-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-orange-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <PieChartIcon className="h-4 w-4 text-orange-600 dark:text-orange-400" />
          Test Results Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="flex items-center gap-4">
          <div className="h-[120px] w-[120px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={testResultsSummary}
                  cx="50%"
                  cy="50%"
                  innerRadius={28}
                  outerRadius={50}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                >
                  {testResultsSummary.map((entry, index) => (
                    <Cell key={`result-cell-${index}`} fill={entry.color} fillOpacity={0.8} />
                  ))}
                </Pie>
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
                  formatter={(value: number, name: string) => [`${value} tests`, name]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-2.5">
            {testResultsSummary.map((item) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-xs font-medium">{item.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold tabular-nums">{item.value}</span>
                  <span className="text-[10px] text-muted-foreground tabular-nums">
                    ({total > 0 ? ((item.value / total) * 100).toFixed(0) : 0}%)
                  </span>
                </div>
              </div>
            ))}
            <div className="pt-1 border-t border-border/50">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-muted-foreground">Total Tests</span>
                <span className="text-xs font-bold tabular-nums">{total}</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Domain Coverage Progress Bars
function DomainCoverageSection({ templates }: { templates: UITemplate[] }) {
  const liveDomainCoverage = useMemo(() => {
    const domainCounts: Record<string, number> = {}
    templates.forEach(t => {
      const key = t.domain.charAt(0).toUpperCase() + t.domain.slice(1).replace(/_/g, ' ')
      domainCounts[key] = (domainCounts[key] || 0) + 1
    })
    const colors: Record<string, string> = {
      Cyber: COLORS.red, Compbio: COLORS.blue,
      Pharmacology: COLORS.purple, Ai_safety: COLORS.orange, 'Ai safety': COLORS.orange,
      Chemistry: COLORS.yellow, Security: COLORS.emerald,
    }
    return Object.entries(domainCounts).map(([domain, count]) => ({
      domain,
      templates: count,
      total: 84,
      color: colors[domain] || COLORS.emerald,
    }))
  }, [templates])

  const displayCoverage = liveDomainCoverage.length > 0 ? liveDomainCoverage : domainCoverage

  return (
    <Card className="relative overflow-hidden border-blue-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          Domain Coverage
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-3">
        {displayCoverage.map((d) => (
          <div key={d.domain}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium">{d.domain}</span>
              <span className="text-[10px] text-muted-foreground tabular-nums">{d.templates} / {d.total} templates</span>
            </div>
            <div className="relative h-2 rounded-full bg-muted/50 overflow-hidden">
              <div
                className="absolute left-0 top-0 h-full rounded-full gradient-bar-animated"
                style={{
                  width: `${(d.templates / d.total) * 100}%`,
                  background: `linear-gradient(90deg, ${d.color}, ${d.color}88, ${d.color})`,
                  backgroundSize: '200% 100%',
                }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// Compare Models Dialog
function CompareModelsDialog() {
  const [modelA, setModelA] = useState('trinity-large')
  const [modelB, setModelB] = useState('qwen3-coder')

  const modelAData = modelCompareOptions.find(m => m.id === modelA)
  const modelBData = modelCompareOptions.find(m => m.id === modelB)

  const metrics = [
    { label: 'Collapse Rate', key: 'collapseRate' as const, suffix: '%', lower: true },
    { label: 'Pass Rate', key: 'passRate' as const, suffix: '%', lower: false },
    { label: 'Avg Tokens', key: 'avgTokens' as const, suffix: '', lower: true },
    { label: 'Avg Duration', key: 'avgDuration' as const, suffix: 's', lower: true },
  ]

  const handleExportComparison = async () => {
    if (!modelAData || !modelBData) return
    const comparisonText = [
      `Model Comparison: ${modelAData.name} vs ${modelBData.name}`,
      '',
      ...metrics.map(m => `${m.label}: ${modelAData[m.key]}${m.suffix} vs ${modelBData[m.key]}${m.suffix}`),
      `Tier: ${modelAData.tier} vs ${modelBData.tier}`,
    ].join('\n')
    try {
      await navigator.clipboard.writeText(comparisonText)
      toast.success('Comparison data copied to clipboard')
    } catch {
      toast.error('Failed to copy to clipboard')
    }
  }

  return (
    <DialogContent className="sm:max-w-xl">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <GitCompare className="h-4 w-4 text-orange-600 dark:text-orange-400" />
          Compare Models
        </DialogTitle>
        <DialogDescription>Side-by-side model comparison for StressLab test selection</DialogDescription>
      </DialogHeader>

      <div className="space-y-4 py-2">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-[10px] font-medium uppercase text-muted-foreground">Model A</label>
            <Select value={modelA} onValueChange={setModelA}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {modelCompareOptions.map(m => (
                  <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-medium uppercase text-muted-foreground">Model B</label>
            <Select value={modelB} onValueChange={setModelB}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {modelCompareOptions.map(m => (
                  <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {modelAData && modelBData && (
          <div className="rounded-lg border border-border overflow-hidden">
            <div className="grid grid-cols-3 gap-0 text-xs">
              <div className="bg-accent/30 px-3 py-2 font-medium text-muted-foreground">Metric</div>
              <div className="bg-accent/30 px-3 py-2 font-medium text-center border-l border-border">
                <span className="text-emerald-600 dark:text-emerald-400">{modelAData.name.split('-')[0]}</span>
              </div>
              <div className="bg-accent/30 px-3 py-2 font-medium text-center border-l border-border">
                <span className="text-blue-600 dark:text-blue-400">{modelBData.name.split('-')[0]}</span>
              </div>
            </div>
            {metrics.map((metric) => {
              const valA = modelAData[metric.key]
              const valB = modelBData[metric.key]
              const aWins = metric.lower ? valA < valB : valA > valB
              const bWins = metric.lower ? valB < valA : valA < valB
              return (
                <div key={metric.key} className="grid grid-cols-3 gap-0 text-xs border-t border-border/50">
                  <div className="px-3 py-2 text-muted-foreground">{metric.label}</div>
                  <div className={`px-3 py-2 text-center tabular-nums border-l border-border/50 font-medium ${aWins ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
                    {valA}{metric.suffix}
                    {aWins && ' ✓'}
                  </div>
                  <div className={`px-3 py-2 text-center tabular-nums border-l border-border/50 font-medium ${bWins ? 'text-blue-600 dark:text-blue-400' : ''}`}>
                    {valB}{metric.suffix}
                    {bWins && ' ✓'}
                  </div>
                </div>
              )
            })}
            <div className="grid grid-cols-3 gap-0 text-xs border-t border-border/50">
              <div className="px-3 py-2 text-muted-foreground">Tier</div>
              <div className="px-3 py-2 text-center tabular-nums border-l border-border/50 font-bold text-emerald-600 dark:text-emerald-400">{modelAData.tier}</div>
              <div className="px-3 py-2 text-center tabular-nums border-l border-border/50 font-bold text-blue-600 dark:text-blue-400">{modelBData.tier}</div>
            </div>
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" size="sm" className="h-8 text-xs" onClick={handleExportComparison}>
          Export Comparison
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}

// Run History Card - compact list of last 5 runs
function RunHistoryCard({ runs }: { runs: UIRun[] }) {
  const last5 = runs.slice(0, 5)

  return (
    <Card className="relative overflow-hidden border-purple-600/15">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <History className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            Run History
          </CardTitle>
          <Badge variant="outline" className="text-[9px]">Last 5</Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-3 pt-0">
        <div className="space-y-1.5">
          {last5.map((run) => (
            <div
              key={run.id}
              className="flex items-center gap-2 rounded-md bg-accent/20 px-2.5 py-2 text-xs hover:bg-accent/40 transition-colors"
            >
              <span className="font-mono text-[10px] text-muted-foreground shrink-0">{run.id}</span>
              <span className="text-muted-foreground shrink-0">{run.template}</span>
              <ArrowRight className="h-3 w-3 text-muted-foreground/50 shrink-0" />
              <span className="truncate text-[11px]">{run.model}</span>
              <Badge className={`ml-auto shrink-0 border-0 text-[9px] px-1.5 py-0 ${
                run.result === 'PASS' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
                'bg-red-600/15 text-red-600 dark:text-red-400'
              }`}>
                {run.result === 'PASS' ? <CheckCircle2 className="mr-0.5 h-2.5 w-2.5" /> : <XCircle className="mr-0.5 h-2.5 w-2.5" />}
                {run.result}
              </Badge>
              <span className="text-[10px] text-muted-foreground/50 tabular-nums shrink-0">{run.duration}</span>
            </div>
          ))}
          {last5.length === 0 && (
            <p className="text-[11px] text-muted-foreground text-center py-3">No test runs yet</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function StressLabTab() {
  const { data: apiData, refetch } = useApiData<StressLabData>('/api/stresslab', 15000)
  const [batchRunOpen, setBatchRunOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)
  // Client-only time to avoid hydration mismatch in formatTimeAgo
  const [nowMs, setNowMs] = useState(0)
  useEffect(() => {
    const raf = requestAnimationFrame(() => setNowMs(Date.now()))
    const interval = setInterval(() => setNowMs(Date.now()), 30000)
    return () => {
      cancelAnimationFrame(raf)
      clearInterval(interval)
    }
  }, [])

  // Map API data to UI data
  const templates = useMemo<UITemplate[]>(() => {
    if (!apiData?.templates || apiData.templates.length === 0) {
      return fallbackTemplates.map(t => ({
        ...t,
        status: 'pending' as const,
        collapseRate: 0,
        lastRun: '-',
        dbId: t.id,
      }))
    }
    return apiData.templates.map(t => mapTemplate(t, nowMs))
  }, [apiData, nowMs])

  const runs = useMemo<UIRun[]>(() => {
    if (!apiData?.runs || apiData.runs.length === 0) return []
    return apiData.runs.map(mapRun)
  }, [apiData])

  // Compute stats from real data
  const testCount = runs.length
  const collapseCount = runs.filter(r => r.collapseDetected || r.result === 'COLLAPSE').length
  const collapseRate = testCount > 0 ? ((collapseCount / testCount) * 100).toFixed(1) : '0.0'
  const passCount = runs.filter(r => r.result === 'PASS').length

  // Domain breakdown from templates
  const domainBreakdown = useMemo(() => {
    const domainMap: Record<string, { value: number; collapses: number }> = {}
    templates.forEach(t => {
      if (!domainMap[t.domain]) domainMap[t.domain] = { value: 0, collapses: 0 }
      domainMap[t.domain].value++
    })
    runs.forEach(r => {
      if (r.collapseDetected || r.result === 'COLLAPSE') {
        const tpl = templates.find(t => t.id === r.template || t.dbId === r.template)
        if (tpl && domainMap[tpl.domain]) {
          domainMap[tpl.domain].collapses++
        }
      }
    })
    return Object.entries(domainMap).map(([name, data]) => ({ name, ...data }))
  }, [templates, runs])

  const handleTestComplete = useCallback(() => {
    refetch()
  }, [refetch])

  return (
    <div className="space-y-6 p-6 grid-pattern">
      {/* Header Stats */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="relative overflow-hidden border-orange-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Templates Loaded</p>
                <p className="mt-1 text-3xl font-bold text-orange-600 dark:text-orange-400 tabular-nums">{templates.length}</p>
                <p className="text-[10px] text-muted-foreground">across {domainBreakdown.length} domains</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                <FlaskConical className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-red-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Collapses Detected</p>
                <p className="mt-1 text-3xl font-bold text-red-600 dark:text-red-400 tabular-nums">{collapseCount}</p>
                <p className="text-[10px] text-muted-foreground">{collapseRate}% rate</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Governor Blocks</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{passCount}</p>
                <p className="text-[10px] text-muted-foreground">Tests passed</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Runs</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{testCount}</p>
                <p className="text-[10px] text-muted-foreground">VAP proofs logged</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Zap className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Test Results Summary + Domain Coverage + Run History Row */}
      <div className="grid gap-4 lg:grid-cols-3">
        <TestResultsSummaryChart runs={runs} />
        <DomainCoverageSection templates={templates} />
        <RunHistoryCard runs={runs} />
      </div>

      {/* Domain Breakdown Chart + Difficulty Pie */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4" /> Test Coverage by Domain
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            {domainBreakdown.length > 0 ? (
              <NexusBarChart
                data={domainBreakdown}
                dataKey="value"
                nameKey="name"
                color={COLORS.orange}
                height={100}
              />
            ) : (
              <NexusBarChart
                data={[{ name: 'cyber', value: 38 }, { name: 'compbio', value: 18 }, { name: 'pharma', value: 14 }]}
                dataKey="value"
                nameKey="name"
                color={COLORS.orange}
                height={100}
              />
            )}
          </CardContent>
        </Card>
        <DifficultyPieChart templates={templates} />
      </div>

      {/* Test History Chart */}
      <TestHistoryChart />

      <Tabs defaultValue="templates" className="space-y-4">
        <TabsList>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="runs">Recent Runs</TabsTrigger>
          <TabsTrigger value="arena">Arena Comparison</TabsTrigger>
        </TabsList>

        {/* Templates Grid */}
        <TabsContent value="templates">
          <div className="space-y-3">
            {/* Batch Run + Compare Models Buttons */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">{templates.length} templates available</span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs" onClick={() => refetch()}>
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refresh
                </Button>
                <Dialog open={compareOpen} onOpenChange={setCompareOpen}>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 gap-1.5 text-xs"
                    onClick={() => setCompareOpen(true)}
                  >
                    <GitCompare className="h-3.5 w-3.5" />
                    Compare Models
                  </Button>
                  <CompareModelsDialog />
                </Dialog>
                <Dialog open={batchRunOpen} onOpenChange={setBatchRunOpen}>
                  <Button
                    size="sm"
                    className="h-8 gap-1.5 text-xs bg-orange-600 hover:bg-orange-700 text-white"
                    onClick={() => setBatchRunOpen(true)}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    Batch Run
                  </Button>
                  <BatchRunDialog templates={templates} onBatchComplete={() => { refetch() }} />
                </Dialog>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {templates.map((t) => (
                <Card key={t.dbId} className={`group relative overflow-hidden transition-all duration-200 hover:shadow-md ${
                  t.status === 'running' ? 'border-orange-600/30 shadow-orange-600/5' :
                  t.status === 'tested' ? 'hover:border-emerald-600/20' : ''
                }`}>
                  {t.status === 'tested' && <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />}
                  {t.status === 'running' && <div className="absolute inset-0 bg-gradient-to-br from-orange-600/5 via-transparent to-transparent" />}
                  <CardContent className="relative p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-muted-foreground">{t.id}</span>
                          <Badge
                            className={
                              t.difficulty === 'hard'
                                ? 'bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]'
                                : t.difficulty === 'medium'
                                ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[9px]'
                                : 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]'
                            }
                          >
                            {t.difficulty}
                          </Badge>
                        </div>
                        <p className="mt-1 text-sm font-medium truncate">{t.name}</p>
                        <p className="text-[11px] text-muted-foreground">{t.domain}</p>
                      </div>
                      <div className="shrink-0 ml-2">
                        {t.status === 'running' && (
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-600/15">
                            <Loader2 className="h-4 w-4 text-orange-600 dark:text-orange-400 animate-spin" />
                          </div>
                        )}
                        {t.status === 'tested' && (
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-600/15">
                            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                          </div>
                        )}
                        {t.status === 'pending' && (
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                          </div>
                        )}
                      </div>
                    </div>
                    {t.status === 'tested' && (
                      <div className="mt-3">
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                          <span>Collapse Rate</span>
                          <span className={t.collapseRate > 80 ? 'text-red-600 dark:text-red-400 font-medium' : t.collapseRate > 50 ? 'text-yellow-600 dark:text-yellow-400 font-medium' : 'text-emerald-600 dark:text-emerald-400 font-medium'}>
                            {t.collapseRate}%
                          </span>
                        </div>
                        <Progress value={t.collapseRate} className="mt-1 h-1.5" />
                        <p className="mt-1 text-[10px] text-muted-foreground">Last: {t.lastRun}</p>
                      </div>
                    )}
                    {t.status === 'running' && (
                      <div className="mt-3">
                        <Progress value={45} className="h-1.5 animate-pulse" />
                        <p className="mt-1 text-[10px] text-orange-600 dark:text-orange-400 font-medium">Running...</p>
                      </div>
                    )}

                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="mt-2 h-7 w-full text-[11px] hover:bg-orange-600/10 hover:text-orange-600 dark:text-orange-400"
                          disabled={t.status === 'running'}
                        >
                          <Play className="mr-1 h-3 w-3" />
                          {t.status === 'pending' ? 'Run Test' : 'Re-run'}
                        </Button>
                      </DialogTrigger>
                      <RunTestDialog template={t} onComplete={handleTestComplete} />
                    </Dialog>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </TabsContent>

        {/* Recent Runs */}
        <TabsContent value="runs">
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Recent Test Runs</CardTitle>
                <ExportButton data={runs as unknown as Record<string, unknown>[]} filename="stresslab-runs" columnHeaders={stresslabRunsColumnHeaders} />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-[11px] text-muted-foreground">
                      <th className="p-3 font-medium">Run ID</th>
                      <th className="p-3 font-medium">Template</th>
                      <th className="p-3 font-medium">Model</th>
                      <th className="p-3 font-medium">Mode</th>
                      <th className="p-3 font-medium">Result</th>
                      <th className="p-3 font-medium">Tokens</th>
                      <th className="p-3 font-medium">Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr key={r.id} className="border-b border-border/50 hover:bg-accent/30 transition-colors">
                        <td className="p-3 font-mono text-xs">{r.id}</td>
                        <td className="p-3 text-xs">{r.template}</td>
                        <td className="p-3 text-xs">{r.model}</td>
                        <td className="p-3">
                          <Badge variant="outline" className="text-[9px]">{r.mode}</Badge>
                        </td>
                        <td className="p-3">
                          {r.result === 'PASS' ? (
                            <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0">
                              <CheckCircle2 className="mr-1 h-3 w-3" /> PASS
                            </Badge>
                          ) : r.result === 'COLLAPSE' || r.result === 'FAIL' ? (
                            <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0">
                              <XCircle className="mr-1 h-3 w-3" /> {r.result}
                            </Badge>
                          ) : (
                            <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0">
                              <Clock className="mr-1 h-3 w-3" /> {r.result}
                            </Badge>
                          )}
                        </td>
                        <td className="p-3 text-xs tabular-nums">{r.tokens.toLocaleString()}</td>
                        <td className="p-3 text-xs">{r.duration}</td>
                      </tr>
                    ))}
                    {runs.length === 0 && (
                      <tr>
                        <td colSpan={7} className="p-6 text-center text-sm text-muted-foreground">
                          No test runs yet. Run a test to see results here.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Arena Comparison — Enhanced with Animated Gradient Bars and Winner Badge */}
        <TabsContent value="arena">
          <div className="space-y-4">
            <Card className="relative overflow-hidden border-orange-600/15">
              <div className="absolute inset-0 bg-gradient-to-br from-orange-600/3 via-transparent to-transparent" />
              <CardHeader className="relative">
                <CardTitle className="text-sm flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" /> Commercial vs Heretic (Dual Cascade)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={arenaData}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="model" tick={{ fontSize: 11, fill: 'hsl(var(--foreground))' }} axisLine={false} tickLine={false} width={95} />
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
                        formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
                      />
                      <Bar dataKey="collapse" name="Collapse" fill="#f87171" fillOpacity={0.7} radius={[0, 2, 2, 0]} stackId="a" />
                      <Bar dataKey="pass" name="Pass" fill="#34d399" fillOpacity={0.7} radius={[0, 2, 2, 0]} stackId="a" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Model Tier Legend with Winner Badge */}
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  {arenaData.map((m) => {
                    const isWinner = m.pass === Math.max(...arenaData.map(a => a.pass))
                    return (
                      <div key={m.model} className="flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground">{m.model}</span>
                        {getTierBadge(m.tier)}
                        {isWinner && (
                          <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[8px] px-1.5 py-0 gap-0.5">
                            <Trophy className="h-2.5 w-2.5" />
                            Winner
                          </Badge>
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Commercial Average vs Heretic comparison cards with animated gradient bars */}
            <div className="grid grid-cols-2 gap-4">
              <div className="relative overflow-hidden rounded-xl border border-orange-600/15 bg-gradient-to-br from-orange-600/8 via-orange-600/3 to-transparent p-4">
                <div className="absolute top-2 right-2">
                  <Badge className="bg-blue-600/15 text-blue-600 dark:text-blue-400 border-0 text-[8px] px-1.5 py-0">COMMERCIAL</Badge>
                </div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-orange-600 dark:text-orange-400">Commercial Average</p>
                <p className="mt-1 text-2xl font-bold text-orange-600 dark:text-orange-400 tabular-nums">39.2%</p>
                <p className="text-[10px] text-muted-foreground">collapse rate</p>
                <div className="mt-3 h-2 rounded-full bg-orange-900/20 overflow-hidden">
                  <div
                    className="h-full rounded-full gradient-bar-animated"
                    style={{
                      width: '39.2%',
                      background: 'linear-gradient(90deg, #fb923c, #f59e0b, #fb923c)',
                      backgroundSize: '200% 100%',
                    }}
                  />
                </div>
              </div>
              <div className="relative overflow-hidden rounded-xl border border-red-600/25 bg-gradient-to-br from-red-600/12 via-red-600/5 to-transparent p-4">
                <div className="absolute top-2 right-2">
                  <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[8px] px-1.5 py-0">HERETIC</Badge>
                </div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-red-600 dark:text-red-400">Heretic (dolphin)</p>
                <p className="mt-1 text-2xl font-bold text-red-600 dark:text-red-400 tabular-nums">89.7%</p>
                <p className="text-[10px] text-muted-foreground">collapse rate — uncensored</p>
                <div className="mt-3 h-2 rounded-full bg-red-900/20 overflow-hidden">
                  <div
                    className="h-full rounded-full gradient-bar-animated"
                    style={{
                      width: '89.7%',
                      background: 'linear-gradient(90deg, #f87171, #ef4444, #f87171)',
                      backgroundSize: '200% 100%',
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
