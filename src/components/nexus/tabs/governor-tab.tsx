'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Shield, CheckCircle2, XCircle, Clock, AlertTriangle, Eye, Lock } from 'lucide-react'

const decisions = [
  { time: '14:23:01', agent: 'worker-3', action: 'read file', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.82 },
  { time: '14:22:45', agent: 'coordinator', action: 'spawn sub-agent', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.91 },
  { time: '14:22:12', agent: 'worker-1', action: 'write stresslab/config.py', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', trust: 0.73 },
  { time: '14:21:58', agent: 'worker-2', action: 'delete all vault entries', scope: 'SYSTEM', impact: 'CRIT', decision: 'DENY', trust: 0.45 },
  { time: '14:21:30', agent: 'research-agent', action: 'API call external', scope: 'CROSS', impact: 'MED', decision: 'HOLD', trust: 0.62 },
  { time: '14:20:55', agent: 'worker-3', action: 'execute shell command', scope: 'PROJECT', impact: 'HIGH', decision: 'DENY', trust: 0.38 },
  { time: '14:20:12', agent: 'coordinator', action: 'read constitution', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', trust: 0.95 },
]

const agents = [
  { name: 'coordinator', trust: 0.91, decisions: 234, allowed: 228, denied: 4, held: 2, lane: 'impl' },
  { name: 'worker-1', trust: 0.73, decisions: 189, allowed: 172, denied: 12, held: 5, lane: 'review' },
  { name: 'worker-2', trust: 0.45, decisions: 156, allowed: 98, denied: 42, held: 16, lane: 'research' },
  { name: 'worker-3', trust: 0.82, decisions: 312, allowed: 298, denied: 8, held: 6, lane: 'audit' },
  { name: 'research-agent', trust: 0.62, decisions: 87, allowed: 64, denied: 11, held: 12, lane: 'research' },
]

const dangerPatterns = [
  { pattern: 'delete all', count: 3, severity: 'CRIT', status: 'blocked' },
  { pattern: 'rm -rf', count: 1, severity: 'CRIT', status: 'blocked' },
  { pattern: 'exfiltrate data', count: 0, severity: 'HIGH', status: 'watching' },
  { pattern: 'backdoor install', count: 0, severity: 'HIGH', status: 'watching' },
  { pattern: 'override constitution', count: 2, severity: 'CRIT', status: 'blocked' },
]

export function GovernorTab() {
  return (
    <div className="space-y-6 p-6">
      {/* Decision Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-emerald-600/20 bg-emerald-600/5">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">ALLOW (24h)</p>
            <p className="text-2xl font-bold text-emerald-400">847</p>
            <p className="text-[10px] text-muted-foreground">96.8% of decisions</p>
          </CardContent>
        </Card>
        <Card className="border-red-600/20 bg-red-600/5">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">DENY (24h)</p>
            <p className="text-2xl font-bold text-red-400">23</p>
            <p className="text-[10px] text-muted-foreground">2.6% of decisions</p>
          </CardContent>
        </Card>
        <Card className="border-yellow-600/20 bg-yellow-600/5">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">HOLD (24h)</p>
            <p className="text-2xl font-bold text-yellow-400">5</p>
            <p className="text-[10px] text-muted-foreground">0.6% of decisions</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Avg Trust Score</p>
            <p className="text-2xl font-bold">0.73</p>
            <p className="text-[10px] text-muted-foreground">threshold: 0.30 (research)</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Agent Trust Scores */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Shield className="h-4 w-4" /> Agent Trust Scores
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {agents.map((a) => (
                <div key={a.name} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{a.name}</span>
                      <Badge variant="outline" className="text-[9px]">{a.lane}</Badge>
                    </div>
                    <span className={`text-sm font-bold ${a.trust >= 0.7 ? 'text-emerald-400' : a.trust >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {a.trust.toFixed(2)}
                    </span>
                  </div>
                  <Progress value={a.trust * 100} className="h-1.5" />
                  <div className="flex gap-3 text-[10px] text-muted-foreground">
                    <span>{a.decisions} decisions</span>
                    <span className="text-emerald-400">{a.allowed} allow</span>
                    <span className="text-red-400">{a.denied} deny</span>
                    <span className="text-yellow-400">{a.held} hold</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Danger Gate Patterns */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Lock className="h-4 w-4" /> Danger Gate Patterns
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2.5">
              {dangerPatterns.map((p) => (
                <div key={p.pattern} className="flex items-center justify-between rounded-md bg-accent/30 px-3 py-2">
                  <div>
                    <code className="text-xs">{p.pattern}</code>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge className={`text-[9px] border-0 ${p.severity === 'CRIT' ? 'bg-red-600/15 text-red-400' : 'bg-orange-600/15 text-orange-400'}`}>
                        {p.severity}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">{p.count} triggers</span>
                    </div>
                  </div>
                  <Badge className={`text-[9px] border-0 ${p.status === 'blocked' ? 'bg-red-600/15 text-red-400' : 'bg-yellow-600/15 text-yellow-400'}`}>
                    {p.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Decision Log */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Eye className="h-4 w-4" /> Decision Log
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] text-muted-foreground">
                  <th className="p-3 font-medium">Time</th>
                  <th className="p-3 font-medium">Agent</th>
                  <th className="p-3 font-medium">Action</th>
                  <th className="p-3 font-medium">Scope</th>
                  <th className="p-3 font-medium">Impact</th>
                  <th className="p-3 font-medium">Decision</th>
                  <th className="p-3 font-medium">Trust</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((d, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-accent/50">
                    <td className="p-3 font-mono text-xs">{d.time}</td>
                    <td className="p-3 text-xs">{d.agent}</td>
                    <td className="p-3 text-xs max-w-[200px] truncate">{d.action}</td>
                    <td className="p-3">
                      <Badge variant="outline" className="text-[9px]">{d.scope}</Badge>
                    </td>
                    <td className="p-3">
                      <Badge className={`text-[9px] border-0 ${d.impact === 'CRIT' ? 'bg-red-600/15 text-red-400' : d.impact === 'HIGH' ? 'bg-orange-600/15 text-orange-400' : d.impact === 'MED' ? 'bg-yellow-600/15 text-yellow-400' : 'bg-emerald-600/15 text-emerald-400'}`}>
                        {d.impact}
                      </Badge>
                    </td>
                    <td className="p-3">
                      {d.decision === 'ALLOW' && <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[10px]"><CheckCircle2 className="mr-1 h-3 w-3" />ALLOW</Badge>}
                      {d.decision === 'DENY' && <Badge className="bg-red-600/15 text-red-400 border-0 text-[10px]"><XCircle className="mr-1 h-3 w-3" />DENY</Badge>}
                      {d.decision === 'HOLD' && <Badge className="bg-yellow-600/15 text-yellow-400 border-0 text-[10px]"><Clock className="mr-1 h-3 w-3" />HOLD</Badge>}
                    </td>
                    <td className="p-3 text-xs font-mono">{d.trust.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
