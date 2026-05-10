'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Target,
  TrendingUp,
  Shield,
  Zap,
  Users,
  Brain,
  Clock,
  Activity,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'

const kpiCategories = [
  {
    name: 'System Health',
    icon: Activity,
    kpis: [
      { label: 'Uptime', value: '99.7%', target: '99.9%', status: 'warning', trend: 'stable' },
      { label: 'Error Rate', value: '0.3%', target: '<1%', status: 'ok', trend: 'down' },
      { label: 'Avg Latency', value: '142ms', target: '<200ms', status: 'ok', trend: 'down' },
      { label: 'P99 Latency', value: '387ms', target: '<500ms', status: 'ok', trend: 'up' },
    ],
  },
  {
    name: 'Agent Performance',
    icon: Users,
    kpis: [
      { label: 'Active Agents', value: '4/5', target: '≤5', status: 'ok', trend: 'stable' },
      { label: 'Avg Trust Score', value: '0.88', target: '>0.8', status: 'ok', trend: 'up' },
      { label: 'Task Completion', value: '94.2%', target: '>90%', status: 'ok', trend: 'up' },
      { label: 'Failed Tasks (24h)', value: '10', target: '<15', status: 'ok', trend: 'down' },
    ],
  },
  {
    name: 'Governor Effectiveness',
    icon: Shield,
    kpis: [
      { label: 'Blocked Actions', value: '3', target: 'Track only', status: 'ok', trend: 'up' },
      { label: 'False Positive Rate', value: '2.1%', target: '<5%', status: 'ok', trend: 'down' },
      { label: 'Constitution Compliance', value: '100%', target: '100%', status: 'ok', trend: 'stable' },
      { label: 'Danger Patterns Matched', value: '3', target: 'Track only', status: 'ok', trend: 'stable' },
    ],
  },
  {
    name: 'Model & Token Efficiency',
    icon: Brain,
    kpis: [
      { label: 'Budget Utilization', value: '26.6%', target: '<80%', status: 'ok', trend: 'up' },
      { label: 'Burn Rate', value: '142 tok/min', target: '<500', status: 'ok', trend: 'stable' },
      { label: 'Model Availability', value: '7/7', target: '100%', status: 'ok', trend: 'stable' },
      { label: 'Failover Time', value: '1.2s avg', target: '<3s', status: 'ok', trend: 'down' },
    ],
  },
]

const statusConfig = {
  ok: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/20' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-600/20' },
  critical: { icon: AlertTriangle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/20' },
}

const trendConfig = {
  up: { icon: TrendingUp, label: 'Up' },
  down: { icon: TrendingUp, label: 'Down' },
  stable: { icon: Activity, label: 'Stable' },
}

// Sparkline-like mini chart
function SparkLine({ values, color }: { values: number[]; color: string }) {
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min || 1

  return (
    <div className="flex items-end gap-0.5 h-6">
      {values.map((value, i) => (
        <div
          key={i}
          className={`flex-1 rounded-t ${color}`}
          style={{ height: `${((value - min) / range) * 100}%`, minHeight: '2px' }}
        />
      ))}
    </div>
  )
}

export function KpiTab() {
  const okCount = kpiCategories.reduce((sum, cat) => sum + cat.kpis.filter(k => k.status === 'ok').length, 0)
  const warningCount = kpiCategories.reduce((sum, cat) => sum + cat.kpis.filter(k => k.status === 'warning').length, 0)
  const totalKpis = kpiCategories.reduce((sum, cat) => sum + cat.kpis.length, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Target className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">KPI Dashboard</h2>
        <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">{totalKpis} KPIs</Badge>
      </div>

      {/* Top-level Score */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-4xl font-bold text-emerald-600 dark:text-emerald-400">{Math.round((okCount / totalKpis) * 100)}%</div>
              <div className="text-xs text-muted-foreground mt-1">KPIs On Target</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-emerald-600 dark:text-emerald-400">{okCount}</div>
              <div className="text-xs text-muted-foreground mt-1">OK</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-yellow-600 dark:text-yellow-400">{warningCount}</div>
              <div className="text-xs text-muted-foreground mt-1">Warning</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold">A+</div>
              <div className="text-xs text-muted-foreground mt-1">Overall Grade</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Categories */}
      {kpiCategories.map((category) => (
        <Card key={category.name} className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <category.icon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              {category.name}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {category.kpis.map((kpi) => {
                const status = statusConfig[kpi.status as keyof typeof statusConfig]
                const StatusIcon = status.icon
                const trend = trendConfig[kpi.trend as keyof typeof trendConfig]
                return (
                  <div key={kpi.label} className="p-3 rounded-lg bg-muted/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{kpi.label}</span>
                      <StatusIcon className={`h-3.5 w-3.5 ${status.color}`} />
                    </div>
                    <div className="text-lg font-bold">{kpi.value}</div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-muted-foreground">Target: {kpi.target}</span>
                      <Badge className={`text-[9px] h-4 border-0 ${status.bg} ${status.color}`}>
                        {kpi.status.toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      ))}

      {/* Trend Sparklines */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            24h Trend Sparklines
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { label: 'Uptime', values: [99.5, 99.6, 99.7, 99.8, 99.7, 99.6, 99.7, 99.8, 99.9, 99.7, 99.6, 99.7], color: 'bg-emerald-500/60' },
              { label: 'Error Rate', values: [0.5, 0.4, 0.3, 0.4, 0.3, 0.2, 0.3, 0.4, 0.3, 0.2, 0.3, 0.3], color: 'bg-red-500/60' },
              { label: 'Latency', values: [180, 165, 150, 142, 138, 145, 152, 148, 142, 139, 145, 142], color: 'bg-blue-500/60' },
              { label: 'Trust Score', values: [0.82, 0.84, 0.85, 0.86, 0.87, 0.86, 0.87, 0.88, 0.87, 0.88, 0.88, 0.88], color: 'bg-emerald-500/60' },
              { label: 'Budget Used', values: [15, 18, 20, 21, 22, 23, 24, 24.5, 25, 25.5, 26, 26.6], color: 'bg-orange-500/60' },
              { label: 'Task Success', values: [92, 93, 93, 94, 93, 94, 94, 95, 94, 94, 94, 94.2], color: 'bg-emerald-500/60' },
            ].map((chart) => (
              <div key={chart.label} className="space-y-1">
                <div className="text-[10px] text-muted-foreground">{chart.label}</div>
                <SparkLine values={chart.values} color={chart.color} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
