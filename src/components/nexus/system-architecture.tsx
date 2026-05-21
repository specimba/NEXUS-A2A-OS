'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import {
  Zap,
  Router,
  Shield,
  Database,
  FlaskConical,
  Bug,
  Activity,
  Settings,
  Hexagon,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useMemo } from 'react'

// ─── Pillar definitions ───────────────────────────────────────────
const PILLAR_DEFS = [
  { name: 'Bridge', icon: Zap, color: '#34d399', colorClass: 'emerald', desc: 'HMAC auth · JSON-RPC', metric: 'latency', metricUnit: 'ms', metricValue: 12 },
  { name: 'Engine', icon: Router, color: '#60a5fa', colorClass: 'blue', desc: 'Hermes intent routing', metric: 'intents', metricUnit: '/min', metricValue: 0 },
  { name: 'Governor', icon: Shield, color: '#f87171', colorClass: 'red', desc: 'Kaiju + TrustScorer', metric: 'decisions', metricUnit: '/24h', metricValue: 18 },
  { name: 'Vault', icon: Database, color: '#a78bfa', colorClass: 'purple', desc: '5-Track memory', metric: 'entries', metricUnit: '', metricValue: 10 },
  { name: 'GMR', icon: FlaskConical, color: '#fb923c', colorClass: 'orange', desc: 'Model rotation', metric: 'models', metricUnit: 'active', metricValue: 7 },
  { name: 'Swarm', icon: Bug, color: '#facc15', colorClass: 'yellow', desc: 'Worker pool', metric: 'workers', metricUnit: 'busy', metricValue: 3 },
  { name: 'Monitor', icon: Activity, color: '#f472b6', colorClass: 'pink', desc: 'Token budget + audit', metric: 'budget', metricUnit: '%', metricValue: 27 },
  { name: 'Config', icon: Settings, color: '#34d399', colorClass: 'emerald', desc: 'Constitution', metric: 'version', metricUnit: '', metricValue: 3.2 },
] as const

// ─── Data flow connections (which pillars talk to which) ──────────
const CONNECTIONS = [
  { from: 'Bridge', to: 'Engine', label: 'auth', color: '#34d399' },
  { from: 'Engine', to: 'Governor', label: 'intent', color: '#60a5fa' },
  { from: 'Engine', to: 'GMR', label: 'route', color: '#60a5fa' },
  { from: 'Engine', to: 'Swarm', label: 'dispatch', color: '#60a5fa' },
  { from: 'Governor', to: 'Vault', label: 'audit', color: '#f87171' },
  { from: 'Swarm', to: 'Vault', label: 'log', color: '#facc15' },
  { from: 'GMR', to: 'Monitor', label: 'tokens', color: '#fb923c' },
  { from: 'Monitor', to: 'Config', label: 'enforce', color: '#f472b6' },
  { from: 'Vault', to: 'Config', label: 'constitution', color: '#a78bfa' },
  { from: 'Bridge', to: 'Vault', label: 'session', color: '#34d399' },
] as const

interface PillarData {
  name: string
  health: number
  status?: string
  desc?: string
  uptime?: string
}

interface SystemArchitectureProps {
  pillarsData?: PillarData[]
  onPillarClick?: (pillarName: string) => void
  showDataSource?: boolean
}

// ─── SVG Circular Progress Ring ───────────────────────────────────
function HealthRing({ health, color, size = 52 }: { health: number; color: string; size?: number }) {
  const strokeWidth = 4
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (health / 100) * circumference
  const center = size / 2

  const glowColor = health >= 95 ? color : health >= 85 ? '#facc15' : '#f87171'

  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      {/* Background track */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-muted/20"
      />
      {/* Progress arc */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={glowColor}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{
          transition: 'stroke-dashoffset 1s ease-in-out, stroke 0.5s ease',
          filter: `drop-shadow(0 0 3px ${glowColor}40)`,
        }}
      />
      {/* Glow pulse on degraded/error */}
      {health < 95 && (
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={glowColor}
          strokeWidth={strokeWidth + 2}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          opacity="0.3"
        >
          <animate
            attributeName="opacity"
            values="0.3;0.1;0.3"
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>
      )}
    </svg>
  )
}

