'use client'

import { useEffect, useRef, useCallback } from 'react'
import {
  Bell,
  Check,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  X,
  Trash2,
  BellOff,
} from 'lucide-react'
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
import { useNexusStore, type NotificationType, type Notification } from '@/store/nexus-store'
import { toast } from 'sonner'

const typeConfig: Record<NotificationType, { icon: React.ElementType; color: string; stripe: string; bg: string; badgeBg: string }> = {
  error: { icon: XCircle, color: 'text-red-600 dark:text-red-400', stripe: 'bg-red-500', bg: 'bg-red-50 dark:bg-red-600/5', badgeBg: 'bg-red-100 dark:bg-red-600/15 text-red-600 dark:text-red-400' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', stripe: 'bg-yellow-500', bg: 'bg-yellow-50 dark:bg-yellow-600/5', badgeBg: 'bg-yellow-100 dark:bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' },
  success: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', stripe: 'bg-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-600/5', badgeBg: 'bg-emerald-100 dark:bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' },
  info: { icon: Info, color: 'text-blue-600 dark:text-blue-400', stripe: 'bg-blue-500', bg: 'bg-blue-50 dark:bg-blue-600/5', badgeBg: 'bg-blue-100 dark:bg-blue-600/15 text-blue-600 dark:text-blue-400' },
}

const sourceColors: Record<string, string> = {
  Governor: 'bg-purple-100 dark:bg-purple-600/15 text-purple-600 dark:text-purple-400',
  GMR: 'bg-cyan-100 dark:bg-cyan-600/15 text-cyan-600 dark:text-cyan-400',
  Swarm: 'bg-orange-100 dark:bg-orange-600/15 text-orange-600 dark:text-orange-400',
  Vault: 'bg-emerald-100 dark:bg-emerald-600/15 text-emerald-600 dark:text-emerald-400',
  StressLab: 'bg-red-100 dark:bg-red-600/15 text-red-600 dark:text-red-400',
  Research: 'bg-blue-100 dark:bg-blue-600/15 text-blue-600 dark:text-blue-400',
  Tokens: 'bg-yellow-100 dark:bg-yellow-600/15 text-yellow-600 dark:text-yellow-400',
  Monitor: 'bg-teal-100 dark:bg-teal-600/15 text-teal-600 dark:text-teal-400',
}

const simulatedNotifications: Omit<Notification, 'id' | 'read'>[] = [
  { type: 'warning', title: 'Vault entry V-2048 integrity check failed', message: 'Hash mismatch detected on CAP track entry. Re-verification scheduled.', time: 'just now', source: 'Vault' },
  { type: 'info', title: 'GMR rotation: trinity-large → kimi-k2.5', message: 'Scheduled pool rotation for PREMIUM tier. Latency improved by 12ms.', time: 'just now', source: 'GMR' },
  { type: 'error', title: 'Worker-4 unresponsive for 30s', message: 'Heartbeat timeout exceeded. Attempting restart...', time: 'just now', source: 'Swarm' },
  { type: 'success', title: 'StressLab batch run completed', message: 'ISC-005 through ISC-008 all passed. No collapses detected in ICL mode.', time: 'just now', source: 'StressLab' },
  { type: 'warning', title: 'Token burn rate increased to 189 tok/min', message: 'Above rolling average of 142 tok/min. Session ETA reduced by 18min.', time: 'just now', source: 'Tokens' },
  { type: 'info', title: 'Research pipeline: new arXiv paper detected', message: 'Title: "Constitutional AI Safety Bounds". Auto-tagged P1 priority.', time: 'just now', source: 'Research' },
  { type: 'success', title: 'Governor trust recalibration complete', message: 'All agent trust scores recalibrated. worker-3 promoted to review lane.', time: 'just now', source: 'Governor' },
  { type: 'error', title: 'GMR model gemma-fast health critical', message: 'Health at 42%. Auto-failover to nemotron-3-super initiated.', time: 'just now', source: 'GMR' },
  { type: 'warning', title: 'Vault storage at 89% capacity', message: 'Consider archiving TRUST track entries older than 30 days.', time: 'just now', source: 'Vault' },
  { type: 'info', title: 'Monitor: daily health report generated', message: 'System uptime: 99.7%. 2 warnings, 0 critical issues in last 24h.', time: 'just now', source: 'Monitor' },
  { type: 'success', title: 'Swarm task T-1247 completed successfully', message: 'Research summarization finished in 3m 42s. Output stored in Vault.', time: 'just now', source: 'Swarm' },
  { type: 'error', title: 'Governor override attempt blocked', message: 'Agent coordinator attempted CRIT action without quorum. Logged and denied.', time: 'just now', source: 'Governor' },
]

export function NotificationCenter() {
  const {
    notifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    clearNotification,
    clearAllNotifications,
    unreadCount,
    isNotificationCenterOpen,
    setNotificationCenterOpen,
  } = useNexusStore()

  const simIndexRef = useRef(0)

  const count = unreadCount()

  // Simulate new notifications arriving every 30-60 seconds
  useEffect(() => {
    let timerId: ReturnType<typeof setTimeout>

    const tick = () => {
      const delay = 30000 + Math.random() * 30000
      timerId = setTimeout(() => {
        const nextNotif = simulatedNotifications[simIndexRef.current % simulatedNotifications.length]
        simIndexRef.current++
        addNotification(nextNotif)
        toast(nextNotif.title, {
          description: nextNotif.message.length > 80 ? nextNotif.message.slice(0, 80) + '...' : nextNotif.message,
          duration: 4000,
          position: 'bottom-right',
        })
        tick()
      }, delay)
    }
    tick()

    return () => clearTimeout(timerId)
  }, [addNotification])

  const handleClearAll = useCallback(() => {
    clearAllNotifications()
    toast.success('All notifications cleared')
  }, [clearAllNotifications])

  const handleNotificationClick = useCallback((id: string) => {
    markAsRead(id)
  }, [markAsRead])

  const handleDismiss = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    clearNotification(id)
  }, [clearNotification])

  return (
    <Popover open={isNotificationCenterOpen} onOpenChange={setNotificationCenterOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative h-8 w-8 text-muted-foreground hover:text-foreground">
          <Bell className="h-4 w-4" />
          {count > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white dark:text-white animate-in zoom-in-50 duration-200">
              {count > 9 ? '9+' : count}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0 glass-card rounded-xl border-border/60 shadow-2xl" align="end" sideOffset={8}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <h3 className="text-sm font-semibold">Notifications</h3>
            {count > 0 && (
              <Badge className="h-5 px-1.5 text-[9px] bg-red-100 dark:bg-red-600/15 text-red-600 dark:text-red-400 border-0">
                {count} new
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {count > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[10px] text-muted-foreground hover:text-foreground gap-1 px-2"
                onClick={markAllAsRead}
              >
                <Check className="h-3 w-3" />
                Mark all read
              </Button>
            )}
            {notifications.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[10px] text-muted-foreground hover:text-red-600 dark:hover:text-red-400 gap-1 px-2"
                onClick={handleClearAll}
              >
                <Trash2 className="h-3 w-3" />
                Clear all
              </Button>
            )}
          </div>
        </div>

        {/* Notification List */}
        {notifications.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-12 px-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/50 mb-3">
              <BellOff className="h-5 w-5 text-muted-foreground/50" />
            </div>
            <p className="text-sm font-medium text-muted-foreground">No notifications</p>
            <p className="text-[11px] text-muted-foreground/60 mt-1">You&apos;re all caught up. New alerts will appear here.</p>
          </div>
        ) : (
          <ScrollArea className="max-h-96">
            <div className="divide-y divide-border/30">
              {notifications.map((n) => {
                const config = typeConfig[n.type]
                const Icon = config.icon
                return (
                  <div
                    key={n.id}
                    className={cn(
                      'relative flex w-full items-start gap-3 px-4 py-3 text-left transition-all duration-200 cursor-pointer group',
                      'hover:bg-accent/30',
                      !n.read && config.bg
                    )}
                    onClick={() => handleNotificationClick(n.id)}
                  >
                    {/* Left stripe */}
                    <div className={cn('absolute left-0 top-0 h-full w-0.5', config.stripe, !n.read ? 'opacity-100' : 'opacity-20')} />

                    {/* Icon */}
                    <div className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-full', config.bg)}>
                      <Icon className={cn('h-3.5 w-3.5', config.color)} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className={cn('text-xs font-medium leading-snug', !n.read && 'text-foreground')}>
                          {n.title}
                        </p>
                        {/* Dismiss X button */}
                        <button
                          className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-muted/80"
                          onClick={(e) => handleDismiss(e, n.id)}
                          aria-label="Dismiss notification"
                        >
                          <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                        </button>
                      </div>
                      <p className="mt-0.5 text-[11px] text-muted-foreground leading-snug line-clamp-2">
                        {n.message}
                      </p>
                      <div className="mt-1.5 flex items-center gap-2">
                        <Badge className={cn('text-[8px] border-0 h-4 px-1.5', sourceColors[n.source] || 'bg-muted text-muted-foreground')}>
                          {n.source}
                        </Badge>
                        <Badge className={cn('text-[8px] border-0 h-4 px-1.5', config.badgeBg)}>
                          {n.type.toUpperCase()}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground/60 tabular-nums">{n.time}</span>
                        {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 dark:bg-emerald-400 animate-pulse" />}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        )}

        {/* Footer */}
        <Separator className="opacity-50" />
        <div className="px-4 py-2 flex items-center justify-between">
          <p className="text-[10px] text-muted-foreground tabular-nums">
            {notifications.length} notification{notifications.length !== 1 ? 's' : ''} · {count} unread
          </p>
          <p className="text-[10px] text-muted-foreground/50 font-mono">
            ⌘N
          </p>
        </div>
      </PopoverContent>
    </Popover>
  )
}
