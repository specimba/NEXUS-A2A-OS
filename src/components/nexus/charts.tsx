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
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} width={30} />
          </>
        )}
        <RechartsTooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            fontSize: '11px',
            color: 'hsl(var(--foreground))',
          }}
          labelStyle={{ color: 'hsl(var(--foreground))' }}
          itemStyle={{ color: 'hsl(var(--muted-foreground))' }}
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
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey={nameKey} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
        <RechartsTooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            fontSize: '11px',
            color: 'hsl(var(--foreground))',
          }}
          labelStyle={{ color: 'hsl(var(--foreground))' }}
          itemStyle={{ color: 'hsl(var(--muted-foreground))' }}
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
          <RadialBar dataKey="value" cornerRadius={6} fill={color} background={{ fill: 'hsl(var(--muted))' }} />
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
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey={nameKey}
          tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
          axisLine={false}
          tickLine={false}
          width={30}
          domain={['auto', 'auto']}
        />
        <RechartsTooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            fontSize: '11px',
            color: 'hsl(var(--foreground))',
          }}
          labelStyle={{ color: 'hsl(var(--foreground))' }}
          itemStyle={{ color: 'hsl(var(--muted-foreground))' }}
          formatter={(value: number, name: string) => [`${value}%`, name]}
        />
        <Legend
          wrapperStyle={{ fontSize: '10px', color: 'hsl(var(--muted-foreground))' }}
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
