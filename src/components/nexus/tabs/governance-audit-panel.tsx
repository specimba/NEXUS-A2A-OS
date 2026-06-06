'use client'

import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Shield,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  FileWarning,
  Activity,
} from 'lucide-react'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

// ─── Types ───

interface ComplianceData {
  score: number
  allowCount: number
  denyCount: number
  holdCount: number
  totalDecisions: number
  trend: { direction: 'up' | 'down' | 'stable'; delta: number }
}

interface ThreatData {
  categories: { name: string; count: number }[]
  severityDistribution: {
    critical: number
    high: number
    medium: number
    low: number
    clean: number
  }
}

interface AgentComplianceEntry {
  id: string
  name: string
  trust: number
  totalDecisions: number
  allowed: number
  denied: number
  held: number
  complianceRate: number
  violationRate: number
}

interface ViolationTimelineEntry {
  hour: string
  deny: number
  hold: number
}

interface AuditEvent {
  id: string
  type: 'decision' | 'vault_event'
  agent: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  decision?: string
  action: string
  scope: string
  trust: number
  reason?: string | null
  timestamp: string
}

interface GovernanceAuditAPIResponse {
  compliance: ComplianceData
  threats: ThreatData
  agentCompliance: AgentComplianceEntry[]
  violationTimeline: ViolationTimelineEntry[]
  auditEvents: AuditEvent[]
}

// ─── Fallback data ───

const fallbackData: GovernanceAuditAPIResponse = {
  compliance: {
    score: 87,
    allowCount: 0,
    denyCount: 0,
    holdCount: 0,
    totalDecisions: 0,
    trend: { direction: 'stable', delta: 0 },
  },
  threats: {
    categories: [],
    severityDistribution: { critical: 0, high: 0, medium: 0, low: 0, clean: 0 },
  },
  agentCompliance: [],
  violationTimeline: Array.from({ length: 24 }, (_, i) => ({
    hour: `${String(23 - i).padStart(2, '0')}:00`,
    deny: 0,
    hold: 0,
  })),
  auditEvents: [],
}

// ─── Severity Helpers ───

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f87171',
  high: '#fb923c',
  medium: '#facc15',
  low: '#34d399',
}

const SEVERITY_BADGE_CLASSES: Record<string, string> = {
  critical: 'bg-red-600/15 text-red-600 dark:text-red-400',
  high: 'bg-orange-600/15 text-orange-600 dark:text-orange-400',
  medium: 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400',
  low: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400',
}

const SEVERITY_ICONS: Record<string, React.ElementType> = {
  critical: XCircle,
  high: AlertTriangle,
  medium: Clock,
  low: CheckCircle2,
}

// ─── Sub-Components ───

