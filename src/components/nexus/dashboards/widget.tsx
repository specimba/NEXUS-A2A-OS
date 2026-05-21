'use client'

import { useApiData } from '@/hooks/use-api-data'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { GripVertical, Settings, Trash2, Loader2, AlertTriangle } from 'lucide-react'
import { CSS } from '@dnd-kit/utilities'
import { useSortable } from '@dnd-kit/sortable'
import { COLOR_PALETTE, getDataSource, type WidgetType } from './widget-catalog'
import { parseConfig, type CustomWidgetDTO } from './types'
import { cn } from '@/lib/utils'
import { useId } from 'react'

interface MetricResponse {
  type: 'kpi' | 'categorical' | 'series' | 'timeseries' | 'table'
  value?: number
  label?: string
  total?: number
  pct?: number
  suffix?: string
  delta?: number
  data?: { name: string; value: number }[]
  columns?: string[]
  rows?: (string | number)[][]
}

const tooltipStyle: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  fontSize: '11px',
  color: 'var(--foreground)',
}
const axisTick = { fontSize: 10, fill: 'var(--muted-foreground)' }

interface Props {
  widget: CustomWidgetDTO
  editMode: boolean
  onConfigure?: () => void
  onDelete?: () => void
}

export function DashboardWidget({ widget, editMode, onConfigure, onDelete }: Props) {
  const { data, loading, error } = useApiData<MetricResponse>(
    `/api/metrics?source=${encodeURIComponent(widget.dataSource)}`,
    15000,
  )

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: widget.id,
    disabled: !editMode,
  })
  const config = parseConfig(widget.config)
  const accent = (config.color as string) || COLOR_PALETTE[0]

  const dataSource = getDataSource(widget.dataSource)

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    gridColumn: `span ${widget.width} / span ${widget.width}`,
    gridRow: `span ${widget.height} / span ${widget.height}`,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className={cn(
        'relative group flex flex-col overflow-hidden border-border/60 bg-card/80 backdrop-blur-sm transition-colors',
        editMode && 'cursor-default ring-1 ring-primary/10 hover:ring-primary/30',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 p-3 border-b border-border/40">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          {editMode && (
            <button
              {...attributes}
              {...listeners}
              className="mt-0.5 text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing touch-none"
              aria-label="Drag widget"
            >
              <GripVertical className="h-4 w-4" />
            </button>
          )}
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-foreground/90 truncate">
              {widget.title}
            </div>
            {widget.subtitle && (
              <div className="text-[10px] text-muted-foreground truncate">{widget.subtitle}</div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {dataSource && (
            <Badge variant="outline" className="text-[9px] font-normal h-5 px-1.5">
              {dataSource.group}
            </Badge>
          )}
          {editMode && (
            <>
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6"
                onClick={onConfigure}
                aria-label="Configure widget"
              >
                <Settings className="h-3 w-3" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6 text-red-500 hover:text-red-600"
                onClick={onDelete}
                aria-label="Delete widget"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 min-h-0 p-3">
        {loading && !data && (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
          </div>
        )}
        {error && (
          <div className="h-full flex items-center justify-center gap-2 text-xs text-red-500">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>{error}</span>
          </div>
        )}
        {data && !error && (
          <WidgetBody type={widget.type as WidgetType} data={data} accent={accent} />
        )}
      </div>
    </Card>
  )
}

function WidgetBody({
  type,
  data,
  accent,
}: {
  type: WidgetType
  data: MetricResponse
  accent: string
}) {
  const uid = useId()
  const gradId = `widget-grad-${uid}`

  if (type === 'kpi') {
    return (
      <div className="h-full flex flex-col justify-center">
        <div className="text-3xl font-bold tabular-nums" style={{ color: accent }}>
          {typeof data.value === 'number'
            ? data.value.toLocaleString()
            : data.value ?? '—'}
          {data.suffix && <span className="text-xl ml-0.5">{data.suffix}</span>}
        </div>
        {data.label && (
          <div className="text-[11px] text-muted-foreground mt-0.5 truncate">{data.label}</div>
        )}
        {typeof data.pct === 'number' && (
          <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${Math.min(100, data.pct)}%`, background: accent }}
            />
          </div>
        )}
        {typeof data.delta === 'number' && (
          <div className="text-[10px] text-muted-foreground mt-1">
            Δ {data.delta.toLocaleString()} last hour
          </div>
        )}
      </div>
    )
  }

  if (type === 'line') {
    const series = data.data ?? []
    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={accent} stopOpacity={0.4} />
              <stop offset="95%" stopColor={accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
          <YAxis tick={axisTick} axisLine={false} tickLine={false} width={32} />
          <RechartsTooltip contentStyle={tooltipStyle} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={accent}
            fill={`url(#${gradId})`}
            strokeWidth={1.8}
          />
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  if (type === 'bar') {
    const series = data.data ?? []
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={series} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="name"
            tick={axisTick}
            axisLine={false}
            tickLine={false}
            interval={0}
            angle={series.length > 5 ? -30 : 0}
            textAnchor={series.length > 5 ? 'end' : 'middle'}
            height={series.length > 5 ? 50 : 25}
          />
          <YAxis tick={axisTick} axisLine={false} tickLine={false} width={32} />
          <RechartsTooltip contentStyle={tooltipStyle} />
          <Bar dataKey="value" fill={accent} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (type === 'pie') {
    const series = data.data ?? []
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={series}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="45%"
            outerRadius="75%"
            paddingAngle={2}
          >
            {series.map((_, i) => (
              <Cell key={i} fill={COLOR_PALETTE[i % COLOR_PALETTE.length]} />
            ))}
          </Pie>
          <RechartsTooltip contentStyle={tooltipStyle} />
          <Legend
            wrapperStyle={{ fontSize: '10px', color: 'var(--muted-foreground)' }}
            iconType="circle"
            iconSize={6}
          />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (type === 'table') {
    const columns = data.columns ?? []
    const rows = data.rows ?? []
    return (
      <div className="h-full overflow-auto custom-scrollbar -mx-3">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-card/95 backdrop-blur-sm">
            <tr className="border-b border-border/40">
              {columns.map((c) => (
                <th
                  key={c}
                  className="px-3 py-2 text-left font-medium text-[10px] uppercase tracking-wider text-muted-foreground"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-6 text-center text-muted-foreground"
                >
                  No data
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-border/20 hover:bg-accent/40 transition-colors"
                >
                  {row.map((cell, j) => (
                    <td key={j} className="px-3 py-1.5 tabular-nums">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    )
  }

  return <div className="text-muted-foreground text-xs">Unsupported widget type</div>
}
