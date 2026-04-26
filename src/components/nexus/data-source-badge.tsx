'use client'

import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Database, Wifi, FlaskConical, FileText, Activity } from 'lucide-react'

/**
 * Data Source Badge — clearly indicates whether displayed data is
 * LIVE (from API), SIMULATED (preview/mock), SEED (from DB seed), or MOCK (hardcoded).
 *
 * This is critical for user trust — they need to know what's real and what's fake.
 */

export type DataSource = 'live' | 'simulated' | 'seed' | 'mock' | 'computed' | 'api'

interface DataSourceBadgeProps {
  source: DataSource
  label?: string
  showIcon?: boolean
  className?: string
}

const SOURCE_CONFIG: Record<DataSource, {
  icon: React.ElementType
  label: string
  className: string
  tooltip: string
}> = {
  live: {
    icon: Wifi,
    label: 'LIVE',
    className: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-emerald-600/20 live-badge-glow',
    tooltip: 'Data fetched from a live API or real-time source in real-time',
  },
  api: {
    icon: Wifi,
    label: 'API',
    className: 'bg-cyan-600/15 text-cyan-600 dark:text-cyan-400 border-cyan-600/20',
    tooltip: 'Data fetched from an external API endpoint. Real-time or near-real-time data.',
  },
  seed: {
    icon: Database,
    label: 'SEED',
    className: 'bg-blue-600/15 text-blue-600 dark:text-blue-400 border-blue-600/20',
    tooltip: 'Data loaded from database (seeded at startup). Real structure, preset values.',
  },
  simulated: {
    icon: FlaskConical,
    label: 'SIMULATED',
    className: 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-yellow-600/20',
    tooltip: 'Preview/simulated data shown when no real data is available yet. Will be replaced by live data when it flows in.',
  },
  mock: {
    icon: FileText,
    label: 'MOCK',
    className: 'bg-orange-600/15 text-orange-600 dark:text-orange-400 border-orange-600/20',
    tooltip: 'Hardcoded placeholder data. Not connected to any real data source. For visual demo only.',
  },
  computed: {
    icon: Activity,
    label: 'COMPUTED',
    className: 'bg-purple-600/15 text-purple-600 dark:text-purple-400 border-purple-600/20',
    tooltip: 'Data computed/derived from other data sources. Values are calculated, not stored.',
  },
}

export function DataSourceBadge({ source, label, showIcon = true, className = '' }: DataSourceBadgeProps) {
  const config = SOURCE_CONFIG[source]
  const Icon = config.icon

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={`text-[8px] px-1.5 py-0 font-bold tracking-wider gap-1 cursor-help ${config.className} ${className}`}
          >
            {showIcon && <Icon className="h-2.5 w-2.5" />}
            {label || config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs text-xs">
          <p className="font-medium">{config.label} DATA</p>
          <p className="text-muted-foreground mt-0.5">{config.tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
