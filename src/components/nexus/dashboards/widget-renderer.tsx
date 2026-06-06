'use client'

import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import {
  TrendingUp,
  BarChart3,
  Activity,
  Gauge,
  Hash,
  PieChart,
  Table,
  ScrollText,
  FileText,
  Grid3x3,
  Loader2,
  Target,
  Users,
  Coins,
  Network,
  Bell,
  Shield,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Zap,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart as RechartsPie,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts'
import type { DashboardWidget, MetricSeries, WidgetType } from '@/lib/dashboard-types'
import { generateMockSeries, DATA_SOURCES } from '@/lib/dashboard-types'

// NEXUS metrics type (from /api/dashboards/metrics)
export interface NexusMetrics {
  agents: { total: number; active: number; avgTrust: number; topAgent: string }
  tokens: { budgetTotal: number; budgetUsed: number; budgetRemaining: number; burnRate: number; topModel: string }
  models: { total: number; healthy: number; degraded: number; avgLatency: number; freeModels: number }
  governor: { totalDecisions: number; blocked: number; compliance: number }
  swarm: { totalWorkers: number; activeWorkers: number; errorRate: number }
  system: { uptime: string; healthScore: number; pillars: Record<string, { health: number; status: string }> }
  research: { totalPapers: number; vetted: number; avgRelevance: number }
  rateLimits: { totalProviders: number; activeKeys: number; rateLimitedKeys: number }
  providers: { total: number; available: number; totalModels: number }
  timeSeries: {
    tokens: { labels: string[]; values: number[] }
    requests: { labels: string[]; values: number[] }
    errors: { labels: string[]; values: number[] }
    health: { labels: string[]; values: number[] }
  }
  alertFeed: { id: string; type: string; title: string; message: string; time: string }[]
}

const COLORS = ['#34d399', '#60a5fa', '#a78bfa', '#fb923c', '#f87171', '#facc15', '#f472b6', '#2dd4bf']

const WIDGET_ICONS: Record<string, React.ElementType> = {
  line_chart: TrendingUp,
  bar_chart: BarChart3,
  area_chart: Activity,
  gauge: Gauge,
  stat_card: Hash,
  pie_chart: PieChart,
  table: Table,
  log_stream: ScrollText,
  markdown: FileText,
  heatmap: Grid3x3,
  kpi: Target,
  agent_health: Users,
  token_gauge: Coins,
  model_relay: Network,
  alert_feed: Bell,
}

const tooltipStyle: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  fontSize: '11px',
  color: 'var(--foreground)',
}

interface WidgetRendererProps {
  widget: DashboardWidget
  metrics: MetricSeries[]
  nexusMetrics?: NexusMetrics | null
  isEditing?: boolean
  onEdit?: () => void
  onDelete?: () => void
  className?: string
}

