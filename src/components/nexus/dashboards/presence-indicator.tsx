'use client'

import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import type { SharedMember } from './types'

interface Viewer {
  id: string
  name: string
  online: boolean
}

interface Props {
  dashboardId: string
  sharedWith: SharedMember[]
}

/**
 * Lightweight presence indicator. In production this would be wired to a
 * realtime channel (Supabase / WebSocket). Here it simulates teammate activity
 * by marking some shared members "online" based on a stable hash of their id
 * combined with a 30s tick — giving a live, but deterministic feel.
 */
export function PresenceIndicator({ dashboardId, sharedWith }: Props) {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 30000)
    return () => clearInterval(interval)
  }, [])

  if (sharedWith.length === 0) return null

  const viewers: Viewer[] = [
    { id: 'me', name: 'You', online: true },
    ...sharedWith.map((m) => {
      const seed = hash(`${dashboardId}-${m.id}-${Math.floor(Date.now() / 60000) + tick}`)
      return { id: m.id, name: m.name, online: seed % 3 === 0 }
    }),
  ]

  const online = viewers.filter((v) => v.online)
  const visible = online.slice(0, 4)
  const extra = online.length - visible.length

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex items-center -space-x-2">
        {visible.map((v, i) => (
          <Tooltip key={v.id}>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  'h-7 w-7 rounded-full border-2 border-background flex items-center justify-center text-[11px] font-semibold',
                  v.id === 'me'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground',
                )}
                style={{ zIndex: 10 - i }}
              >
                {v.name.slice(0, 1).toUpperCase()}
                <span className="absolute -bottom-0 -right-0 h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-background" />
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p className="text-xs">{v.name} · live</p>
            </TooltipContent>
          </Tooltip>
        ))}
        {extra > 0 && (
          <div
            className="h-7 w-7 rounded-full border-2 border-background bg-muted text-muted-foreground flex items-center justify-center text-[10px] font-semibold"
            style={{ zIndex: 1 }}
          >
            +{extra}
          </div>
        )}
      </div>
    </TooltipProvider>
  )
}

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i)
  return Math.abs(h)
}
