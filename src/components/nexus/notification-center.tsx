'use client'

import { useState } from 'react'
import { Bell, Check, CheckCircle2, AlertTriangle, XCircle, Info, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

type Severity = 'info' | 'warning' | 'error' | 'success'
type Category = 'SYSTEM' | 'SECURITY' | 'PERFORMANCE' | 'BUDGET'

interface Notification {
  id: string
  title: string
  description: string
  severity: Severity
  category: Category
  time: string
  read: boolean
}

const severityConfig: Record<Severity, { icon: React.ElementType; color: string; stripe: string; bg: string }> = {
  error: { icon: XCircle, color: 'text-red-400', stripe: 'bg-red-500', bg: 'bg-red-600/5' },
  warning: { icon: AlertTriangle, color: 'text-yellow-400', stripe: 'bg-yellow-500', bg: 'bg-yellow-600/5' },
  success: { icon: CheckCircle2, color: 'text-emerald-400', stripe: 'bg-emerald-500', bg: 'bg-emerald-600/5' },
  info: { icon: Info, color: 'text-blue-400', stripe: 'bg-blue-500', bg: 'bg-blue-600/5' },
}

const categoryColors: Record<Category, string> = {
  SYSTEM: 'bg-emerald-600/15 text-emerald-400',
  SECURITY: 'bg-red-600/15 text-red-400',
  PERFORMANCE: 'bg-orange-600/15 text-orange-400',
  BUDGET: 'bg-blue-600/15 text-blue-400',
}

const initialNotifications: Notification[] = [
  { id: 'n1', title: 'Swarm worker-2 error rate exceeded threshold', description: 'Error rate at 34% — exceeds 25% threshold. Auto-recovery initiated.', severity: 'error', category: 'SYSTEM', time: '2m ago', read: false },
  { id: 'n2', title: 'Governor blocked 3 CRITICAL actions', description: 'Patterns matched: delete_all (2x), override_constitution (1x). All blocked.', severity: 'warning', category: 'SECURITY', time: '5m ago', read: false },
  { id: 'n3', title: 'Token budget at 73.4%', description: '26,550 tokens remaining of 100,000 session budget. Burn rate: 142 tok/min.', severity: 'warning', category: 'BUDGET', time: '10m ago', read: false },
  { id: 'n4', title: 'StressLab test ISC-001 completed', description: 'Result: COLLAPSE detected. qwen3-coder collapsed at 95.3% rate in agentic mode.', severity: 'info', category: 'PERFORMANCE', time: '12m ago', read: false },
  { id: 'n5', title: 'New research paper vetted: OR-Bench', description: 'Over-Refusal Benchmark added to P1 queue. Relevance: 95%. Task assigned.', severity: 'success', category: 'SYSTEM', time: '15m ago', read: true },
  { id: 'n6', title: 'GMR pool FAST: all models healthy', description: 'gemma-fast (100%), nemotron-3-super (96%) — no fallbacks needed.', severity: 'success', category: 'PERFORMANCE', time: '20m ago', read: true },
  { id: 'n7', title: 'Agent worker-3 trust score increased', description: 'Trust updated: 0.78 → 0.82. Reason: successful stress test completion.', severity: 'info', category: 'SECURITY', time: '25m ago', read: true },
  { id: 'n8', title: 'Constitution check passed', description: 'All limits within bounds: 3/5 agents, 12/20 API calls, 8/30 writes, 2/2 concurrent.', severity: 'success', category: 'BUDGET', time: '30m ago', read: true },
]

export function NotificationCenter() {
  const [notifications, setNotifications] = useState(initialNotifications)
  const [open, setOpen] = useState(false)

  const unreadCount = notifications.filter((n) => !n.read).length

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  const markRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative h-8 w-8 text-muted-foreground hover:text-foreground">
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">
              {unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0 glass-card rounded-xl border-border/60 shadow-2xl" align="end" sideOffset={8}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">Notifications</h3>
            {unreadCount > 0 && (
              <Badge className="h-5 px-1.5 text-[9px] bg-red-600/15 text-red-400 border-0">
                {unreadCount} new
              </Badge>
            )}
          </div>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[10px] text-muted-foreground hover:text-foreground gap-1"
              onClick={markAllRead}
            >
              <Check className="h-3 w-3" />
              Mark all read
            </Button>
          )}
        </div>

        {/* Notification List */}
        <ScrollArea className="max-h-80">
          <div className="divide-y divide-border/30">
            {notifications.map((n) => {
              const config = severityConfig[n.severity]
              const Icon = config.icon
              return (
                <button
                  key={n.id}
                  className={cn(
                    'flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/30',
                    !n.read && config.bg
                  )}
                  onClick={() => markRead(n.id)}
                >
                  {/* Left stripe + icon */}
                  <div className="relative flex shrink-0 flex-col items-center">
                    <div className={cn('absolute -left-4 top-0 h-full w-0.5', config.stripe, !n.read ? 'opacity-100' : 'opacity-30')} />
                    <div className={cn('flex h-7 w-7 items-center justify-center rounded-full', config.bg)}>
                      <Icon className={cn('h-3.5 w-3.5', config.color)} />
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className={cn('text-xs font-medium leading-snug', !n.read && 'text-foreground')}>
                        {n.title}
                      </p>
                    </div>
                    <p className="mt-0.5 text-[11px] text-muted-foreground leading-snug line-clamp-2">
                      {n.description}
                    </p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <Badge className={cn('text-[8px] border-0 h-4 px-1', categoryColors[n.category])}>
                        {n.category}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground/60 tabular-nums">{n.time}</span>
                      {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="border-t border-border/50 px-4 py-2">
          <p className="text-[10px] text-muted-foreground text-center">
            {notifications.length} notifications · {unreadCount} unread
          </p>
        </div>
      </PopoverContent>
    </Popover>
  )
}
