'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Clock,
  Play,
  Shield,
  AlertTriangle,
  RefreshCw,
  Coins,
  FlaskConical,
  Activity,
} from 'lucide-react'

interface TimelineEvent {
  id: string
  label: string
  time: string
  icon: React.ElementType
  status: 'active' | 'past' | 'future'
  color: string
}

const timelineEvents: TimelineEvent[] = [
  { id: 'start', label: 'Session Started', time: '14:00:00', icon: Play, status: 'past', color: '#34d399' },
  { id: 'stresslab', label: 'First StressLab Test', time: '14:05:23', icon: FlaskConical, status: 'past', color: '#fb923c' },
  { id: 'governor', label: 'Governor Denial', time: '14:12:47', icon: Shield, status: 'past', color: '#f87171' },
  { id: 'rotation', label: 'Model Rotation', time: '14:18:12', icon: RefreshCw, status: 'active', color: '#60a5fa' },
  { id: 'budget', label: 'Budget Alert', time: '~14:30', icon: AlertTriangle, status: 'future', color: '#facc15' },
  { id: 'checkpoint', label: 'VAP Checkpoint', time: '~14:45', icon: Activity, status: 'future', color: '#a78bfa' },
  { id: 'report', label: 'Session Report', time: '~15:00', icon: Coins, status: 'future', color: '#34d399' },
]

export function SessionTimeline() {
  return (
    <Card className="relative overflow-hidden border-blue-600/20">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" /> Session Timeline
          </CardTitle>
          <Badge variant="outline" className="text-[9px] gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            live
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="overflow-x-auto custom-scrollbar pb-2">
          <div className="flex items-center min-w-[600px]">
            {timelineEvents.map((event, i) => {
              const Icon = event.icon
              const isLast = i === timelineEvents.length - 1

              return (
                <div key={event.id} className="flex items-center">
                  {/* Event node */}
                  <div className="flex flex-col items-center">
                    {/* Icon + dot */}
                    <div
                      className={`flex h-9 w-9 items-center justify-center rounded-full border-2 transition-all ${
                        event.status === 'active'
                          ? 'border-emerald-400 bg-emerald-400/10 shadow-lg shadow-emerald-400/20'
                          : event.status === 'past'
                            ? 'border-border bg-card'
                            : 'border-dashed border-muted-foreground/30 bg-transparent'
                      }`}
                    >
                      <Icon
                        className={`h-4 w-4 ${
                          event.status === 'active'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : event.status === 'past'
                              ? 'text-muted-foreground'
                              : 'text-muted-foreground/40'
                        }`}
                      />
                    </div>

                    {/* Active pulse ring */}
                    {event.status === 'active' && (
                      <div className="absolute mt-0 flex h-9 w-9 items-center justify-center">
                        <span className="absolute h-9 w-9 rounded-full border-2 border-emerald-400/40 animate-ping" />
                      </div>
                    )}

                    {/* Label */}
                    <span
                      className={`mt-2 text-[10px] font-medium text-center max-w-[80px] leading-tight ${
                        event.status === 'future' ? 'text-muted-foreground/40' : 'text-muted-foreground'
                      }`}
                    >
                      {event.label}
                    </span>

                    {/* Timestamp */}
                    <span
                      className={`text-[9px] tabular-nums ${
                        event.status === 'active' ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-muted-foreground/50'
                      }`}
                    >
                      {event.time}
                    </span>

                    {/* Status badge */}
                    {event.status === 'active' && (
                      <Badge className="mt-1 bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[8px] px-1.5 py-0">
                        now
                      </Badge>
                    )}
                  </div>

                  {/* Connector line */}
                  {!isLast && (
                    <div className="flex items-center mx-1">
                      <div
                        className={`h-0.5 w-10 ${
                          event.status === 'past' && timelineEvents[i + 1]?.status !== 'future'
                            ? 'bg-emerald-400/30'
                            : event.status === 'active'
                              ? 'bg-gradient-to-r from-emerald-400/30 to-muted-foreground/20'
                              : 'bg-muted-foreground/10 border-t border-dashed border-muted-foreground/20'
                        }`}
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
