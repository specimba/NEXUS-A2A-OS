'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Shield,
  Scale,
  Ban,
  CheckCircle2,
  AlertTriangle,
  Clock,
  TrendingUp,
  Eye,
} from 'lucide-react'

const constitutionRules = [
  { id: 'C1', rule: 'Max agents per hour', limit: 5, current: 3, impact: 'high', status: 'ok', rationale: 'Based on free-tier API rate limits across providers. Prevents quota exhaustion.' },
  { id: 'C2', rule: 'API calls per session', limit: 20, current: 12, impact: 'medium', status: 'ok', rationale: 'Conservative limit to stay within concurrent request thresholds on free tiers.' },
  { id: 'C3', rule: 'Max concurrent agents', limit: 2, current: 2, impact: 'high', status: 'caution', rationale: 'Matches typical free-tier concurrency limits (Cerebras: 2, Groq: 2, NVIDIA: 2).' },
  { id: 'C4', rule: 'File writes per session', limit: 30, current: 8, impact: 'low', status: 'ok', rationale: 'Prevents runaway agents from flooding storage. 30 is generous for governance operations.' },
  { id: 'C5', rule: 'Max tokens per session', limit: 100000, current: 73450, impact: 'high', status: 'caution', rationale: 'Aligned with combined free-tier token budgets across 14 providers.' },
  { id: 'C6', rule: 'Trust score minimum', limit: 0.5, current: 0.78, impact: 'critical', status: 'ok', rationale: 'Below 0.5 trust indicates unreliable behavior patterns. Threshold for intervention.' },
  { id: 'C7', rule: 'Block CRITICAL actions', limit: 1, current: 0, impact: 'critical', status: 'ok', rationale: 'Zero-tolerance for destructive patterns. Any match triggers immediate block.' },
]

const recentDecisions = [
  { time: '2m ago', action: 'delete_all', scope: 'global', impact: 'CRITICAL', decision: 'BLOCKED', reason: 'Pattern matched: destructive operation', trust: 0.92 },
  { time: '8m ago', action: 'override_constitution', scope: 'session', impact: 'CRITICAL', decision: 'BLOCKED', reason: 'Constitution override not permitted', trust: 0.85 },
  { time: '15m ago', action: 'api_call', scope: 'session', impact: 'LOW', decision: 'ALLOWED', reason: 'Within session limits', trust: 0.78 },
  { time: '22m ago', action: 'file_write', scope: 'project', impact: 'MEDIUM', decision: 'ALLOWED', reason: 'Write limit: 8/30', trust: 0.88 },
  { time: '35m ago', action: 'spawn_agent', scope: 'session', impact: 'MEDIUM', decision: 'ALLOWED', reason: 'Agent limit: 3/5', trust: 0.92 },
  { time: '45m ago', action: 'delete_all', scope: 'global', impact: 'CRITICAL', decision: 'BLOCKED', reason: 'Pattern matched: destructive operation', trust: 0.67 },
  { time: '1h ago', action: 'api_call', scope: 'session', impact: 'LOW', decision: 'ALLOWED', reason: 'Within session limits', trust: 0.85 },
]

const trustScores = [
  { agent: 'coordinator', score: 0.95, trend: 'up', decisions: 142, blocked: 0 },
  { agent: 'worker-1', score: 0.92, trend: 'up', decisions: 89, blocked: 2 },
  { agent: 'worker-3', score: 0.85, trend: 'up', decisions: 67, blocked: 1 },
  { agent: 'worker-2', score: 0.78, trend: 'down', decisions: 54, blocked: 5 },
]

const dangerPatterns = [
  { pattern: 'delete_all', matches: 2, severity: 'critical', action: 'Block' },
  { pattern: 'override_constitution', matches: 1, severity: 'critical', action: 'Block' },
  { pattern: 'rm -rf', matches: 0, severity: 'critical', action: 'Block' },
  { pattern: 'exfil_data', matches: 0, severity: 'high', action: 'Block + Alert' },
  { pattern: 'elevate_privilege', matches: 0, severity: 'high', action: 'Block + Audit' },
]