function ComplianceScoreCard({ compliance }: { compliance: ComplianceData }) {
  const TrendIcon = compliance.trend.direction === 'up'
    ? TrendingUp
    : compliance.trend.direction === 'down'
      ? TrendingDown
      : Minus

  const trendColor = compliance.trend.direction === 'up'
    ? 'text-emerald-600 dark:text-emerald-400'
    : compliance.trend.direction === 'down'
      ? 'text-red-600 dark:text-red-400'
      : 'text-muted-foreground'

  const scoreColor = compliance.score >= 80
    ? 'text-emerald-600 dark:text-emerald-400'
    : compliance.score >= 60
      ? 'text-yellow-600 dark:text-yellow-400'
      : 'text-red-600 dark:text-red-400'

  const progressColor = compliance.score >= 80
    ? '[&>div]:bg-emerald-500'
    : compliance.score >= 60
      ? '[&>div]:bg-yellow-500'
      : '[&>div]:bg-red-500'

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-purple-600/5" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Compliance Score
          </CardTitle>
          <DataSourceBadge source="computed" />
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="flex items-end justify-between mb-3">
          <div>
            <p className={`text-4xl font-bold tabular-nums ${scoreColor}`}>
              {compliance.score}%
            </p>
            <p className="text-[11px] text-muted-foreground mt-1">
              {compliance.totalDecisions} decisions evaluated
            </p>
          </div>
          <div className={`flex items-center gap-1 ${trendColor}`}>
            <TrendIcon className="h-4 w-4" />
            <span className="text-xs font-medium tabular-nums">
              {compliance.trend.delta > 0 ? '+' : ''}{compliance.trend.delta}%
            </span>
          </div>
        </div>
        <Progress value={compliance.score} className={`h-2.5 ${progressColor}`} />
        <div className="mt-3 grid grid-cols-3 gap-2">
          <div className="rounded-md bg-emerald-600/10 px-2 py-1.5 text-center">
            <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{compliance.allowCount}</p>
            <p className="text-[9px] text-muted-foreground">ALLOW</p>
          </div>
          <div className="rounded-md bg-red-600/10 px-2 py-1.5 text-center">
            <p className="text-sm font-bold text-red-600 dark:text-red-400 tabular-nums">{compliance.denyCount}</p>
            <p className="text-[9px] text-muted-foreground">DENY</p>
          </div>
          <div className="rounded-md bg-yellow-600/10 px-2 py-1.5 text-center">
            <p className="text-sm font-bold text-yellow-600 dark:text-yellow-400 tabular-nums">{compliance.holdCount}</p>
            <p className="text-[9px] text-muted-foreground">HOLD</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ViolationTimelineChart({ data }: { data: ViolationTimelineEntry[] }) {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-red-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <FileWarning className="h-4 w-4 text-red-600 dark:text-red-400" />
            Policy Violation Timeline
          </CardTitle>
          <DataSourceBadge source="computed" />
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, bottom: 2, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} />
              <XAxis
                dataKey="hour"
                tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }}
                interval={3}
              />
              <YAxis
                tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }}
                allowDecimals={false}
              />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '11px',
                  color: 'var(--foreground)',
                }}
                labelStyle={{ color: 'var(--foreground)' }}
                itemStyle={{ color: 'var(--muted-foreground)' }}
              />
              <Bar dataKey="deny" name="DENY" stackId="violations" fill="#f87171" radius={[0, 0, 0, 0]} />
              <Bar dataKey="hold" name="HOLD" stackId="violations" fill="#facc15" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex items-center justify-center gap-4 text-[10px]">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-red-400" />
            <span className="text-muted-foreground">DENY</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-yellow-400" />
            <span className="text-muted-foreground">HOLD</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ThreatLevelDistribution({ data }: { data: ThreatData }) {
  const chartData = [
    { name: 'CRITICAL', value: data.severityDistribution.critical, color: '#f87171' },
    { name: 'HIGH', value: data.severityDistribution.high, color: '#fb923c' },
    { name: 'MEDIUM', value: data.severityDistribution.medium, color: '#facc15' },
    { name: 'LOW', value: data.severityDistribution.low, color: '#34d399' },
    { name: 'CLEAN', value: data.severityDistribution.clean, color: '#6ee7b7' },
  ].filter((d) => d.value > 0)

  const total = chartData.reduce((sum, d) => sum + d.value, 0)

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-orange-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            Threat Level Distribution
          </CardTitle>
          <DataSourceBadge source="computed" />
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
            No threat data recorded yet
          </div>
        ) : (
          <>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={35}
                    outerRadius={60}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: 'var(--card)',
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: 'var(--foreground)',
                    }}
                    labelStyle={{ color: 'var(--foreground)' }}
                    itemStyle={{ color: 'var(--muted-foreground)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
              {chartData.map((d, idx) => (
                <div key={`threat-${d.name}-${idx}`} className="flex items-center gap-1.5 text-[10px]">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-muted-foreground">{d.name}</span>
                  <span className="font-medium tabular-nums">{d.value}</span>
                  {total > 0 && (
                    <span className="text-muted-foreground/60">({((d.value / total) * 100).toFixed(0)}%)</span>
                  )}
                </div>
              ))}
            </div>
            {/* Threat categories detail */}
            {data.categories.length > 0 && (
              <div className="mt-3 space-y-1.5">
                <p className="text-[10px] font-medium text-muted-foreground uppercase">Top Threat Categories</p>
                {data.categories.slice(0, 5).map((cat, idx) => (
                  <div key={`cat-${cat.name}-${idx}`} className="flex items-center justify-between rounded-md bg-accent/30 px-2.5 py-1.5">
                    <span className="text-[10px] truncate">{cat.name}</span>
                    <Badge variant="outline" className="text-[8px] tabular-nums">{cat.count}</Badge>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function AgentComplianceRanking({ agents }: { agents: AgentComplianceEntry[] }) {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            Agent Compliance Ranking
          </CardTitle>
          <DataSourceBadge source="computed" />
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        {agents.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
            No agent compliance data available
          </div>
        ) : (
          <div className="max-h-72 overflow-y-auto custom-scrollbar">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[9px] h-8">Agent</TableHead>
                  <TableHead className="text-[9px] h-8 text-center">Compliance</TableHead>
                  <TableHead className="text-[9px] h-8 text-center">Violations</TableHead>
                  <TableHead className="text-[9px] h-8 text-center">Trust</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((agent, idx) => (
                  <TableRow key={agent.id ?? `agent-${idx}`}>
                    <TableCell className="text-[11px] font-medium py-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[9px] text-muted-foreground w-4 text-right">{idx + 1}</span>
                        {agent.name}
                      </div>
                    </TableCell>
                    <TableCell className="py-1.5 text-center">
                      <div className="flex items-center gap-1.5 justify-center">
                        <div className="w-12">
                          <Progress
                            value={agent.complianceRate}
                            className={`h-1.5 ${
                              agent.complianceRate >= 80 ? '[&>div]:bg-emerald-500' :
                              agent.complianceRate >= 60 ? '[&>div]:bg-yellow-500' :
                              '[&>div]:bg-red-500'
                            }`}
                          />
                        </div>
                        <span className={`text-[10px] font-medium tabular-nums ${
                          agent.complianceRate >= 80 ? 'text-emerald-600 dark:text-emerald-400' :
                          agent.complianceRate >= 60 ? 'text-yellow-600 dark:text-yellow-400' :
                          'text-red-600 dark:text-red-400'
                        }`}>
                          {agent.complianceRate}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="py-1.5 text-center">
                      <span className="text-[10px] tabular-nums text-red-600 dark:text-red-400">
                        {agent.denied + agent.held}
                      </span>
                      <span className="text-[9px] text-muted-foreground">/{agent.totalDecisions}</span>
                    </TableCell>
                    <TableCell className="py-1.5 text-center">
                      <span className={`text-[10px] font-medium tabular-nums ${
                        agent.trust >= 0.7 ? 'text-emerald-600 dark:text-emerald-400' :
                        agent.trust >= 0.5 ? 'text-yellow-600 dark:text-yellow-400' :
                        'text-red-600 dark:text-red-400'
                      }`}>
                        {agent.trust.toFixed(2)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function RecentAuditEvents({ events }: { events: AuditEvent[] }) {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <FileWarning className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            Recent Audit Events
          </CardTitle>
          <DataSourceBadge source="computed" />
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        {events.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
            No audit events recorded yet
          </div>
        ) : (
          <div className="max-h-96 space-y-1.5 overflow-y-auto custom-scrollbar">
            {events.map((event, idx) => {
              const SeverityIcon = SEVERITY_ICONS[event.severity] ?? CheckCircle2
              const time = new Date(event.timestamp).toLocaleTimeString('en-US', { hour12: false })
              const date = new Date(event.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

              return (
                <div
                  key={`${event.id}-${idx}`}
                  className="flex items-start gap-2.5 rounded-md bg-accent/30 px-3 py-2.5 text-xs hover:bg-accent/50 transition-colors"
                >
                  <SeverityIcon className={`h-3.5 w-3.5 shrink-0 mt-0.5 ${
                    event.severity === 'critical' ? 'text-red-600 dark:text-red-400' :
                    event.severity === 'high' ? 'text-orange-600 dark:text-orange-400' :
                    event.severity === 'medium' ? 'text-yellow-600 dark:text-yellow-400' :
                    'text-emerald-600 dark:text-emerald-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <Badge className={`text-[7px] border-0 ${SEVERITY_BADGE_CLASSES[event.severity] ?? ''}`}>
                        {event.severity.toUpperCase()}
                      </Badge>
                      {event.decision && (
                        <Badge className={`text-[7px] border-0 ${
                          event.decision === 'ALLOW' ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
                          event.decision === 'DENY' ? 'bg-red-600/15 text-red-600 dark:text-red-400' :
                          'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
                        }`}>
                          {event.decision}
                        </Badge>
                      )}
                      <Badge variant="outline" className="text-[7px]">{event.type === 'decision' ? 'DEC' : 'VAULT'}</Badge>
                      <span className="font-mono text-[9px] text-muted-foreground tabular-nums">{date} {time}</span>
                    </div>
                    <p className="text-[11px] text-foreground truncate">
                      <span className="text-muted-foreground">{event.agent}</span>
                      <span className="mx-1 text-muted-foreground/50">→</span>
                      <span className="truncate">{event.action}</span>
                    </p>
                    {event.reason && (
                      <p className="text-[9px] text-muted-foreground truncate mt-0.5">{event.reason}</p>
                    )}
                  </div>
                  <span className="text-[9px] text-muted-foreground tabular-nums shrink-0">
                    {event.trust.toFixed(2)}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Main Component ───

export function GovernanceAuditPanel() {
  const { data, loading } = useApiData<GovernanceAuditAPIResponse>('/api/governance-audit', 30000)

  const auditData = useMemo(() => {
    if (!data) return fallbackData
    return data
  }, [data])

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          <h3 className="text-sm font-semibold">Governance Audit</h3>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 w-32 bg-muted/50 rounded mb-3" />
              <div className="h-10 w-16 bg-muted/50 rounded mb-2" />
              <div className="h-2 w-full bg-muted/30 rounded" />
            </CardContent>
          </Card>
          <Card className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 w-40 bg-muted/50 rounded mb-3" />
              <div className="h-40 bg-muted/30 rounded" />
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-purple-600 shadow-lg shadow-emerald-600/10">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Governance Audit</h3>
            <p className="text-[10px] text-muted-foreground">
              Compliance monitoring · Threat scanning · Audit trail
            </p>
          </div>
        </div>
        <DataSourceBadge source="computed" />
      </div>

      {/* Compliance Score + Threat Distribution */}
      <div className="grid gap-4 md:grid-cols-2">
        <ComplianceScoreCard compliance={auditData.compliance} />
        <ThreatLevelDistribution data={auditData.threats} />
      </div>

      {/* Violation Timeline + Agent Compliance */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ViolationTimelineChart data={auditData.violationTimeline} />
        <AgentComplianceRanking agents={auditData.agentCompliance} />
      </div>

      {/* Recent Audit Events */}
      <RecentAuditEvents events={auditData.auditEvents} />
    </div>
  )
}