// ─── Mini Sparkline ───────────────────────────────────────────────
function MiniSparkline({ data, color, width = 48, height = 16 }: { data: number[]; color: string; width?: number; height?: number }) {
  if (!data || data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const padding = 1

  const points = data.map((v, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding)
    const y = height - padding - ((v - min) / range) * (height - 2 * padding)
    return `${x},${y}`
  }).join(' ')

  const areaPoints = `${padding},${height - padding} ${points} ${width - padding},${height - padding}`

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={`spark-grad-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={areaPoints}
        fill={`url(#spark-grad-${color.replace('#','')})`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// ─── Single Pillar Cell ───────────────────────────────────────────
function PillarCell({
  pillar,
  health,
  status,
  desc,
  uptime,
  onClick,
}: {
  pillar: typeof PILLAR_DEFS[number]
  health: number
  status?: string
  desc?: string
  uptime?: string
  onClick?: () => void
}) {
  const Icon = pillar.icon
  const isDegraded = status === 'degraded' || health < 90
  const isError = status === 'down' || health < 80

  // Generate deterministic sparkline from health (simulated 8-point trend)
  const sparklineData = useMemo(() => {
    const base = health
    return Array.from({ length: 8 }, (_, i) => {
      const variation = Math.sin(i * 0.8 + pillar.name.charCodeAt(0)) * 3
      return Math.max(70, Math.min(100, base + variation - (i > 5 ? 1 : 0)))
    })
  }, [health, pillar.name])

  // Tailwind needs full class names for JIT — dynamic interpolation won't work
  const colorBorderMap: Record<string, string> = {
    emerald: 'border-emerald-500/20',
    blue: 'border-blue-500/20',
    red: 'border-red-500/20',
    purple: 'border-purple-500/20',
    orange: 'border-orange-500/20',
    yellow: 'border-yellow-500/20',
    pink: 'border-pink-500/20',
  }
  const borderColorClass = isError
    ? 'border-red-500/40'
    : isDegraded
    ? 'border-yellow-500/30'
    : colorBorderMap[pillar.colorClass] ?? 'border-emerald-500/20'

  const statusLabel = isError ? 'ERROR' : isDegraded ? 'DEGRADED' : health === 100 ? 'NOMINAL' : 'OPERATIONAL'
  const statusColorClass = isError
    ? 'text-red-500'
    : isDegraded
    ? 'text-yellow-500'
    : 'text-emerald-500 dark:text-emerald-400'

  return (
    <motion.button
      onClick={onClick}
      className={`group relative flex flex-col items-center gap-1.5 rounded-xl border bg-card/80 p-3 text-center transition-all duration-300 hover:shadow-lg hover:scale-[1.03] active:scale-[0.98] ${borderColorClass}`}
      style={{
        boxShadow: isDegraded || isError
          ? `inset 0 0 20px ${isError ? 'rgba(239,68,68,0.05)' : 'rgba(234,179,8,0.05)'}`
          : `inset 0 0 20px ${pillar.color}08`,
      }}
      whileHover={{ y: -2 }}
      whileTap={{ y: 0 }}
    >
      {/* Status dot - top right */}
      <span className={`absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full border border-card ${
        isError ? 'bg-red-500 animate-pulse' : isDegraded ? 'bg-yellow-500 animate-pulse' : 'bg-emerald-500'
      }`} style={isError || isDegraded ? {} : { boxShadow: `0 0 4px ${pillar.color}60` }} />

      {/* Health ring + icon */}
      <div className="relative flex items-center justify-center">
        <HealthRing health={health} color={pillar.color} size={52} />
        <div className="absolute inset-0 flex items-center justify-center">
          <Icon className="h-4 w-4" style={{ color: pillar.color }} />
        </div>
      </div>

      {/* Pillar name */}
      <span className="text-[11px] font-semibold text-foreground leading-tight">{pillar.name}</span>

      {/* Health percentage */}
      <span className={`text-[10px] font-bold tabular-nums ${statusColorClass}`}>
        {health}%
      </span>

      {/* Sparkline */}
      <MiniSparkline data={sparklineData} color={pillar.color} width={48} height={14} />

      {/* Status label */}
      <span className={`text-[8px] font-medium tracking-wider ${statusColorClass}`}>
        {statusLabel}
      </span>

      {/* Uptime */}
      {uptime && (
        <span className="text-[8px] text-muted-foreground tabular-nums">{uptime}</span>
      )}

      {/* Hover detail overlay */}
      <div className="absolute inset-x-0 bottom-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
        <div className="rounded-b-xl bg-card/95 backdrop-blur-sm border-t border-border/50 px-2 py-1.5">
          <p className="text-[8px] text-muted-foreground leading-tight">{desc || pillar.desc}</p>
        </div>
      </div>
    </motion.button>
  )
}

// ─── Data Flow Line (animated) ────────────────────────────────────
function DataFlowLine({ from, to, pillars }: { from: string; to: string; pillars: typeof PILLAR_DEFS }) {
  const fromPillar = pillars.find(p => p.name === from)
  const toPillar = pillars.find(p => p.name === to)
  if (!fromPillar || !toPillar) return null

  return (
    <div className="flex items-center gap-0.5 text-[8px] text-muted-foreground/50">
      <span style={{ color: fromPillar.color }}>{from}</span>
      <motion.span
        animate={{ x: [0, 2, 0] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        className="text-muted-foreground/30"
      >
        →
      </motion.span>
      <span style={{ color: toPillar.color }}>{to}</span>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────
export function SystemArchitecture({ pillarsData, onPillarClick, showDataSource = true }: SystemArchitectureProps) {
  // Merge API data into defaults
  const pillars = PILLAR_DEFS.map(dp => {
    const api = pillarsData?.find(p => p.name === dp.name)
    return {
      ...dp,
      health: api?.health ?? dp.metricValue,
      status: api?.status,
      desc: api?.desc ?? dp.desc,
      uptime: api?.uptime,
    }
  })

  const avgHealth = pillars.reduce((s, p) => s + p.health, 0) / pillars.length
  const healthyCount = pillars.filter(p => p.health >= 95).length
  const degradedCount = pillars.filter(p => p.health >= 85 && p.health < 95).length
  const errorCount = pillars.filter(p => p.health < 85).length

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Hexagon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Pillar Command Grid
            {showDataSource && <DataSourceBadge source="api" />}
          </CardTitle>
          <div className="flex items-center gap-2">
            {/* Summary indicators */}
            <Badge variant="outline" className="text-[9px] border-emerald-600/30 text-emerald-600 dark:text-emerald-400 gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {healthyCount} OK
            </Badge>
            {degradedCount > 0 && (
              <Badge variant="outline" className="text-[9px] border-yellow-600/30 text-yellow-600 dark:text-yellow-400 gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
                {degradedCount} degraded
              </Badge>
            )}
            {errorCount > 0 && (
              <Badge variant="outline" className="text-[9px] border-red-600/30 text-red-600 dark:text-red-400 gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
                {errorCount} error
              </Badge>
            )}
            <Badge variant="outline" className="text-[9px] tabular-nums">
              Avg: {avgHealth.toFixed(0)}%
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-2">
        {/* Pillar Grid — 4 columns on desktop, 2 on mobile */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {pillars.map((pillar) => (
            <PillarCell
              key={pillar.name}
              pillar={pillar}
              health={pillar.health}
              status={pillar.status}
              desc={pillar.desc}
              uptime={pillar.uptime}
              onClick={() => onPillarClick?.(pillar.name)}
            />
          ))}
        </div>

        {/* Data Flow Topology — shows inter-pillar communication */}
        <div className="mt-4 rounded-lg border border-border/30 bg-card/30 p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground">Data Flow Topology</span>
            <div className="flex-1 h-px bg-border/30" />
            <span className="text-[8px] text-muted-foreground/50">{CONNECTIONS.length} connections</span>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 justify-center">
            {CONNECTIONS.map((conn) => (
              <DataFlowLine key={`${conn.from}-${conn.to}`} from={conn.from} to={conn.to} pillars={PILLAR_DEFS} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
