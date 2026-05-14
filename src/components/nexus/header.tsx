'use client'

import { useState, useEffect, useCallback } from 'react'
import { useNexusStore } from '@/store/nexus-store'
import { Moon, Sun, Menu, Activity, Settings, Bell, Wifi, Search, ChevronRight } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { NotificationCenter } from '@/components/nexus/notification-center'
import { SettingsPanel } from '@/components/nexus/settings-panel'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

const tabTitles: Record<string, string> = {
  overview: 'System Overview',
  architecture: 'System Architecture',
  stresslab: 'StressLab Arena',
  gmr: 'GMR Router Panel',
  providers: 'Provider Management',
  governor: 'Governor Dashboard',
  vault: 'Vault Browser',
  research: 'Research Pipeline',
  aichat: 'AI Assistant',
  swarm: 'Swarm Monitor',
  tokens: 'Token Budget',
  kpi: 'KPI Dashboard',
  ratelimit: 'Rate Limit Control Center',
  dashboards: 'Dashboards',
  modelrelay: 'ModelRelay Gateway',
}

// Map each tab to its group name for breadcrumbs
const tabGroups: Record<string, string> = {
  overview: 'Core',
  architecture: 'Core',
  stresslab: 'Testing & Routing',
  gmr: 'Testing & Routing',
  providers: 'Testing & Routing',
  governor: 'Governance',
  vault: 'Governance',
  research: 'Intelligence',
  aichat: 'Intelligence',
  swarm: 'Intelligence',
  tokens: 'Metrics',
  ratelimit: 'Metrics',
  kpi: 'Metrics',
  dashboards: 'Metrics',
  modelrelay: 'Metrics',
}

/** Circular progress ring for token budget */
function TokenRing({ percent, size = 28, strokeWidth = 3 }: { percent: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (percent / 100) * circumference

  return (
    <svg width={size} height={size} className="shrink-0 -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-muted/30"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="url(#tokenGradient)"
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700"
      />
      <defs>
        <linearGradient id="tokenGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="50%" stopColor="#34d399" />
          <stop offset="100%" stopColor="#22d3ee" />
        </linearGradient>
      </defs>
    </svg>
  )
}

/** Animated number for requests/sec */
function AnimatedRps({ value }: { value: number }) {
  return (
    <motion.span
      key={value}
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.15 }}
      className="inline-block tabular-nums"
    >
      {value}
    </motion.span>
  )
}

