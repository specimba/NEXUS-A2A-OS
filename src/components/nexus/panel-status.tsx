'use client'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type PanelStatusValue = 'LIVE' | 'MOCK' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'

export interface PanelStatusProps {
  relayed?: boolean
  source?: string
  brainApiStatus?: string
  latencyMs?: number
  error?: string
  compact?: boolean
  className?: string
}

function normalizeStatus(value?: string): PanelStatusValue {
  if (value === 'LIVE' || value === 'MOCK' || value === 'DEGRADED' || value === 'OFFLINE') return value
  return 'UNKNOWN'
}

const STATUS_CLASS: Record<PanelStatusValue, string> = {
  LIVE: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500',
  MOCK: 'border-sky-500/40 bg-sky-500/10 text-sky-500',
  DEGRADED: 'border-amber-500/40 bg-amber-500/10 text-amber-500',
  OFFLINE: 'border-red-500/40 bg-red-500/10 text-red-500',
  UNKNOWN: 'border-zinc-500/40 bg-zinc-500/10 text-zinc-400',
}

const DOT_CLASS: Record<PanelStatusValue, string> = {
  LIVE: 'bg-emerald-500',
  MOCK: 'bg-sky-500',
  DEGRADED: 'bg-amber-500',
  OFFLINE: 'bg-red-500',
  UNKNOWN: 'bg-zinc-500',
}

export function PanelStatus({
  source,
  brainApiStatus,
  latencyMs,
  error,
  compact = false,
  className,
}: PanelStatusProps) {
  const status = normalizeStatus(brainApiStatus)
  const title = [
    `status=${status}`,
    source ? `source=${source}` : null,
    typeof latencyMs === 'number' ? `latency=${latencyMs}ms` : null,
    error ? `error=${error}` : null,
  ].filter(Boolean).join(' | ')

  return (
    <Badge
      variant="outline"
      title={title}
      className={cn('gap-1.5 text-[10px] uppercase tracking-wide', STATUS_CLASS[status], className)}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', DOT_CLASS[status])} />
      {compact ? status : `${status}${source ? ` - ${source}` : ''}`}
    </Badge>
  )
}
