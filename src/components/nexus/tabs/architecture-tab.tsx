'use client'

import { useState, useCallback, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Boxes,
  Activity,
  Shield,
  Zap,
  Server,
  Users,
  ArrowRight,
  Brain,
  Globe,
  Lock,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Eye,
  ChevronDown,
  ChevronUp,
  Cpu,
  Network,
  Layers,
  GitBranch,
  Monitor,
  Radio,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────

type HealthStatus = 'healthy' | 'degraded' | 'down'

interface ArchNode {
  id: string
  label: string
  description: string
  health: HealthStatus
  details?: string
  meta?: string
}

// ─── Health Color Helpers ─────────────────────────────────────────────────

const HEALTH_COLORS: Record<HealthStatus, { text: string; bg: string; border: string; dot: string; badge: string }> = {
  healthy: {
    text: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-600/10 hover:bg-emerald-600/20',
    border: 'border-emerald-600/30',
    dot: 'bg-emerald-400',
    badge: 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400',
  },
  degraded: {
    text: 'text-yellow-600 dark:text-yellow-400',
    bg: 'bg-yellow-600/10 hover:bg-yellow-600/20',
    border: 'border-yellow-600/30',
    dot: 'bg-yellow-400',
    badge: 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400',
  },
  down: {
    text: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-600/10 hover:bg-red-600/20',
    border: 'border-red-600/30',
    dot: 'bg-red-400',
    badge: 'bg-red-600/20 text-red-600 dark:text-red-400',
  },
}

const HEALTH_ICONS: Record<HealthStatus, React.ReactNode> = {
  healthy: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
  degraded: <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />,
  down: <XCircle className="h-3.5 w-3.5 text-red-500" />,
}

// ─── Mock Data ────────────────────────────────────────────────────────────

const PROVIDERS: ArchNode[] = [
  { id: 'zai', label: 'Z-AI', description: 'GLM-4.7, GLM-5', health: 'healthy', details: '2 models · Free tier · 250ms avg', meta: 'Primary' },
  { id: 'nvidia', label: 'NVIDIA NIM', description: 'Nemotron-4, Llama 3.3, etc.', health: 'healthy', details: '4 models · Free tier · 200ms avg', meta: 'Tier 1' },
  { id: 'openrouter', label: 'OpenRouter', description: 'Nemotron Super, DeepSeek, Gemini', health: 'healthy', details: '3 models · Credits · 180ms avg', meta: 'Tier 1' },
  { id: 'groq', label: 'Groq', description: 'Llama 3.3, Mixtral 8x7B', health: 'healthy', details: '2 models · $0.59/1M · 80ms avg', meta: 'Fast' },
  { id: 'cerebras', label: 'Cerebras', description: 'Llama 3.3 70B, Llama 3.1 8B', health: 'healthy', details: '2 models · $0.60/1M · 40ms avg', meta: 'Fastest' },
  { id: 'sambanova', label: 'SambaNova', description: 'DeepSeek V3, Llama 3.3', health: 'healthy', details: '2 models · Free tier · 150ms avg', meta: 'Free' },
  { id: 'deepseek', label: 'DeepSeek', description: 'DeepSeek Chat, Reasoner', health: 'healthy', details: '2 models · $0.27/1M · 200ms avg', meta: 'Reasoning' },
  { id: 'openai', label: 'OpenAI', description: 'GPT-4o-mini', health: 'healthy', details: '1 model · $0.15/1M · 300ms avg', meta: 'Fallback' },
  { id: 'fireworks', label: 'Fireworks AI', description: 'Llama 3.1, Qwen2.5', health: 'degraded', details: '2 models · $0.20/1M · 140ms avg', meta: 'Degraded' },
  { id: 'siliconflow', label: 'SiliconFlow', description: 'DeepSeek V3, Qwen2.5', health: 'healthy', details: '2 models · $0.30/1M · 180ms avg', meta: 'China' },
  { id: 'mistral', label: 'Mistral AI', description: 'Mistral Medium', health: 'healthy', details: '1 model · $0.40/1M · 220ms avg', meta: 'EU' },
  { id: 'codestral', label: 'Codestral', description: 'Codestral Latest', health: 'healthy', details: '1 model · $0.30/1M · 180ms avg', meta: 'Code' },
  { id: 'bitdeer', label: 'Bitdeer AI', description: 'Bitdeer Default', health: 'healthy', details: '1 model · Free · 300ms avg', meta: 'GPU' },
  { id: 'scaleway', label: 'Scaleway', description: 'Scaleway Models', health: 'down', details: '0 models · Offline · —', meta: 'Down' },
]

const AGENTS: ArchNode[] = [
  { id: 'coordinator', label: 'Coordinator', description: 'glm-4.7', health: 'healthy', details: 'Orchestration & task routing · Trust: 0.95', meta: 'Active' },
  { id: 'worker-1', label: 'worker-1', description: 'trinity-large', health: 'healthy', details: 'Reasoning & analysis tasks · Trust: 0.88', meta: 'Active' },
  { id: 'worker-2', label: 'worker-2', description: 'qwen3-coder', health: 'degraded', details: 'Code generation & review · Trust: 0.71', meta: 'Warning' },
  { id: 'worker-3', label: 'worker-3', description: 'gemma-fast', health: 'healthy', details: 'Fast response & summaries · Trust: 0.82', meta: 'Active' },
]

const GOV_NODES: ArchNode[] = [
  { id: 'governor', label: 'Governor', description: 'Constitutional AI', health: 'healthy', details: '7 active rules · 3 blocks today', meta: 'Enforcing' },
  { id: 'rules', label: 'Rules Engine', description: '7 constitutional rules', health: 'healthy', details: 'Max agents: 5 · Max calls: 20/min · Max writes: 30/min', meta: 'Active' },
  { id: 'enforcement', label: 'Enforcement', description: 'Block & audit', health: 'healthy', details: '12 actions blocked · 0 violations unlogged', meta: 'Strict' },
  { id: 'audit', label: 'Audit Log', description: 'Full audit trail', health: 'healthy', details: '847 entries · 30-day retention', meta: 'Logging' },
]

// ─── Node Component ───────────────────────────────────────────────────────

function ArchNodeBox({ node, compact = false }: { node: ArchNode; compact?: boolean }) {
  const [hovered, setHovered] = useState(false)
  const colors = HEALTH_COLORS[node.health]

  return (
    <div
      className={cn(
        'relative rounded-lg border p-2.5 transition-all duration-200 cursor-default',
        colors.bg,
        colors.border,
        hovered && 'scale-105 shadow-lg z-10',
      )}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex items-center gap-2">
        <span className={cn('h-2 w-2 rounded-full shrink-0', colors.dot)} />
        <span className="text-xs font-semibold truncate">{node.label}</span>
        {node.meta && (
          <Badge className={cn('h-3.5 px-1 text-[8px] border-0 shrink-0', colors.badge)}>
            {node.meta}
          </Badge>
        )}
      </div>
      {!compact && (
        <div className="text-[10px] text-muted-foreground mt-1 truncate">{node.description}</div>
      )}

      {/* Tooltip on hover */}
      {hovered && (
        <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-50 w-56 rounded-lg border border-border bg-card p-3 shadow-xl animate-in fade-in-0 zoom-in-95 duration-150">
          <div className="flex items-center gap-2 mb-1.5">
            {HEALTH_ICONS[node.health]}
            <span className="text-xs font-semibold">{node.label}</span>
            <Badge className={cn('text-[8px] border-0 ml-auto', colors.badge)}>
              {node.health.toUpperCase()}
            </Badge>
          </div>
          <p className="text-[10px] text-muted-foreground mb-1">{node.description}</p>
          {node.details && (
            <p className="text-[10px] text-muted-foreground/70 border-t border-border/30 pt-1 mt-1">
              {node.details}
            </p>
          )}
          <div className="absolute left-1/2 -translate-x-1/2 top-full w-2 h-2 rotate-45 border-b border-r border-border bg-card -mt-1" />
        </div>
      )}
    </div>
  )
}

// ─── Flow Arrow ───────────────────────────────────────────────────────────

function FlowArrow({ label, vertical = false }: { label?: string; vertical?: boolean }) {
  if (vertical) {
    return (
      <div className="flex flex-col items-center py-1">
        <div className="w-px h-4 bg-gradient-to-b from-emerald-500/50 to-emerald-500/20" />
        <ArrowRight className="h-3 w-3 text-emerald-500/50 rotate-90 -mt-1" />
        {label && <span className="text-[8px] text-muted-foreground/50 mt-0.5">{label}</span>}
      </div>
    )
  }
  return (
    <div className="flex items-center px-1">
      <div className="w-4 h-px bg-gradient-to-r from-emerald-500/50 to-emerald-500/20" />
      <ArrowRight className="h-3 w-3 text-emerald-500/40 shrink-0" />
      {label && <span className="text-[8px] text-muted-foreground/50 ml-1">{label}</span>}
    </div>
  )
}

// ─── Section Header ───────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-600/10">
        <Icon className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
      </div>
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-[10px] text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────

export function ArchitectureTab() {
  const [showProviders, setShowProviders] = useState(true)
  const [showAgents, setShowAgents] = useState(true)
  const [showDataFlow, setShowDataFlow] = useState(true)
  const [showGovernance, setShowGovernance] = useState(true)
  const [healthPercent, setHealthPercent] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  // Calculate health stats
  const allNodes = [...PROVIDERS, ...AGENTS, ...GOV_NODES]
  const healthyCount = allNodes.filter(n => n.health === 'healthy').length
  const degradedCount = allNodes.filter(n => n.health === 'degraded').length
  const downCount = allNodes.filter(n => n.health === 'down').length
  const totalComponents = allNodes.length
  const totalConnections = PROVIDERS.length + AGENTS.length + GOV_NODES.length + 4 // +4 for gateway, dashboard, user, coordinator

  useEffect(() => {
    setHealthPercent(Math.round((healthyCount / totalComponents) * 100))
  }, [healthyCount, totalComponents])

  const handleRefresh = useCallback(() => {
    setRefreshing(true)
    setTimeout(() => setRefreshing(false), 1500)
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Boxes className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold">System Architecture</h2>
          <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
            LIVE
          </Badge>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5 h-8"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          <RefreshCw className={cn('h-3 w-3', refreshing && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Components', value: totalComponents, icon: Layers, color: 'text-emerald-600' },
          { label: 'Connections', value: totalConnections, icon: GitBranch, color: 'text-blue-600' },
          { label: 'Health', value: `${healthPercent}%`, icon: Activity, color: 'text-emerald-600', bar: true, barValue: healthPercent },
          { label: 'Alerts', value: degradedCount + downCount, icon: AlertTriangle, color: degradedCount + downCount > 0 ? 'text-yellow-600' : 'text-emerald-600' },
        ].map((stat) => (
          <Card key={stat.label} className="bg-card/50 border-border/50">
            <CardContent className="p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <stat.icon className={cn('h-3.5 w-3.5', stat.color)} />
                <span className="text-[10px] text-muted-foreground">{stat.label}</span>
              </div>
              <div className="text-lg font-bold tabular-nums">{stat.value}</div>
              {stat.bar && (
                <Progress value={stat.barValue} className="h-1 mt-1.5" />
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ─── Section 1: System Topology ──────────────────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <SectionHeader
              icon={Network}
              title="System Topology"
              description="User → Dashboard → ModelRelay Gateway → Providers → Models"
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] gap-1"
              onClick={() => setShowProviders(!showProviders)}
            >
              {showProviders ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        </CardHeader>
        {showProviders && (
          <CardContent className="p-4 pt-0">
            {/* Topology Flow */}
            <div className="flex flex-col items-center gap-3">
              {/* Row 1: User → Dashboard → Gateway */}
              <div className="flex items-center justify-center gap-1 flex-wrap">
                {/* User */}
                <div className="flex flex-col items-center">
                  <div className="rounded-lg border border-emerald-600/30 bg-emerald-600/10 p-3 flex flex-col items-center min-w-[80px]">
                    <Users className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mb-1" />
                    <span className="text-xs font-semibold">User</span>
                    <span className="text-[9px] text-muted-foreground">Browser Client</span>
                  </div>
                </div>

                <FlowArrow label="HTTP" />

                {/* Dashboard */}
                <div className="flex flex-col items-center">
                  <div className="rounded-lg border border-emerald-600/30 bg-emerald-600/10 p-3 flex flex-col items-center min-w-[100px]">
                    <Monitor className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mb-1" />
                    <span className="text-xs font-semibold">Dashboard</span>
                    <span className="text-[9px] text-muted-foreground">Next.js Frontend</span>
                    <Badge className="mt-1 h-3 px-1 text-[7px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
                      15 TABS
                    </Badge>
                  </div>
                </div>

                <FlowArrow label="API" />

                {/* ModelRelay Gateway */}
                <div className="flex flex-col items-center">
                  <div className="rounded-lg border-2 border-emerald-500/40 bg-emerald-500/15 p-3 flex flex-col items-center min-w-[120px] shadow-md shadow-emerald-500/10">
                    <Radio className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mb-1" />
                    <span className="text-xs font-bold">ModelRelay</span>
                    <span className="text-[9px] text-muted-foreground">Gateway Router</span>
                    <div className="flex gap-1 mt-1">
                      <Badge className="h-3 px-1 text-[7px] bg-violet-600/20 text-violet-600 dark:text-violet-400 border-0">QUOTA</Badge>
                      <Badge className="h-3 px-1 text-[7px] bg-cyan-600/20 text-cyan-600 dark:text-cyan-400 border-0">COST</Badge>
                      <Badge className="h-3 px-1 text-[7px] bg-amber-600/20 text-amber-600 dark:text-amber-400 border-0">FAST</Badge>
                    </div>
                  </div>
                </div>
              </div>

              {/* Arrow down to providers */}
              <div className="flex flex-col items-center">
                <div className="w-px h-6 bg-gradient-to-b from-emerald-500/40 to-emerald-500/10" />
                <ArrowRight className="h-3 w-3 text-emerald-500/40 rotate-90 -mt-1" />
                <span className="text-[9px] text-muted-foreground mt-0.5">Routes to 14 providers</span>
              </div>

              {/* Providers Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 w-full">
                {PROVIDERS.map((provider) => (
                  <ArchNodeBox key={provider.id} node={provider} compact />
                ))}
              </div>

              {/* Arrow down to models */}
              <div className="flex flex-col items-center">
                <div className="w-px h-6 bg-gradient-to-b from-emerald-500/40 to-emerald-500/10" />
                <ArrowRight className="h-3 w-3 text-emerald-500/40 rotate-90 -mt-1" />
                <span className="text-[9px] text-muted-foreground mt-0.5">24 models across all providers</span>
              </div>

              {/* Models summary */}
              <div className="grid grid-cols-3 gap-3 w-full max-w-lg">
                <div className="rounded-lg border border-violet-600/20 bg-violet-600/5 p-3 text-center">
                  <Cpu className="h-4 w-4 text-violet-600 dark:text-violet-400 mx-auto mb-1" />
                  <div className="text-lg font-bold">8</div>
                  <div className="text-[9px] text-muted-foreground">Premium</div>
                  <Badge className="mt-1 h-3 px-1 text-[7px] bg-violet-600/20 text-violet-600 dark:text-violet-400 border-0">Tier 85+</Badge>
                </div>
                <div className="rounded-lg border border-blue-600/20 bg-blue-600/5 p-3 text-center">
                  <Brain className="h-4 w-4 text-blue-600 dark:text-blue-400 mx-auto mb-1" />
                  <div className="text-lg font-bold">10</div>
                  <div className="text-[9px] text-muted-foreground">Mid-tier</div>
                  <Badge className="mt-1 h-3 px-1 text-[7px] bg-blue-600/20 text-blue-600 dark:text-blue-400 border-0">Tier 65-84</Badge>
                </div>
                <div className="rounded-lg border border-amber-600/20 bg-amber-600/5 p-3 text-center">
                  <Zap className="h-4 w-4 text-amber-600 dark:text-amber-400 mx-auto mb-1" />
                  <div className="text-lg font-bold">6</div>
                  <div className="text-[9px] text-muted-foreground">Fast</div>
                  <Badge className="mt-1 h-3 px-1 text-[7px] bg-amber-600/20 text-amber-600 dark:text-amber-400 border-0">&lt;100ms</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* ─── Section 2: Agent Architecture ────────────────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <SectionHeader
              icon={Users}
              title="Agent Architecture"
              description="Swarm of AI agents coordinated by a central orchestrator"
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] gap-1"
              onClick={() => setShowAgents(!showAgents)}
            >
              {showAgents ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        </CardHeader>
        {showAgents && (
          <CardContent className="p-4 pt-0">
            <div className="flex flex-col items-center gap-4">
              {/* Coordinator */}
              <div className="w-full max-w-md">
                <ArchNodeBox node={AGENTS[0]} />
              </div>

              {/* Connection lines */}
              <div className="relative w-full max-w-2xl">
                <div className="flex items-start justify-center">
                  {/* Vertical line from coordinator */}
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-8 bg-gradient-to-b from-emerald-500/40 to-emerald-500/10" />
                  {/* Horizontal line across workers */}
                  <div className="w-4/5 h-px bg-emerald-500/20 mt-8" />
                </div>

                {/* Worker agents */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-10">
                  {AGENTS.slice(1).map((agent) => (
                    <ArchNodeBox key={agent.id} node={agent} />
                  ))}
                </div>
              </div>

              {/* Agent stats */}
              <div className="grid grid-cols-3 gap-3 w-full max-w-lg mt-2">
                <div className="text-center p-2 rounded-lg bg-muted/30">
                  <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">3</div>
                  <div className="text-[9px] text-muted-foreground">Active Agents</div>
                </div>
                <div className="text-center p-2 rounded-lg bg-muted/30">
                  <div className="text-lg font-bold text-violet-600 dark:text-violet-400">4</div>
                  <div className="text-[9px] text-muted-foreground">Total Models</div>
                </div>
                <div className="text-center p-2 rounded-lg bg-muted/30">
                  <div className="text-lg font-bold text-amber-600 dark:text-amber-400">0.84</div>
                  <div className="text-[9px] text-muted-foreground">Avg Trust Score</div>
                </div>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* ─── Section 3: Data Flow Pipeline ────────────────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <SectionHeader
              icon={GitBranch}
              title="Request Data Flow"
              description="How a request flows from user input to model response"
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] gap-1"
              onClick={() => setShowDataFlow(!showDataFlow)}
            >
              {showDataFlow ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        </CardHeader>
        {showDataFlow && (
          <CardContent className="p-4 pt-0">
            <div className="flex items-center gap-0 overflow-x-auto overflow-y-hidden custom-scrollbar pb-2">
              {[
                { icon: Globe, label: 'Request', desc: 'User prompt received', color: 'emerald' },
                { icon: Brain, label: 'Intent', desc: 'Classify: code/reason/speed', color: 'violet' },
                { icon: Layers, label: 'Strategy', desc: 'Select routing strategy', color: 'blue' },
                { icon: Server, label: 'Provider', desc: 'Choose provider + model', color: 'amber' },
                { icon: Zap, label: 'Response', desc: 'Stream result to user', color: 'emerald' },
              ].map((step, i) => (
                <div key={step.label} className="flex items-center shrink-0">
                  <div className={cn(
                    'flex flex-col items-center rounded-lg border p-3 min-w-[90px] transition-all duration-200 hover:scale-105',
                    step.color === 'emerald' && 'border-emerald-600/30 bg-emerald-600/5',
                    step.color === 'violet' && 'border-violet-600/30 bg-violet-600/5',
                    step.color === 'blue' && 'border-blue-600/30 bg-blue-600/5',
                    step.color === 'amber' && 'border-amber-600/30 bg-amber-600/5',
                  )}>
                    <step.icon className={cn(
                      'h-5 w-5 mb-1.5',
                      step.color === 'emerald' && 'text-emerald-600 dark:text-emerald-400',
                      step.color === 'violet' && 'text-violet-600 dark:text-violet-400',
                      step.color === 'blue' && 'text-blue-600 dark:text-blue-400',
                      step.color === 'amber' && 'text-amber-600 dark:text-amber-400',
                    )} />
                    <span className="text-xs font-semibold">{step.label}</span>
                    <span className="text-[8px] text-muted-foreground text-center mt-0.5">{step.desc}</span>
                    <Badge variant="outline" className="mt-1 h-3 px-1 text-[7px]">
                      Step {i + 1}
                    </Badge>
                  </div>
                  {i < 4 && <FlowArrow />}
                </div>
              ))}
            </div>

            {/* Flow details */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg border border-border/30 bg-muted/20">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
                  <span className="text-xs font-semibold">Intent Classification</span>
                </div>
                <div className="space-y-1.5">
                  {[
                    { intent: 'code', pattern: 'function, debug, api, fix...', color: 'bg-cyan-600/20 text-cyan-600' },
                    { intent: 'reasoning', pattern: 'solve, plan, analyze, think...', color: 'bg-violet-600/20 text-violet-600' },
                    { intent: 'speed', pattern: 'quick, summarize, list, brief...', color: 'bg-amber-600/20 text-amber-600' },
                    { intent: 'general', pattern: 'fallback for all other prompts', color: 'bg-emerald-600/20 text-emerald-600' },
                  ].map((item) => (
                    <div key={item.intent} className="flex items-center gap-2">
                      <Badge className={cn('text-[8px] border-0 h-4', item.color)}>{item.intent}</Badge>
                      <span className="text-[10px] text-muted-foreground font-mono">{item.pattern}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="p-3 rounded-lg border border-border/30 bg-muted/20">
                <div className="flex items-center gap-2 mb-2">
                  <Layers className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                  <span className="text-xs font-semibold">Routing Strategies</span>
                </div>
                <div className="space-y-1.5">
                  {[
                    { name: 'Quota Aware', desc: 'Free tier first, failover when exhausted', active: true },
                    { name: 'Cost Optimized', desc: 'Always prefer cheapest option', active: false },
                    { name: 'Quality First', desc: 'Best model within budget', active: false },
                    { name: 'Latency Optimized', desc: 'Minimize response time', active: false },
                  ].map((strat) => (
                    <div key={strat.name} className="flex items-center gap-2">
                      <span className={cn(
                        'h-1.5 w-1.5 rounded-full shrink-0',
                        strat.active ? 'bg-emerald-500' : 'bg-muted-foreground/30'
                      )} />
                      <span className="text-[10px] font-medium">{strat.name}</span>
                      {strat.active && (
                        <Badge className="h-3 px-1 text-[7px] bg-emerald-600 text-white border-0">ACTIVE</Badge>
                      )}
                      <span className="text-[9px] text-muted-foreground ml-auto">{strat.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* ─── Section 4: Constitutional Governance Layer ────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <SectionHeader
              icon={Shield}
              title="Constitutional Governance Layer"
              description="Governor → Rules → Enforcement → Audit Log"
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] gap-1"
              onClick={() => setShowGovernance(!showGovernance)}
            >
              {showGovernance ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        </CardHeader>
        {showGovernance && (
          <CardContent className="p-4 pt-0">
            {/* Governance flow */}
            <div className="flex items-center gap-0 overflow-x-auto overflow-y-hidden custom-scrollbar pb-2">
              {[
                { icon: Shield, label: 'Governor', desc: 'Constitutional AI', color: 'emerald', node: GOV_NODES[0] },
                { icon: Lock, label: 'Rules Engine', desc: '7 constraints', color: 'violet', node: GOV_NODES[1] },
                { icon: Eye, label: 'Enforcement', desc: 'Block & audit', color: 'red', node: GOV_NODES[2] },
                { icon: FileText, label: 'Audit Log', desc: 'Full trail', color: 'blue', node: GOV_NODES[3] },
              ].map((step, i) => (
                <div key={step.label} className="flex items-center shrink-0">
                  <div className={cn(
                    'flex flex-col items-center rounded-lg border p-3 min-w-[100px] transition-all duration-200 hover:scale-105',
                    step.color === 'emerald' && 'border-emerald-600/30 bg-emerald-600/5',
                    step.color === 'violet' && 'border-violet-600/30 bg-violet-600/5',
                    step.color === 'red' && 'border-red-600/30 bg-red-600/5',
                    step.color === 'blue' && 'border-blue-600/30 bg-blue-600/5',
                  )}>
                    <step.icon className={cn(
                      'h-5 w-5 mb-1.5',
                      step.color === 'emerald' && 'text-emerald-600 dark:text-emerald-400',
                      step.color === 'violet' && 'text-violet-600 dark:text-violet-400',
                      step.color === 'red' && 'text-red-600 dark:text-red-400',
                      step.color === 'blue' && 'text-blue-600 dark:text-blue-400',
                    )} />
                    <span className="text-xs font-semibold">{step.label}</span>
                    <span className="text-[8px] text-muted-foreground text-center mt-0.5">{step.desc}</span>
                    <div className="flex items-center gap-1 mt-1">
                      {HEALTH_ICONS[step.node.health]}
                      <Badge className={cn(
                        'h-3 px-1 text-[7px] border-0',
                        HEALTH_COLORS[step.node.health].badge
                      )}>
                        {step.node.health.toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                  {i < 3 && <FlowArrow />}
                </div>
              ))}
            </div>

            {/* Constitutional Rules Summary */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                { rule: 'Max Concurrent Agents', limit: '5', current: '3', percent: 60 },
                { rule: 'Max API Calls/min', limit: '20', current: '12', percent: 60 },
                { rule: 'Max Write Operations/min', limit: '30', current: '8', percent: 27 },
                { rule: 'Max Token Budget', limit: '100K', current: '73.4K', percent: 73 },
                { rule: 'Block Dangerous Actions', limit: '∞', current: '3 blocked', percent: 0 },
                { rule: 'Trust Score Threshold', limit: '0.60', current: '0.84 avg', percent: 84 },
                { rule: 'Circuit Breaker', limit: '3 failures', current: '0', percent: 0 },
              ].map((r) => (
                <div key={r.rule} className="flex items-center gap-2 p-2 rounded-lg bg-muted/20 border border-border/20">
                  <Shield className="h-3 w-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span className="text-[10px] font-medium flex-1 min-w-0 truncate">{r.rule}</span>
                  <span className="text-[10px] text-muted-foreground font-mono shrink-0">{r.current}/{r.limit}</span>
                  {r.percent > 0 && (
                    <div className="w-12 shrink-0">
                      <Progress
                        value={r.percent}
                        className={cn('h-1', r.percent > 80 && '[&>div]:bg-yellow-500', r.percent > 95 && '[&>div]:bg-red-500')}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {/* ─── Legend ─────────────────────────────────────────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4 text-[10px] text-muted-foreground">
            <span className="font-semibold text-xs">Legend:</span>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              <span>Healthy</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-yellow-400" />
              <span>Degraded</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
              <span>Down</span>
            </div>
            <div className="border-l border-border/40 h-3" />
            <span>Hover over any node for details</span>
            <span>·</span>
            <span>Use <kbd className="font-mono bg-muted px-1 rounded text-[9px]">⌘K</kbd> to navigate tabs</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
