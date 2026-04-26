'use client'

import { useId } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
  Legend,
} from 'recharts'

const COLORS = {
  emerald: '#34d399',
  red: '#f87171',
  orange: '#fb923c',
  yellow: '#facc15',
  blue: '#60a5fa',
  purple: '#a78bfa',
  pink: '#f472b6',
}

// NOTE: CSS variables (--foreground, --muted-foreground, etc.) are defined
// using oklch() format (Tailwind CSS 4). They already contain the full color
// function, so we use var(--xxx) directly — NOT hsl(var(--xxx)).

// Shared tooltip style for consistent appearance across all charts
const tooltipContentStyle: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  fontSize: '11px',
  color: 'var(--foreground)',
}

const tooltipLabelStyle: React.CSSProperties = {
  color: 'var(--foreground)',
}

const tooltipItemStyle: React.CSSProperties = {
  color: 'var(--muted-foreground)',
}

// Axis tick style — uses CSS variable directly for oklch support
const axisTickStyle = {
  fontSize: 10,
  fill: 'var(--muted-foreground)',
}

// Mini sparkline-style area chart
export function MiniAreaChart({
  data,
  dataKey = 'value',
  color = COLORS.emerald,
  height = 40,
  showAxis = false,
}: {
  data: Record<string, unknown>[]
  dataKey?: string
  color?: string
  height?: number
  showAxis?: boolean
}) {
  const uid = useId()
  const gradId = `grad-${uid}-${dataKey}`
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
        {showAxis && (
          <>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="name" tick={axisTickStyle} axisLine={false} tickLine={false} />
            <YAxis tick={axisTickStyle} axisLine={false} tickLine={false} width={30} />
          </>
        )}
        <RechartsTooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          itemStyle={tooltipItemStyle}
        />
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey={dataKey} stroke={color} fill={`url(#${gradId})`} strokeWidth={1.5} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// Bar chart
export function NexusBarChart({
  data,
  dataKey = 'value',
  nameKey = 'name',
  color = COLORS.emerald,
  height = 120,
}: {
  data: Record<string, unknown>[]
  dataKey?: string
  nameKey?: string
  color?: string
  height?: number
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey={nameKey} tick={axisTickStyle} axisLine={false} tickLine={false} />
        <YAxis tick={axisTickStyle} axisLine={false} tickLine={false} />
        <RechartsTooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          itemStyle={tooltipItemStyle}
        />
        <Bar dataKey={dataKey} fill={color} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// Radial gauge (for single percentage)
export function NexusGauge({
  value,
  max = 100,
  color = COLORS.emerald,
  label,
  height = 120,
}: {
  value: number
  max?: number
  color?: string
  label?: string
  height?: number
}) {
  const pct = (value / max) * 100
  const data = [{ name: label || 'value', value: pct, fill: color }]

  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart innerRadius="70%" outerRadius="100%" data={data} startAngle={180} endAngle={0}>
          <RadialBar dataKey="value" cornerRadius={6} fill={color} background={{ fill: 'var(--muted)' }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-bold" style={{ color }}>{value.toLocaleString()}</span>
        {label && <span className="text-[10px] text-muted-foreground">{label}</span>}
      </div>
    </div>
  )
}

// Stacked area chart for multi-series timeline data
export function NexusStackedAreaChart({
  data,
  areas,
  height = 200,
  nameKey = 'name',
}: {
  data: Record<string, unknown>[]
  areas: { dataKey: string; color: string; name: string }[]
  height?: number
  nameKey?: string
}) {
  const uid = useId()
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <defs>
          {areas.map((area) => (
            <linearGradient key={area.dataKey} id={`stacked-grad-${uid}-${area.dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={area.color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={area.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey={nameKey}
          tick={axisTickStyle}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={axisTickStyle}
          axisLine={false}
          tickLine={false}
          width={30}
          domain={['auto', 'auto']}
        />
        <RechartsTooltip
          contentStyle={tooltipContentStyle}
          labelStyle={tooltipLabelStyle}
          itemStyle={tooltipItemStyle}
          formatter={(value: number, name: string) => [`${value}%`, name]}
        />
        <Legend
          wrapperStyle={{ fontSize: '10px', color: 'var(--muted-foreground)' }}
          iconType="circle"
          iconSize={8}
        />
        {areas.map((area) => (
          <Area
            key={area.dataKey}
            type="monotone"
            dataKey={area.dataKey}
            name={area.name}
            stroke={area.color}
            fill={`url(#stacked-grad-${uid}-${area.dataKey})`}
            strokeWidth={1.5}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}

export { COLORS }