export function NexusHeader() {
  const { activeTab, setSidebarOpen } = useNexusStore()
  const { setTheme, theme } = useTheme()
  const [time, setTime] = useState('--:--:--')
  const [date, setDate] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [rps, setRps] = useState(42)
  const [healthPercent, setHealthPercent] = useState(94)

  // Clock + Date
  useEffect(() => {
    const update = () => {
      const now = new Date()
      setTime(
        now.toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      )
      setDate(
        now.toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
        })
      )
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  // Simulated requests/sec counter
  useEffect(() => {
    const interval = setInterval(() => {
      setRps(prev => Math.max(1, prev + Math.floor(Math.random() * 11) - 5))
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  // Simulated health fluctuation
  useEffect(() => {
    const interval = setInterval(() => {
      setHealthPercent(prev => Math.min(100, Math.max(60, prev + (Math.random() - 0.45) * 4)))
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  // Health bar color
  const healthColor = healthPercent >= 90 ? 'from-emerald-500 via-emerald-400 to-emerald-500'
    : healthPercent >= 70 ? 'from-emerald-500 via-yellow-400 to-yellow-500'
    : 'from-yellow-500 via-red-400 to-red-500'

  // Breadcrumb path
  const breadcrumbGroup = tabGroups[activeTab] || ''
  const breadcrumbTab = tabTitles[activeTab] || 'NEXUS OS'

  // Open command palette via custom event
  const openCommandPalette = useCallback(() => {
    // Dispatch a keyboard shortcut Cmd+K
    const event = new KeyboardEvent('keydown', {
      key: 'k',
      metaKey: true,
      ctrlKey: true,
      bubbles: true,
    })
    document.dispatchEvent(event)
  }, [])

  return (
    <>
      <header className="relative flex flex-col">
        {/* System Health indicator bar — thin gradient at very top */}
        <div className="h-1 w-full overflow-hidden bg-muted/20">
          <motion.div
            className={cn('h-full bg-gradient-to-r', healthColor)}
            initial={{ width: '0%' }}
            animate={{ width: `${healthPercent}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />
        </div>

        <div className="flex h-14 items-center gap-3 border-b border-border/60 bg-card/80 backdrop-blur-md px-4">
          {/* Gradient bottom border */}
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-600/30 to-transparent" />

          {/* Mobile menu trigger */}
          <Button variant="ghost" size="icon" className="h-8 w-8 md:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-4 w-4" />
          </Button>

          {/* System status indicator */}
          <div className="hidden items-center gap-1.5 sm:flex">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">Online</span>
          </div>

          {/* Breadcrumb navigation */}
          <div className="hidden md:flex items-center gap-1 text-[10px] text-muted-foreground min-w-0">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 shrink-0">NEXUS OS</span>
            {breadcrumbGroup && (
              <>
                <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/40" />
                <span className="shrink-0 truncate">{breadcrumbGroup}</span>
              </>
            )}
            <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/40" />
            <span className="font-medium text-foreground truncate">{breadcrumbTab}</span>
          </div>

          <div className="flex-1 min-w-0 md:hidden">
            <h1 className="text-sm font-semibold truncate gradient-text">
              {tabTitles[activeTab] || 'NEXUS OS'}
            </h1>
          </div>

          {/* Search input — opens command palette */}
          <button
            onClick={openCommandPalette}
            className="hidden lg:flex items-center gap-2 rounded-lg border border-border/50 bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/50 hover:border-emerald-600/20 transition-colors duration-200 cursor-pointer"
          >
            <Search className="h-3 w-3" />
            <span>Search...</span>
            <kbd className="pointer-events-none inline-flex h-4 select-none items-center gap-0.5 rounded border border-border/50 bg-muted px-1 font-mono text-[9px] font-medium text-muted-foreground/60">
              ⌘K
            </kbd>
          </button>

          {/* Token budget indicator with circular progress ring */}
          <div className="hidden items-center gap-2.5 rounded-lg border border-emerald-600/10 px-3 py-1.5 sm:flex relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/15 via-emerald-600/10 to-cyan-500/10" />
            <div className="relative flex items-center gap-2">
              <TokenRing percent={73} size={28} strokeWidth={3} />
              <div className="flex flex-col gap-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 tabular-nums">73,450</span>
                  <span className="text-[9px] text-muted-foreground">/ 100k</span>
                </div>
                <div className="h-1 w-16 rounded-full bg-muted overflow-hidden">
                  <div className="h-full w-[73%] rounded-full bg-gradient-to-r from-emerald-500 via-emerald-400 to-cyan-400 transition-all duration-500" />
                </div>
              </div>
            </div>
          </div>

          {/* Active agents + Requests/sec */}
          <div className="hidden sm:flex items-center gap-2">
            <Badge variant="outline" className="gap-1.5 text-[10px]">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              3 agents
            </Badge>
            <Badge variant="outline" className="gap-1 text-[10px] font-mono">
              <Activity className="h-3 w-3 text-emerald-500" />
              <AnimatePresence mode="wait">
                <AnimatedRps value={rps} />
              </AnimatePresence>
              <span className="text-muted-foreground">req/s</span>
            </Badge>
          </div>

          {/* Notifications bell — uses real NotificationCenter */}
          <NotificationCenter />

          {/* Clock with date */}
          <div className="hidden md:flex flex-col items-end">
            <span className="font-mono text-xs text-muted-foreground tabular-nums leading-tight">{time}</span>
            <span className="text-[9px] text-muted-foreground/60 leading-tight">{date}</span>
          </div>

          {/* Settings */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            onClick={() => setSettingsOpen(true)}
            aria-label="System Settings"
          >
            <Settings className="h-4 w-4" />
          </Button>

          {/* Theme toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
        </div>
      </header>

      {/* Settings Sheet */}
      <SettingsPanel open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  )
}
