'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  FlaskConical,
  Play,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  BarChart3,
} from 'lucide-react'

const testTemplates = [
  { name: 'ISC Core Probe', domain: 'Instruction Set Compliance', difficulty: 'Hard', runs: 47, collapseRate: 23.4 },
  { name: 'Agentic Loop Trap', domain: 'Agentic Mode', difficulty: 'Expert', runs: 31, collapseRate: 41.2 },
  { name: 'Over-Refusal Check', domain: 'Safety Alignment', difficulty: 'Medium', runs: 62, collapseRate: 12.8 },
  { name: 'Context Leak Probe', domain: 'Information Security', difficulty: 'Hard', runs: 28, collapseRate: 18.5 },
  { name: 'Tool Misuse Chain', domain: 'Tool Use Safety', difficulty: 'Expert', runs: 19, collapseRate: 55.1 },
]

const recentTests = [
  { id: 'ISC-047', model: 'qwen3-coder', status: 'collapse', collapseRate: 95.3, mode: 'agentic', time: '2m ago' },
  { id: 'ISC-046', model: 'trinity-large', status: 'pass', collapseRate: 0, mode: 'standard', time: '8m ago' },
  { id: 'ISC-045', model: 'dolphin-mistral', status: 'partial', collapseRate: 34.1, mode: 'agentic', time: '15m ago' },
  { id: 'ISC-044', model: 'gemma-fast', status: 'pass', collapseRate: 0, mode: 'standard', time: '22m ago' },
  { id: 'ISC-043', model: 'kimi-k2.5', status: 'collapse', collapseRate: 78.2, mode: 'agentic', time: '35m ago' },
  { id: 'ISC-042', model: 'nemotron-3', status: 'pass', collapseRate: 5.1, mode: 'standard', time: '41m ago' },
]

const iscBenchmarks = [
  { model: 'trinity-large-preview', score: 92, grade: 'A', collapses: 1 },
  { model: 'minimax-m2.5', score: 88, grade: 'A-', collapses: 2 },
  { model: 'gemma-fast', score: 85, grade: 'B+', collapses: 3 },
  { model: 'nemotron-3-super', score: 81, grade: 'B', collapses: 4 },
  { model: 'qwen3-coder', score: 67, grade: 'C+', collapses: 12 },
  { model: 'kimi-k2.5', score: 58, grade: 'C-', collapses: 18 },
  { model: 'dolphin-mistral', score: 45, grade: 'D', collapses: 27 },
]

const statusConfig = {
  pass: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/10', label: 'PASS' },
  collapse: { icon: XCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/10', label: 'COLLAPSE' },
  partial: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-600/10', label: 'PARTIAL' },
}

const difficultyColors = {
  Medium: 'bg-blue-600/20 text-blue-600 dark:text-blue-400',
  Hard: 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400',
  Expert: 'bg-red-600/20 text-red-600 dark:text-red-400',
}

export function StressLabTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-lg font-semibold">StressLab Arena</h2>
          <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">ISC</Badge>
        </div>
        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5">
          <Play className="h-3.5 w-3.5" />
          Run Test
        </Button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">47</div>
            <div className="text-xs text-muted-foreground">Total Tests</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">72%</div>
            <div className="text-xs text-muted-foreground">Pass Rate</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">5</div>
            <div className="text-xs text-muted-foreground">Collapses Detected</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
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
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {testTemplates.map((template) => (
                <div key={template.name} className="p-3 rounded-lg bg-muted/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{template.name}</span>
                    <Badge className={`text-[9px] h-4 border-0 ${difficultyColors[template.difficulty as keyof typeof difficultyColors]}`}>
                      {template.difficulty}
                    </Badge>
                  </div>
                  <div className="text-[11px] text-muted-foreground">{template.domain}</div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{template.runs} runs</span>
                    <span className={`text-[10px] font-mono ${template.collapseRate > 30 ? 'text-red-600 dark:text-red-400' : template.collapseRate > 15 ? 'text-yellow-600 dark:text-yellow-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                      {template.collapseRate}% collapse
                    </span>
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
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {iscBenchmarks.map((model, i) => (
                <div key={model.model} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted-foreground w-4">{i + 1}</span>
                      <span className="text-sm font-medium">{model.model}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px] h-5">{model.grade}</Badge>
                      <span className="text-xs font-mono">{model.score}%</span>
                    </div>
                  </div>
                  <Progress value={model.score} className="h-1.5" />
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                    <span>{model.collapses} collapse{model.collapses !== 1 ? 's' : ''}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Test Runs */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recent Test Runs
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2">
            {recentTests.map((test) => {
              const config = statusConfig[test.status as keyof typeof statusConfig]
              const StatusIcon = config.icon
              return (
                <div key={test.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                  <StatusIcon className={`h-4 w-4 shrink-0 ${config.color}`} />
                  <span className="text-sm font-mono font-medium">{test.id}</span>
                  <span className="text-sm text-muted-foreground">{test.model}</span>
                  <Badge className={`text-[9px] h-4 border-0 ${config.bg} ${config.color}`}>{config.label}</Badge>
                  <Badge variant="outline" className="text-[9px] h-4">{test.mode}</Badge>
                  <span className="flex-1" />
                  {test.collapseRate > 0 && (
                    <span className="text-xs font-mono text-red-600 dark:text-red-400">{test.collapseRate}%</span>
                  )}
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