export function GovernorTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">Governor Dashboard</h2>
        <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">Enforcing</Badge>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">7</div>
            <div className="text-xs text-muted-foreground">Rules Active</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">3</div>
            <div className="text-xs text-muted-foreground">Blocked Today</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">2</div>
            <div className="text-xs text-muted-foreground">Caution Rules</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">0.88</div>
            <div className="text-xs text-muted-foreground">Avg Trust Score</div>
          </CardContent>
        </Card>
      </div>

      {/* Constitution Rules */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Scale className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Constitutional Rules
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2">
            {constitutionRules.map((rule) => {
              const percent = typeof rule.current === 'number' && typeof rule.limit === 'number' && rule.limit > 100
                ? (rule.current / rule.limit) * 100
                : rule.limit <= 1
                ? rule.current >= rule.limit ? 100 : 0
                : (rule.current / rule.limit) * 100
              return (
                <div key={rule.id} className="p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <code className="text-[10px] font-mono text-muted-foreground">{rule.id}</code>
                      <span className="text-sm">{rule.rule}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        className={`text-[9px] h-4 border-0 ${
                          rule.impact === 'critical'
                            ? 'bg-red-600/20 text-red-600 dark:text-red-400'
                            : rule.impact === 'high'
                            ? 'bg-orange-600/20 text-orange-600 dark:text-orange-400'
                            : rule.impact === 'medium'
                            ? 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400'
                            : 'bg-blue-600/20 text-blue-600 dark:text-blue-400'
                        }`}
                      >
                        {rule.impact.toUpperCase()}
                      </Badge>
                      {rule.status === 'ok' ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400" />
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Progress value={percent} className="h-1.5 flex-1" />
                    <span className="text-[10px] font-mono text-muted-foreground min-w-[80px] text-right">
                      {rule.limit > 100 ? `${(rule.current / 1000).toFixed(1)}k / ${(rule.limit / 1000).toFixed(0)}k` : `${rule.current} / ${rule.limit}`}
                    </span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1.5 leading-relaxed">{rule.rationale}</p>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Decisions */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Recent Decisions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {recentDecisions.map((d, i) => (
                <div key={i} className="p-2 rounded-lg bg-muted/30 space-y-1">
                  <div className="flex items-center gap-2">
                    {d.decision === 'BLOCKED' ? (
                      <Ban className="h-3.5 w-3.5 text-red-600 dark:text-red-400 shrink-0" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    )}
                    <code className="text-xs font-mono">{d.action}</code>
                    <Badge
                      className={`text-[9px] h-4 border-0 ${
                        d.decision === 'BLOCKED'
                          ? 'bg-red-600/20 text-red-600 dark:text-red-400'
                          : 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400'
                      }`}
                    >
                      {d.decision}
                    </Badge>
                    <span className="flex-1" />
                    <span className="text-[10px] text-muted-foreground">{d.time}</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground pl-5">{d.reason}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Trust Scoring */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Trust Scores
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {trustScores.map((agent) => (
                <div key={agent.agent} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{agent.agent}</span>
                      <Badge variant="outline" className="text-[10px] h-4">
                        {agent.trend === 'up' ? '↑' : '↓'} trending
                      </Badge>
                    </div>
                    <span className={`text-sm font-mono font-bold ${agent.score >= 0.9 ? 'text-emerald-600 dark:text-emerald-400' : agent.score >= 0.8 ? 'text-blue-600 dark:text-blue-400' : 'text-yellow-600 dark:text-yellow-400'}`}>
                      {agent.score.toFixed(2)}
                    </span>
                  </div>
                  <Progress value={agent.score * 100} className="h-1.5" />
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span>{agent.decisions} decisions</span>
                    <span className="text-border">|</span>
                    <span className={agent.blocked > 0 ? 'text-red-600 dark:text-red-400' : ''}>{agent.blocked} blocked</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Danger Patterns */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Eye className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Danger Pattern Watch
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {dangerPatterns.map((pattern) => (
              <div key={pattern.pattern} className="p-3 rounded-lg bg-muted/30 space-y-1.5">
                <div className="flex items-center justify-between">
                  <code className="text-xs font-mono font-medium">{pattern.pattern}</code>
                  <Badge
                    className={`text-[9px] h-4 border-0 ${
                      pattern.severity === 'critical'
                        ? 'bg-red-600/20 text-red-600 dark:text-red-400'
                        : 'bg-orange-600/20 text-orange-600 dark:text-orange-400'
                    }`}
                  >
                    {pattern.severity.toUpperCase()}
                  </Badge>
                </div>
                <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                  <span>{pattern.matches} match{pattern.matches !== 1 ? 'es' : ''} today</span>
                  <span>Action: {pattern.action}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