export function WidgetRenderer({
  widget,
  metrics,
  nexusMetrics,
  isEditing,
  onEdit,
  onDelete,
  className,
}: WidgetRendererProps) {
  const Icon = WIDGET_ICONS[widget.type] || Activity

  // Find metric data for this widget's data source, or generate mock data
  const seriesData = useMemo(() => {
    const matched = metrics.find((s) => s.key === widget.dataSource)
    if (matched && matched.data.length > 0) {
      return matched
    }
    // Generate mock series
    const source = DATA_SOURCES.find((s) => s.key === widget.dataSource)
    return {
      key: widget.dataSource,
      label: source?.label || widget.dataSource,
      data: generateMockSeries(widget.dataSource, 20).map((dp, i) => ({
        name: `${i}`,
        value: dp.value,
        timestamp: dp.timestamp,
      })),
      unit: source?.unit,
    }
  }, [metrics, widget.dataSource])

  if (widget.collapsed) {
    return (
      <Card
        className={cn(
          'bg-card/50 border-border/50 transition-all',
          isEditing && 'cursor-move',
          className,
        )}
      >
        <CardContent className="p-3 flex items-center gap-2">
          <Icon className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span className="text-xs font-medium truncate">{widget.title}</span>
          <Badge variant="outline" className="text-[9px] h-4 ml-auto shrink-0">
            {widget.type.replace('_', ' ')}
          </Badge>
          {isEditing && (
            <div className="flex gap-1 ml-2 shrink-0">
              <button
                onClick={onEdit}
                className="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Expand widget"
              >
                <TrendingUp className="h-3 w-3" />
              </button>
              <button
                onClick={onDelete}
                className="text-muted-foreground hover:text-red-500 transition-colors"
                aria-label="Delete widget"
              >
                ×
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      className={cn(
        'bg-card/50 border-border/50 transition-all group h-full flex flex-col',
        isEditing && 'cursor-move ring-1 ring-transparent hover:ring-emerald-600/30',
        className,
      )}
    >
      <CardHeader className="pb-1 pt-3 px-3 flex-row items-center justify-between space-y-0">
        <CardTitle className="text-xs font-semibold flex items-center gap-1.5 min-w-0">
          <Icon className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span className="truncate">{widget.title}</span>
        </CardTitle>
        <div className="flex items-center gap-1 shrink-0">
          <Badge variant="outline" className="text-[8px] h-3.5 px-1">
            {widget.dataSource.split('.').pop()}
          </Badge>
          {isEditing && (
            <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={onEdit}
                className="p-0.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                aria-label="Edit widget"
              >
                <FileText className="h-3 w-3" />
              </button>
              <button
                onClick={onDelete}
                className="p-0.5 rounded text-muted-foreground hover:text-red-500 hover:bg-muted/50 transition-colors"
                aria-label="Delete widget"
              >
                ×
              </button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="px-3 pb-3 flex-1 min-h-0">
        <WidgetContent widget={widget} seriesData={seriesData} nexusMetrics={nexusMetrics} />
      </CardContent>
    </Card>
  )
}

function WidgetContent({
  widget,
  seriesData,
  nexusMetrics,
}: {
  widget: DashboardWidget
  seriesData: MetricSeries & { data: { name: string; value: number; timestamp: number }[] }
  nexusMetrics?: NexusMetrics | null
}) {
  const chartData = seriesData.data
  const unit = seriesData.unit || (widget.config.unit as string) || ''

  // NEXUS-specific widget types
  switch (widget.type) {
    case 'kpi': {
      const ds = widget.dataSource as string
      const kpiItems: { label: string; value: string; status: 'ok' | 'warning' | 'error' }[] = []

      if (ds === 'system' && nexusMetrics) {
        kpiItems.push(
          { label: 'Health Score', value: `${nexusMetrics.system.healthScore}%`, status: nexusMetrics.system.healthScore > 80 ? 'ok' : 'warning' },
          { label: 'Uptime', value: nexusMetrics.system.uptime, status: 'ok' },
          { label: 'Agents Active', value: `${nexusMetrics.agents.active}/${nexusMetrics.agents.total}`, status: 'ok' },
        )
      } else if (ds === 'agents' && nexusMetrics) {
        kpiItems.push(
          { label: 'Total Agents', value: String(nexusMetrics.agents.total), status: 'ok' },
          { label: 'Active', value: String(nexusMetrics.agents.active), status: 'ok' },
          { label: 'Avg Trust', value: nexusMetrics.agents.avgTrust.toFixed(2), status: nexusMetrics.agents.avgTrust > 0.7 ? 'ok' : 'warning' },
        )
      } else if (ds === 'tokens' && nexusMetrics) {
        kpiItems.push(
          { label: 'Budget Used', value: `${Math.round(nexusMetrics.tokens.budgetUsed / nexusMetrics.tokens.budgetTotal * 100)}%`, status: 'ok' },
          { label: 'Remaining', value: nexusMetrics.tokens.budgetRemaining.toLocaleString(), status: 'ok' },
          { label: 'Burn Rate', value: `${nexusMetrics.tokens.burnRate} tok/min`, status: 'ok' },
        )
      } else if (ds === 'models' && nexusMetrics) {
        kpiItems.push(
          { label: 'Total Models', value: String(nexusMetrics.models.total), status: 'ok' },
          { label: 'Healthy', value: String(nexusMetrics.models.healthy), status: 'ok' },
          { label: 'Degraded', value: String(nexusMetrics.models.degraded), status: nexusMetrics.models.degraded > 0 ? 'warning' : 'ok' },
        )
      } else if (ds === 'governor' && nexusMetrics) {
        kpiItems.push(
          { label: 'Decisions', value: String(nexusMetrics.governor.totalDecisions), status: 'ok' },
          { label: 'Blocked', value: String(nexusMetrics.governor.blocked), status: nexusMetrics.governor.blocked > 0 ? 'warning' : 'ok' },
          { label: 'Compliance', value: `${nexusMetrics.governor.compliance}%`, status: 'ok' },
        )
      } else {
        kpiItems.push(
          { label: 'Status', value: 'No data', status: 'warning' },
        )
      }

      const statusIcon = { ok: CheckCircle2, warning: AlertTriangle, error: XCircle }
      const statusColor = { ok: 'text-emerald-600 dark:text-emerald-400', warning: 'text-yellow-600 dark:text-yellow-400', error: 'text-red-600 dark:text-red-400' }

      return (
        <div className="h-full flex flex-col justify-center gap-2">
          {kpiItems.map((item) => {
            const SIcon = statusIcon[item.status]
            return (
              <div key={item.label} className="flex items-center justify-between">
                <span className="text-[10px] text-muted-foreground">{item.label}</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-bold font-mono">{item.value}</span>
                  <SIcon className={cn('h-3 w-3', statusColor[item.status])} />
                </div>
              </div>
            )
          })}
        </div>
      )
    }

    case 'agent_health': {
      const agents = nexusMetrics?.agents
      const swarm = nexusMetrics?.swarm
      if (!agents || !swarm) {
        return <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No agent data</div>
      }
      const mockAgents = [
        { name: 'coordinator', status: 'idle', trust: agents.avgTrust + 0.05, model: 'trinity-large' },
        { name: 'worker-1', status: 'busy', trust: agents.avgTrust + 0.03, model: 'trinity-large' },
        { name: 'worker-2', status: 'idle', trust: agents.avgTrust - 0.02, model: 'qwen3-coder' },
        { name: 'worker-3', status: 'busy', trust: agents.avgTrust - 0.05, model: 'gemma-fast' },
      ]
      return (
        <div className="h-full overflow-auto custom-scrollbar space-y-1.5">
          {mockAgents.map((agent) => (
            <div key={agent.name} className="flex items-center gap-2 p-1.5 rounded bg-muted/30">
              <span className={cn(
                'h-2 w-2 rounded-full shrink-0',
                agent.status === 'busy' ? 'bg-emerald-400' : 'bg-yellow-400'
              )} />
              <span className="text-[10px] font-medium truncate flex-1">{agent.name}</span>
              <Badge variant="outline" className="text-[8px] h-3.5 px-1 shrink-0">{agent.model}</Badge>
              <span className="text-[10px] font-mono text-muted-foreground shrink-0">{agent.trust.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )
    }

    case 'token_gauge': {
      const tokens = nexusMetrics?.tokens
      if (!tokens) {
        return <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No token data</div>
      }
      const pct = Math.round(tokens.budgetUsed / tokens.budgetTotal * 100)
      const remaining = tokens.budgetRemaining
      const color = pct > 80 ? '#f87171' : pct > 60 ? '#fb923c' : '#34d399'
      return (
        <div className="h-full flex flex-col items-center justify-center gap-2">
          <div className="relative w-full max-w-[100px] aspect-square">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPie>
                <Pie
                  data={[
                    { name: 'used', value: pct },
                    { name: 'remaining', value: 100 - pct },
                  ]}
                  cx="50%"
                  cy="50%"
                  innerRadius="65%"
                  outerRadius="100%"
                  startAngle={180}
                  endAngle={0}
                  dataKey="value"
                  stroke="none"
                >
                  <Cell fill={color} />
                  <Cell fill="var(--muted)" />
                </Pie>
              </RechartsPie>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-sm font-bold" style={{ color }}>{pct}%</span>
              <span className="text-[8px] text-muted-foreground">used</span>
            </div>
          </div>
          <div className="text-center space-y-0.5">
            <div className="text-[10px] text-muted-foreground">Remaining: <span className="font-mono font-medium text-foreground">{remaining.toLocaleString()}</span></div>
            <div className="text-[10px] text-muted-foreground">Burn: <span className="font-mono font-medium text-foreground">{tokens.burnRate} tok/min</span></div>
          </div>
        </div>
      )
    }

    case 'model_relay': {
      const providers = nexusMetrics?.providers
      const models = nexusMetrics?.models
      if (!providers || !models) {
        return <div className="h-full flex items-center justify-center text-xs text-muted-foreground">No relay data</div>
      }
      const mockProviders = [
        { name: 'z-ai SDK', status: 'up', latency: 89, models: 1 },
        { name: 'OpenRouter', status: 'up', latency: 245, models: 8 },
        { name: 'NVIDIA NIM', status: 'up', latency: 198, models: 5 },
        { name: 'Cerebras', status: 'degraded', latency: 45, models: 2 },
        { name: 'Groq', status: 'up', latency: 32, models: 3 },
        { name: 'Mistral', status: 'up', latency: 156, models: 2 },
        { name: 'Codestral', status: 'up', latency: 134, models: 1 },
        { name: 'Fireworks', status: 'down', latency: 0, models: 2 },
      ]
      const stateDot: Record<string, string> = { up: 'bg-emerald-400', degraded: 'bg-yellow-400', down: 'bg-red-400' }
      return (
        <div className="h-full overflow-auto custom-scrollbar space-y-1">
          {mockProviders.map((p) => (
            <div key={p.name} className="flex items-center gap-2 p-1 rounded hover:bg-muted/30">
              <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', stateDot[p.status])} />
              <span className="text-[10px] font-medium flex-1 truncate">{p.name}</span>
              <span className="text-[9px] font-mono text-muted-foreground shrink-0">{p.latency > 0 ? `${p.latency}ms` : '—'}</span>
              <Badge variant="outline" className="text-[7px] h-3 px-0.5 shrink-0">{p.models}</Badge>
            </div>
          ))}
        </div>
      )
    }

    case 'alert_feed': {
      const alerts = nexusMetrics?.alertFeed || [
        { id: '1', type: 'info', title: 'System Online', message: 'All subsystems operational', time: new Date().toISOString() },
        { id: '2', type: 'warning', title: 'Token Budget', message: 'Session at 23% utilization', time: new Date(Date.now() - 60000).toISOString() },
      ]
      const typeConfig: Record<string, { icon: typeof Bell; color: string; bg: string }> = {
        info: { icon: Bell, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-600/20' },
        warning: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-600/20' },
        error: { icon: XCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/20' },
        success: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/20' },
      }
      return (
        <div className="h-full overflow-auto custom-scrollbar space-y-1">
          {alerts.slice(0, 8).map((alert) => {
            const cfg = typeConfig[alert.type] || typeConfig.info
            const AIcon = cfg.icon
            return (
              <div key={alert.id} className="flex items-start gap-1.5 p-1.5 rounded hover:bg-muted/30">
                <AIcon className={cn('h-3 w-3 shrink-0 mt-0.5', cfg.color)} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] font-medium truncate">{alert.title}</span>
                    <Badge className={cn('text-[7px] h-3 px-0.5 border-0 shrink-0', cfg.bg, cfg.color)}>{alert.type}</Badge>
                  </div>
                  <p className="text-[9px] text-muted-foreground truncate">{alert.message}</p>
                </div>
              </div>
            )
          })}
        </div>
      )
    }

    // ─── Chart / display widget types ───────────────────────────────────

    case 'line_chart':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} width={30} />
            <RechartsTooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="value" stroke="#34d399" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )

    case 'bar_chart':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} width={30} />
            <RechartsTooltip contentStyle={tooltipStyle} />
            <Bar dataKey="value" fill="#34d399" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )

    case 'area_chart':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
            <defs>
              <linearGradient id={`area-grad-${widget.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#34d399" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} width={30} />
            <RechartsTooltip contentStyle={tooltipStyle} />
            <Area type="monotone" dataKey="value" stroke="#34d399" fill={`url(#area-grad-${widget.id})`} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      )

    case 'gauge': {
      const latestValue = chartData[chartData.length - 1]?.value ?? 0
      const pct = Math.min(100, Math.max(0, latestValue))
      const color = pct > 80 ? '#f87171' : pct > 60 ? '#fb923c' : '#34d399'
      return (
        <div className="h-full flex flex-col items-center justify-center">
          <div className="relative w-full max-w-[120px] aspect-square">
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPie>
                <Pie
                  data={[
                    { name: 'value', value: pct },
                    { name: 'bg', value: 100 - pct },
                  ]}
                  cx="50%"
                  cy="50%"
                  innerRadius="70%"
                  outerRadius="100%"
                  startAngle={180}
                  endAngle={0}
                  dataKey="value"
                  stroke="none"
                >
                  <Cell fill={color} />
                  <Cell fill="var(--muted)" />
                </Pie>
              </RechartsPie>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-lg font-bold" style={{ color }}>
                {Math.round(latestValue)}
              </span>
              <span className="text-[9px] text-muted-foreground">{unit}</span>
            </div>
          </div>
        </div>
      )
    }

    case 'stat_card': {
      const latest = chartData[chartData.length - 1]?.value ?? 0
      const prev = chartData.length > 1 ? chartData[chartData.length - 2]?.value ?? latest : latest
      const trend = latest - prev
      const isUp = trend >= 0
      return (
        <div className="h-full flex flex-col items-center justify-center text-center">
          <div className="text-3xl font-bold tabular-nums text-foreground">
            {typeof latest === 'number' && latest < 1 ? latest.toFixed(3) : Math.round(latest * 100) / 100}
          </div>
          {unit && <div className="text-[10px] text-muted-foreground mt-0.5">{unit}</div>}
          {trend !== 0 && (
            <div className={cn('flex items-center gap-0.5 mt-1 text-[10px]', isUp ? 'text-emerald-600' : 'text-red-500')}>
              <TrendingUp className={cn('h-3 w-3', !isUp && 'rotate-180')} />
              {isUp ? '+' : ''}{Math.round(trend * 100) / 100}
            </div>
          )}
        </div>
      )
    }

    case 'pie_chart': {
      const pieData = chartData.slice(-6).map((d, i) => ({
        name: d.name,
        value: Math.abs(d.value),
      }))
      return (
        <ResponsiveContainer width="100%" height="100%">
          <RechartsPie>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              innerRadius="40%"
              outerRadius="70%"
              dataKey="value"
              stroke="none"
            >
              {pieData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <RechartsTooltip contentStyle={tooltipStyle} />
          </RechartsPie>
        </ResponsiveContainer>
      )
    }

    case 'table': {
      const rows = chartData.slice(-8)
      return (
        <div className="h-full overflow-auto custom-scrollbar">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-border/30">
                <th className="text-left py-1 px-1.5 text-muted-foreground font-medium">Time</th>
                <th className="text-right py-1 px-1.5 text-muted-foreground font-medium">Value</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-border/10 hover:bg-muted/20">
                  <td className="py-1 px-1.5 font-mono text-muted-foreground">
                    {new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td className="py-1 px-1.5 text-right font-mono font-medium">
                    {Math.round(row.value * 100) / 100} {unit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }

    case 'log_stream': {
      const logs = chartData.slice(-12).reverse()
      const levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
      return (
        <div className="h-full overflow-auto custom-scrollbar font-mono text-[10px] space-y-0.5">
          {logs.map((log, i) => {
            const level = levels[i % levels.length]
            return (
              <div key={i} className="flex gap-2 py-0.5">
                <span className="text-muted-foreground shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <Badge
                  variant="outline"
                  className={cn(
                    'text-[7px] h-3 px-0.5 shrink-0 border-0',
                    level === 'ERROR' && 'bg-red-600/20 text-red-500',
                    level === 'WARN' && 'bg-yellow-600/20 text-yellow-600',
                    level === 'INFO' && 'bg-emerald-600/20 text-emerald-600',
                    level === 'DEBUG' && 'bg-muted text-muted-foreground',
                  )}
                >
                  {level}
                </Badge>
                <span className="truncate text-muted-foreground">
                  {seriesData.label}: {Math.round(log.value * 100) / 100} {unit}
                </span>
              </div>
            )
          })}
        </div>
      )
    }

    case 'markdown':
      return (
        <div className="h-full overflow-auto custom-scrollbar text-xs text-muted-foreground leading-relaxed prose prose-sm dark:prose-invert max-w-none">
          <p>
            <strong>{widget.title}</strong> — {(widget.config.markdown as string) || 'Configure markdown content in widget settings.'}
          </p>
        </div>
      )

    case 'heatmap': {
      const grid = Array.from({ length: 4 }, (_, row) =>
        Array.from({ length: 6 }, (_, col) => {
          const idx = row * 6 + col
          return chartData[idx % chartData.length]?.value ?? 0
        }),
      )
      const maxVal = Math.max(...grid.flat(), 1)
      return (
        <div className="h-full flex items-center justify-center">
          <div className="grid grid-cols-6 gap-0.5">
            {grid.flat().map((val, i) => {
              const intensity = val / maxVal
              return (
                <div
                  key={i}
                  className="w-6 h-6 rounded-sm"
                  style={{
                    backgroundColor: `rgba(52, 211, 153, ${0.1 + intensity * 0.8})`,
                  }}
                  title={`${Math.round(val * 100) / 100} ${unit}`}
                />
              )
            })}
          </div>
        </div>
      )
    }

    default:
      return (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          <Activity className="h-4 w-4 mr-2" />
          <span className="text-xs">{widget.type} widget</span>
        </div>
      )
  }
}
