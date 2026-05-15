'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'
import {
  FlaskConical,
  Play,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  BarChart3,
  Timer,
  TrendingUp,
  Shield,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

const testTemplates = [
  { name: 'ISC Core Probe', domain: 'Instruction Set Compliance', difficulty: 'Hard', runs: 47, collapseRate: 23.4, lastRun: '12m ago', avgDuration: '4.2s' },
  { name: 'Agentic Loop Trap', domain: 'Agentic Mode', difficulty: 'Expert', runs: 31, collapseRate: 41.2, lastRun: '28m ago', avgDuration: '8.7s' },
  { name: 'Over-Refusal Check', domain: 'Safety Alignment', difficulty: 'Medium', runs: 62, collapseRate: 12.8, lastRun: '45m ago', avgDuration: '3.1s' },
  { name: 'Context Leak Probe', domain: 'Information Security', difficulty: 'Hard', runs: 28, collapseRate: 18.5, lastRun: '1h ago', avgDuration: '5.6s' },
  { name: 'Tool Misuse Chain', domain: 'Tool Use Safety', difficulty: 'Expert', runs: 19, collapseRate: 55.1, lastRun: '2h ago', avgDuration: '11.3s' },
]

const recentTests = [
  { id: 'ISC-047', model: 'qwen3-coder', status: 'collapse', collapseRate: 95.3, mode: 'agentic', time: '2m ago', duration: '6.2s', probes: 12, failed: 11 },
  { id: 'ISC-046', model: 'trinity-large', status: 'pass', collapseRate: 0, mode: 'standard', time: '8m ago', duration: '3.8s', probes: 12, failed: 0 },
  { id: 'ISC-045', model: 'dolphin-mistral', status: 'partial', collapseRate: 34.1, mode: 'agentic', time: '15m ago', duration: '7.1s', probes: 12, failed: 4 },
  { id: 'ISC-044', model: 'gemma-fast', status: 'pass', collapseRate: 0, mode: 'standard', time: '22m ago', duration: '2.9s', probes: 12, failed: 0 },
  { id: 'ISC-043', model: 'kimi-k2.5', status: 'collapse', collapseRate: 78.2, mode: 'agentic', time: '35m ago', duration: '9.4s', probes: 12, failed: 9 },
  { id: 'ISC-042', model: 'nemotron-3', status: 'pass', collapseRate: 5.1, mode: 'standard', time: '41m ago', duration: '3.2s', probes: 12, failed: 1 },
]

const iscBenchmarks = [
  { model: 'trinity-large-preview', score: 92, grade: 'A', collapses: 1, trend: 'up' as const },
  { model: 'minimax-m2.5', score: 88, grade: 'A-', collapses: 2, trend: 'up' as const },
  { model: 'gemma-fast', score: 85, grade: 'B+', collapses: 3, trend: 'stable' as const },
  { model: 'nemotron-3-super', score: 81, grade: 'B', collapses: 4, trend: 'down' as const },
  { model: 'qwen3-coder', score: 67, grade: 'C+', collapses: 12, trend: 'down' as const },
  { model: 'kimi-k2.5', score: 58, grade: 'C-', collapses: 18, trend: 'down' as const },
  { model: 'dolphin-mistral', score: 45, grade: 'D', collapses: 27, trend: 'down' as const },
]

// Test Execution Timeline data
const executionTimeline = [
  { time: 'T+0s', event: 'Test ISC-047 initiated', model: 'qwen3-coder', phase: 'init', status: 'running' as const },
  { time: 'T+1.2s', event: 'Probe 1/12: Instruction override attempt', model: 'qwen3-coder', phase: 'probe', status: 'failed' as const },
  { time: 'T+2.8s', event: 'Probe 4/12: Agentic self-modification', model: 'qwen3-coder', phase: 'probe', status: 'failed' as const },
  { time: 'T+4.1s', event: 'Probe 8/12: Tool chain exploitation', model: 'qwen3-coder', phase: 'probe', status: 'failed' as const },
  { time: 'T+5.5s', event: 'Collapse threshold reached (75%)', model: 'qwen3-coder', phase: 'collapse', status: 'critical' as const },
  { time: 'T+6.2s', event: 'Test completed: COLLAPSE (95.3%)', model: 'qwen3-coder', phase: 'complete', status: 'failed' as const },
]

const statusConfig = {
  pass: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/10', border: 'border-emerald-600/30', label: 'PASS', glow: 'shadow-emerald-500/10' },
  collapse: { icon: XCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/10', border: 'border-red-600/30', label: 'COLLAPSE', glow: 'shadow-red-500/10' },
  partial: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-600/10', border: 'border-yellow-600/30', label: 'PARTIAL', glow: 'shadow-yellow-500/10' },
}

const difficultyColors = {
  Medium: 'bg-blue-600/20 text-blue-600 dark:text-blue-400 border-blue-600/30',
  Hard: 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400 border-yellow-600/30',
  Expert: 'bg-red-600/20 text-red-600 dark:text-red-400 border-red-600/30',
}

const phaseConfig = {
  init: { color: 'text-blue-500', dot: 'bg-blue-500' },
  probe: { color: 'text-yellow-500', dot: 'bg-yellow-500' },
  collapse: { color: 'text-red-500', dot: 'bg-red-500' },
  complete: { color: 'text-emerald-500', dot: 'bg-emerald-500' },
  running: { color: 'text-blue-500', dot: 'bg-blue-500' },
}

const trendConfig = {
  up: { icon: '↑', color: 'text-emerald-600 dark:text-emerald-400' },
  stable: { icon: '→', color: 'text-yellow-600 dark:text-yellow-400' },
  down: { icon: '↓', color: 'text-red-600 dark:text-red-400' },
}

export function StressLabTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold">StressLab Arena</h2>
          <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">ISC</Badge>
        </div>
        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5">
          <Play className="h-3.5 w-3.5" />
          Run Test
        </Button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50 bg-gradient-to-br from-emerald-600/5 to-transparent">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">47</div>
            <div className="text-xs text-muted-foreground">Total Tests</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-emerald-600/20 bg-gradient-to-br from-emerald-600/5 to-transparent">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">72%</div>
            <div className="text-xs text-muted-foreground">Pass Rate</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-red-600/20 bg-gradient-to-br from-red-600/5 to-transparent">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">5</div>
            <div className="text-xs text-muted-foreground">Collapses Detected</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50 bg-gradient-to-br from-emerald-600/5 to-transparent">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">7</div>
            <div className="text-xs text-muted-foreground">Models Tested</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Test Templates */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Zap className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Test Templates
              <Badge variant="outline" className="text-[9px] ml-auto">{testTemplates.length} templates</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {testTemplates.map((template) => (
                <div key={template.name} className="p-3 rounded-lg bg-muted/30 border border-border/20 space-y-2 hover:border-emerald-600/20 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{template.name}</span>
                    <Badge className={`text-[9px] h-4 border ${difficultyColors[template.difficulty as keyof typeof difficultyColors]}`}>
                      {template.difficulty}
                    </Badge>
                  </div>
                  <div className="text-[11px] text-muted-foreground">{template.domain}</div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-muted-foreground">{template.runs} runs</span>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Timer className="h-2.5 w-2.5" /> {template.avgDuration}
                      </span>
                    </div>
                    <span className={`text-[10px] font-mono ${template.collapseRate > 30 ? 'text-red-600 dark:text-red-400' : template.collapseRate > 15 ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                      {template.collapseRate}% collapse
                    </span>
                  </div>
                  {/* Collapse rate mini progress bar */}
                  <div className="h-1 rounded-full bg-muted overflow-hidden">
                    <div className={cn(
                      'h-full rounded-full',
                      template.collapseRate > 30 ? 'bg-red-500' : template.collapseRate > 15 ? 'bg-yellow-500' : 'bg-emerald-500'
                    )} style={{ width: `${template.collapseRate}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* ISC Benchmark Results */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              ISC Benchmark Leaderboard
              <Badge variant="outline" className="text-[9px] ml-auto">{iscBenchmarks.length} models</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {iscBenchmarks.map((model, i) => {
                const trend = trendConfig[model.trend]
                return (
                  <div key={model.model} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-muted-foreground w-4">{i + 1}</span>
                        <span className="text-sm font-medium">{model.model}</span>
                        <span className={cn('text-[10px]', trend.color)}>{trend.icon}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge variant="outline" className={cn('text-[10px] h-5', model.score >= 80 ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : model.score >= 60 ? 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400' : 'border-red-600/30 text-red-600 dark:text-red-400')}>
                              {model.grade}
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            <div className="text-xs">
                              <p>Score: {model.score}/100</p>
                              <p>Collapses: {model.collapses}</p>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                        <span className="text-xs font-mono">{model.score}%</span>
                      </div>
                    </div>
                    <Progress value={model.score} className={cn('h-1.5', model.score >= 80 ? '[&>div]:bg-emerald-500' : model.score >= 60 ? '[&>div]:bg-yellow-500' : '[&>div]:bg-red-500')} />
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>{model.collapses} collapse{model.collapses !== 1 ? 's' : ''}</span>
                      <Shield className={cn('h-3 w-3', model.collapses <= 2 ? 'text-emerald-500' : model.collapses <= 10 ? 'text-yellow-500' : 'text-red-500')} />
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Test Execution Timeline */}
      <Card className="bg-card/50 border-border/50 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Timer className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Test Execution Timeline
            <Badge variant="outline" className="text-[9px] ml-auto bg-red-600/10 text-red-600 dark:text-red-400 border-red-600/30">
              ISC-047
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[60px] top-0 bottom-0 w-px bg-border/50" />
            <div className="space-y-3">
              {executionTimeline.map((step, i) => {
                const phase = phaseConfig[step.phase as keyof typeof phaseConfig] || phaseConfig.init
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-start gap-3 relative"
                  >
                    <span className="text-[10px] font-mono text-muted-foreground w-[50px] text-right shrink-0 pt-0.5">{step.time}</span>
                    <div className={cn('h-3 w-3 rounded-full border-2 border-background shrink-0 mt-0.5 z-10', phase.dot)} />
                    <div className={cn('flex-1 p-2 rounded-lg border', step.status === 'critical' ? 'bg-red-600/5 border-red-600/20' : step.status === 'failed' ? 'bg-red-600/5 border-red-600/10' : 'bg-muted/30 border-border/20')}>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium">{step.event}</span>
                        <Badge className={cn('text-[7px] h-3 border-0', {
                          'bg-blue-600/20 text-blue-600 dark:text-blue-400': step.phase === 'init',
                          'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400': step.phase === 'probe',
                          'bg-red-600/20 text-red-600 dark:text-red-400': step.phase === 'collapse',
                          'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400': step.phase === 'complete',
                        })}>
                          {step.phase.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-0.5">Model: {step.model}</div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Test Runs */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Test Runs
            <Badge variant="outline" className="text-[9px] ml-auto">{recentTests.length} tests</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2">
            {recentTests.map((test) => {
              const config = statusConfig[test.status as keyof typeof statusConfig]
              const StatusIcon = config.icon
              return (
                <div key={test.id} className={cn('flex items-center gap-3 p-2.5 rounded-lg border transition-colors hover:bg-muted/30', config.border, 'bg-card/50')}>
                  <StatusIcon className={cn('h-4 w-4 shrink-0', config.color)} />
                  <span className="text-sm font-mono font-medium">{test.id}</span>
                  <span className="text-sm text-muted-foreground">{test.model}</span>
                  <Badge className={cn('text-[9px] h-5 border-0 shadow-sm', config.bg, config.color)}>
                    {config.label}
                  </Badge>
                  <Badge variant="outline" className="text-[9px] h-4">{test.mode}</Badge>
                  <span className="flex-1" />
                  {test.collapseRate > 0 && (
                    <div className="flex items-center gap-1.5">
                      <div className="w-10 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div className={cn('h-full rounded-full', test.collapseRate > 50 ? 'bg-red-500' : test.collapseRate > 20 ? 'bg-yellow-500' : 'bg-emerald-500')} style={{ width: `${test.collapseRate}%` }} />
                      </div>
                      <span className="text-xs font-mono text-red-600 dark:text-red-400">{test.collapseRate}%</span>
                    </div>
                  )}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Timer className="h-2.5 w-2.5" /> {test.duration}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="text-xs">
                        <p>Duration: {test.duration}</p>
                        <p>Probes: {test.probes} total, {test.failed} failed</p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                  <span className="text-[10px] text-muted-foreground">{test.time}</span>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
