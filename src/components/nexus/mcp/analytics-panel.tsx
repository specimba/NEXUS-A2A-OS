'use client'

import { useState } from 'react'
import useSWR from 'swr'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TrendingUp, AlertOctagon, Plug, Activity } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { jsonFetcher } from '@/lib/mcp-fetcher'

interface AnalyticsResponse {
  windowHours: number
  total: number
  errors: number
  errorRate: number
  connectedCount: number
  totalConnections: number
  timeseries: Array<{ ts: number; info: number; warn: number; error: number; debug: number }>
  topTopics: Array<{ topic: string; count: number }>
  byConnection: Array<{
    id: string
    name: string
    status: string
    eventsInWindow: number
    lifetimeEvents: number
    lifetimeErrors: number
  }>
}

const PIE_COLORS = ['#10b981', '#06b6d4', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#84cc16']

export function AnalyticsPanel() {
  const [hours, setHours] = useState('24')
  const { data, isLoading } = useSWR<AnalyticsResponse>(
    `/api/mcp/analytics?hours=${hours}`,
    jsonFetcher,
    { refreshInterval: 15000 },
  )

  // Defensive: `data` is undefined on error, and `timeseries`/`topTopics`/`byConnection`
  // might be missing on a partial/error response. Arrays are required for Recharts.
  const timeseries = (Array.isArray(data?.timeseries) ? data!.timeseries : []).map((row) => ({
    ...row,
    label: new Date(row.ts).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  }))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Activity className="h-4 w-4 text-emerald-500" />
          UI/UX & MCP telemetry — augmented by PostHog when configured
        </div>
        <Select value={hours} onValueChange={setHours}>
          <SelectTrigger className="h-8 w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">Last hour</SelectItem>
            <SelectItem value="6">Last 6 hours</SelectItem>
            <SelectItem value="24">Last 24 hours</SelectItem>
            <SelectItem value="72">Last 3 days</SelectItem>
            <SelectItem value="168">Last 7 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Events"
          value={(data?.total ?? 0).toLocaleString()}
          tone="emerald"
          loading={isLoading}
        />
        <KpiCard
          icon={<AlertOctagon className="h-4 w-4" />}
          label="Error rate"
          value={`${((data?.errorRate ?? 0) * 100).toFixed(1)}%`}
          tone={data && data.errorRate > 0.05 ? 'rose' : 'sky'}
          loading={isLoading}
        />
        <KpiCard
          icon={<Plug className="h-4 w-4" />}
          label="Connected"
          value={`${data?.connectedCount ?? 0} / ${data?.totalConnections ?? 0}`}
          tone="emerald"
          loading={isLoading}
        />
        <KpiCard
          icon={<Activity className="h-4 w-4" />}
          label="Top topic"
          value={data?.topTopics?.[0]?.topic ?? '—'}
          tone="amber"
          loading={isLoading}
          mono
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Card className="p-4 lg:col-span-2">
          <header className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-sm">Events over time</h3>
              <p className="text-xs text-muted-foreground">
                Stacked by level — last {data?.windowHours ?? hours} hours
              </p>
            </div>
            <Badge variant="secondary" className="text-[10px]">
              {timeseries.length} buckets
            </Badge>
          </header>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={timeseries}>
              <defs>
                <linearGradient id="g-info" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="g-warn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.6} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="g-error" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.7} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="info" name="Info" stackId="1" stroke="#06b6d4" fill="url(#g-info)" />
              <Area type="monotone" dataKey="warn" name="Warn" stackId="1" stroke="#f59e0b" fill="url(#g-warn)" />
              <Area type="monotone" dataKey="error" name="Error" stackId="1" stroke="#ef4444" fill="url(#g-error)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-4">
          <header className="mb-3">
            <h3 className="font-semibold text-sm">Top topics</h3>
            <p className="text-xs text-muted-foreground">Distribution by event topic</p>
          </header>
          {data?.topTopics && data.topTopics.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={data.topTopics}
                  dataKey="count"
                  nameKey="topic"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                >
                  {data.topTopics.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--popover))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 10 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[260px] flex items-center justify-center text-xs text-muted-foreground">
              No events in window
            </div>
          )}
        </Card>
      </div>

      <Card className="p-4">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm">By connection</h3>
            <p className="text-xs text-muted-foreground">Events received per source</p>
          </div>
        </header>
        {data?.byConnection && data.byConnection.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.byConnection}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
              <YAxis tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="eventsInWindow" name="In window" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="lifetimeErrors" name="Lifetime errors" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[220px] flex items-center justify-center text-xs text-muted-foreground">
            No connections configured
          </div>
        )}
      </Card>
    </div>
  )
}

function KpiCard({
  icon,
  label,
  value,
  tone,
  loading,
  mono,
}: {
  icon: React.ReactNode
  label: string
  value: string
  tone: 'emerald' | 'sky' | 'amber' | 'rose'
  loading: boolean
  mono?: boolean
}) {
  const tones: Record<string, string> = {
    emerald: 'text-emerald-500 bg-emerald-500/10',
    sky: 'text-sky-500 bg-sky-500/10',
    amber: 'text-amber-500 bg-amber-500/10',
    rose: 'text-rose-500 bg-rose-500/10',
  }
  return (
    <Card className="p-3">
      <div className={cn('h-8 w-8 rounded-md flex items-center justify-center mb-2', tones[tone])}>{icon}</div>
      <div className={cn('text-2xl font-bold tabular-nums', mono && 'font-mono text-base truncate')}>
        {loading ? '…' : value}
      </div>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
    </Card>
  )
}
