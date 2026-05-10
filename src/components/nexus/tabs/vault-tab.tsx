'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Database,
  Brain,
  FileText,
  Lock,
  Unlock,
  Shield,
  Clock,
  BarChart3,
} from 'lucide-react'

const tracks = [
  { name: 'Episodic', icon: Brain, entries: 234, avgScore: 0.82, color: 'emerald', description: 'Experience-based memories' },
  { name: 'Semantic', icon: FileText, entries: 567, avgScore: 0.91, color: 'blue', description: 'Knowledge and facts' },
  { name: 'Procedural', icon: Lock, entries: 89, avgScore: 0.76, color: 'orange', description: 'Skills and procedures' },
]

const recentEntries = [
  { id: 'VE-4891', track: 'Episodic', category: 'interaction', key: 'user_preference_dark_mode', score: 0.95, agent: 'worker-1', time: '5m ago' },
  { id: 'VE-4890', track: 'Semantic', category: 'knowledge', key: 'api_rate_limit_policy', score: 0.88, agent: 'coordinator', time: '12m ago' },
  { id: 'VE-4889', track: 'Episodic', category: 'interaction', key: 'gmr_failover_event', score: 0.72, agent: 'worker-3', time: '18m ago' },
  { id: 'VE-4888', track: 'Procedural', category: 'skill', key: 'deploy_pipeline_v2', score: 0.81, agent: 'worker-2', time: '25m ago' },
  { id: 'VE-4887', track: 'Semantic', category: 'knowledge', key: 'constitution_rule_c3', score: 0.93, agent: 'coordinator', time: '32m ago' },
  { id: 'VE-4886', track: 'Episodic', category: 'interaction', key: 'stress_test_isc047', score: 0.67, agent: 'worker-1', time: '45m ago' },
  { id: 'VE-4885', track: 'Semantic', category: 'knowledge', key: 'model_health_baseline', score: 0.89, agent: 'coordinator', time: '1h ago' },
  { id: 'VE-4884', track: 'Procedural', category: 'skill', key: 'snapshot_export', score: 0.74, agent: 'worker-3', time: '1h ago' },
]

const trustDistribution = [
  { range: '0.9 - 1.0', count: 156, percent: 15, color: 'emerald' },
  { range: '0.8 - 0.9', count: 312, percent: 30, color: 'emerald' },
  { range: '0.7 - 0.8', count: 267, percent: 26, color: 'blue' },
  { range: '0.6 - 0.7', count: 178, percent: 17, color: 'yellow' },
  { range: '0.5 - 0.6', count: 72, percent: 7, color: 'orange' },
  { range: '< 0.5', count: 55, percent: 5, color: 'red' },
]

const trackColors: Record<string, string> = {
  emerald: 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400',
  blue: 'bg-blue-600/20 text-blue-600 dark:text-blue-400',
  orange: 'bg-orange-600/20 text-orange-600 dark:text-orange-400',
}

export function VaultTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Database className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">Vault Browser</h2>
        <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">890 entries</Badge>
      </div>

      {/* Track Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {tracks.map((track) => (
          <Card key={track.name} className="bg-card/50 border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${trackColors[track.color]}`}>
                  <track.icon className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-sm font-bold">{track.name}</div>
                  <div className="text-[10px] text-muted-foreground">{track.description}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-lg font-bold">{track.entries}</div>
                  <div className="text-[10px] text-muted-foreground">Entries</div>
                </div>
                <div>
                  <div className="text-lg font-bold">{track.avgScore.toFixed(2)}</div>
                  <div className="text-[10px] text-muted-foreground">Avg Score</div>
                </div>
              </div>
              <Progress value={track.avgScore * 100} className="h-1 mt-2" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent Entries */}
        <Card className="bg-card/50 border-border/50 lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Recent Entries
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {recentEntries.map((entry) => (
                <div key={entry.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                  {entry.score >= 0.8 ? (
                    <Unlock className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  ) : (
                    <Lock className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400 shrink-0" />
                  )}
                  <code className="text-[10px] font-mono text-muted-foreground">{entry.id}</code>
                  <Badge
                    className={`text-[9px] h-4 border-0 ${trackColors[tracks.find(t => t.name === entry.track)?.color || 'blue']}`}
                  >
                    {entry.track}
                  </Badge>
                  <span className="text-sm flex-1 truncate">{entry.key}</span>
                  <span className="text-xs font-mono text-muted-foreground">{entry.score.toFixed(2)}</span>
                  <span className="text-[10px] text-muted-foreground">{entry.time}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Trust Distribution */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Trust Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="space-y-3">
              {trustDistribution.map((bucket) => (
                <div key={bucket.range} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono">{bucket.range}</span>
                    <span className="text-muted-foreground">{bucket.count} ({bucket.percent}%)</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        bucket.color === 'emerald' ? 'bg-emerald-500' :
                        bucket.color === 'blue' ? 'bg-blue-500' :
                        bucket.color === 'yellow' ? 'bg-yellow-500' :
                        bucket.color === 'orange' ? 'bg-orange-500' :
                        'bg-red-500'
                      }`}
                      style={{ width: `${bucket.percent}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Vault Stats */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Constitution Compliance
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">8/30</div>
              <div className="text-xs text-muted-foreground">File Writes</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">12/20</div>
              <div className="text-xs text-muted-foreground">API Calls</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">3/5</div>
              <div className="text-xs text-muted-foreground">Active Agents</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">PASS</div>
              <div className="text-xs text-muted-foreground">Constitution Check</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
