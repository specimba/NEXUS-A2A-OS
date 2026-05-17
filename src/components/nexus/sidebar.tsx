'use client'

import { useState } from 'react'
import { useNexusStore, type NexusTab } from '@/store/nexus-store'
import {
  LayoutDashboard,
  FlaskConical,
  Router,
  Server,
  Shield,
  Database,
  BookOpen,
  MessageSquare,
  Bug,
  Coins,
  Gauge,
  ChevronLeft,
  ChevronRight,
  Zap,
  Target,
  LayoutGrid,
  Network,
  Boxes,
  ChevronsDown,
  ChevronsUp,
  Activity,
  Users,
  Globe,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useMediaQuery } from '@/hooks/use-media'
import { motion, AnimatePresence } from 'framer-motion'

interface NavItem {
  id: NexusTab
  label: string
  icon: React.ReactNode
  badge?: string
  shortcut: string
  description: string
}

const navGroups: { label?: string; items: NavItem[] }[] = [
  {
    label: 'Core',
    items: [
      { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" />, shortcut: '1', description: 'System overview and health status' },
      { id: 'architecture', label: 'Architecture', icon: <Boxes className="h-4 w-4" />, badge: 'ARC', shortcut: '2', description: 'Architecture diagram & data flow' },
    ],
  },
  {
    label: 'Testing & Routing',
    items: [
      { id: 'stresslab', label: 'StressLab', icon: <FlaskConical className="h-4 w-4" />, badge: 'ISC', shortcut: '3', description: 'Model stress testing & ISC analysis' },
      { id: 'gmr', label: 'GMR Router', icon: <Router className="h-4 w-4" />, shortcut: '4', description: 'Global Model Router panel' },
      { id: 'providers', label: 'Providers', icon: <Server className="h-4 w-4" />, shortcut: '5', description: 'Provider management & health' },
    ],
  },
  {
    label: 'Governance',
    items: [
      { id: 'governor', label: 'Governor', icon: <Shield className="h-4 w-4" />, shortcut: '6', description: 'Constitutional governance & rules' },
      { id: 'vault', label: 'Vault', icon: <Database className="h-4 w-4" />, shortcut: '7', description: 'Secure data vault & audit log' },
      { id: 'tasks', label: 'Tasks', icon: <Activity className="h-4 w-4" />, badge: 'GOV', shortcut: 'S7', description: 'Task management & tracking' },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { id: 'research', label: 'Research', icon: <BookOpen className="h-4 w-4" />, badge: '20', shortcut: '8', description: 'Research paper vetting & pipeline' },
      { id: 'aichat', label: 'AI Assistant', icon: <MessageSquare className="h-4 w-4" />, badge: 'AI', shortcut: '9', description: 'Multi-model AI chat interface' },
      { id: 'swarm', label: 'Swarm', icon: <Bug className="h-4 w-4" />, shortcut: 'S1', description: 'Agent swarm monitoring' },
    ],
  },
  {
    label: 'Metrics',
    items: [
      { id: 'tokens', label: 'Token Budget', icon: <Coins className="h-4 w-4" />, shortcut: 'S2', description: 'Token usage & budget tracking' },
      { id: 'ratelimit', label: 'Rate Limits', icon: <Gauge className="h-4 w-4" />, shortcut: 'S3', description: 'Rate limit control center' },
      { id: 'kpi', label: 'KPI Dashboard', icon: <Target className="h-4 w-4" />, shortcut: 'S4', description: 'Key Performance Indicators' },
      { id: 'dashboards', label: 'Dashboards', icon: <LayoutGrid className="h-4 w-4" />, badge: 'DSH', shortcut: 'S5', description: 'Custom dashboards & widgets' },
      { id: 'modelrelay', label: 'ModelRelay', icon: <Network className="h-4 w-4" />, badge: 'GWR', shortcut: 'S6', description: 'Gateway routing & model registry' },
    ],
  },
]

const navItems = navGroups.flatMap(g => g.items)

/** Quick Stats mini grid below logo */
function QuickStats({ collapsed }: { collapsed: boolean }) {
  if (collapsed) return null
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="px-3 pt-1 pb-2"
    >
      <div className="grid grid-cols-3 gap-1 rounded-lg border border-border/40 bg-muted/30 p-1.5">
        <div className="flex flex-col items-center gap-0.5 py-1">
          <Activity className="h-3 w-3 text-emerald-500" />
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">99.7%</span>
          <span className="text-[8px] text-muted-foreground/60 uppercase tracking-wider">Uptime</span>
        </div>
        <div className="flex flex-col items-center gap-0.5 py-1 border-x border-border/30">
          <Users className="h-3 w-3 text-emerald-500" />
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">3</span>
          <span className="text-[8px] text-muted-foreground/60 uppercase tracking-wider">Agents</span>
        </div>
        <div className="flex flex-col items-center gap-0.5 py-1">
          <Globe className="h-3 w-3 text-emerald-500" />
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">14</span>
          <span className="text-[8px] text-muted-foreground/60 uppercase tracking-wider">Provs</span>
        </div>
      </div>
    </motion.div>
  )
}

function SidebarNav({ activeTab, setActiveTab, collapsed, onNavigate, groupsCollapsed, toggleGroups }: {
  activeTab: NexusTab
  setActiveTab: (t: NexusTab) => void
  collapsed: boolean
  onNavigate?: () => void
  groupsCollapsed: boolean
  toggleGroups: () => void
}) {
  return (
    <nav className="flex-1 space-y-0.5 p-2 overflow-y-auto custom-scrollbar">
      {/* Collapse/Expand All toggle */}
      {!collapsed && (
        <div className="flex items-center justify-between px-2 mb-1">
          <span className="text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/40">Navigation</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5 text-muted-foreground/50 hover:text-foreground"
                onClick={toggleGroups}
              >
                {groupsCollapsed ? <ChevronsDown className="h-3 w-3" /> : <ChevronsUp className="h-3 w-3" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right" className="text-xs">
              {groupsCollapsed ? 'Expand All Groups' : 'Collapse All Groups'}
            </TooltipContent>
          </Tooltip>
        </div>
      )}

      <AnimatePresence initial={false}>
        {navGroups.map((group, groupIndex) => {
          // When collapsed mode, check if all groups are collapsed
          const isCollapsedGroup = groupsCollapsed && groupIndex > 0
          return (
            <motion.div
              key={group.label || groupIndex}
              initial={false}
              animate={{
                height: isCollapsedGroup && !collapsed ? 'auto' : 'auto',
                opacity: 1,
              }}
              transition={{ duration: 0.2 }}
            >
              {groupIndex > 0 && (
                <div className="mx-2 my-1.5 border-t border-border/40" />
              )}
              {!collapsed && group.label && (
                <div className={cn(
                  "px-2.5 py-1 text-[9px] font-semibold uppercase tracking-widest text-muted-foreground/50 transition-opacity duration-200",
                  isCollapsedGroup && 'opacity-0 h-0 overflow-hidden py-0'
                )}>
                  {group.label}
                </div>
              )}
              {isCollapsedGroup && !collapsed ? null : (
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    const isActive = activeTab === item.id
                    const globalIndex = navItems.findIndex(n => n.id === item.id)
                    return (
                      <Tooltip key={item.id}>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => {
                              setActiveTab(item.id)
                              onNavigate?.()
                            }}
                            className={cn(
                              'relative flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-200',
                              isActive
                                ? 'bg-gradient-to-r from-emerald-600/20 to-emerald-600/5 text-emerald-600 dark:text-emerald-400 shadow-sm shadow-emerald-600/10'
                                : 'text-muted-foreground hover:bg-emerald-600/10 hover:text-accent-foreground'
                            )}
                          >
                            {/* Animated gradient border on active — pulsing emerald glow */}
                            {isActive && (
                              <motion.span
                                className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r bg-emerald-500"
                                animate={{
                                  boxShadow: [
                                    '0 0 6px rgba(52,211,153,0.4)',
                                    '0 0 14px rgba(52,211,153,0.7)',
                                    '0 0 6px rgba(52,211,153,0.4)',
                                  ],
                                }}
                                transition={{
                                  duration: 2,
                                  repeat: Infinity,
                                  ease: 'easeInOut',
                                }}
                              />
                            )}
                            <span className={cn('shrink-0 transition-transform duration-200', isActive && 'scale-110')}>{item.icon}</span>
                            {!collapsed && (
                              <>
                                <span className="flex-1 text-left truncate">{item.label}</span>
                                {/* Keyboard shortcut hint */}
                                <kbd className="pointer-events-none inline-flex h-4 select-none items-center rounded border border-border/50 bg-muted/50 px-1 font-mono text-[9px] font-medium text-muted-foreground/50">
                                  {item.shortcut}
                                </kbd>
                                {item.badge && (
                                  <Badge variant="secondary" className="h-4 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
                                    {item.badge}
                                  </Badge>
                                )}
                              </>
                            )}
                          </button>
                        </TooltipTrigger>
                        {collapsed && (
                          <TooltipContent side="right" className="text-xs">
                            <div className="flex flex-col gap-0.5">
                              <div className="flex items-center gap-2">
                                {item.label}
                                <kbd className="text-[9px] bg-muted px-1 rounded">{item.shortcut}</kbd>
                              </div>
                              <span className="text-[10px] text-muted-foreground font-normal">{item.description}</span>
                            </div>
                          </TooltipContent>
                        )}
                      </Tooltip>
                    )
                  })}
                </div>
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>
    </nav>
  )
}

export function NexusSidebar() {
  const { activeTab, setActiveTab, sidebarOpen, toggleSidebar, setSidebarOpen } = useNexusStore()
  const isMobile = !useMediaQuery('(min-width: 768px)')
  const [groupsCollapsed, setGroupsCollapsed] = useState(false)

  const toggleGroups = () => setGroupsCollapsed(prev => !prev)

  // Mobile: use Sheet
  if (isMobile) {
    return (
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-64 p-0 bg-card">
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation</SheetTitle>
          </SheetHeader>
          <TooltipProvider delayDuration={0}>
            <div className="flex h-full flex-col">
              {/* Logo */}
              <div className="flex h-14 items-center gap-2 px-3 border-b border-border/50">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700">
                  <Zap className="h-4 w-4 text-white" />
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-bold tracking-tight">NEXUS OS</span>
                  <span className="text-[10px] text-muted-foreground">v3.1 — Intelligence Dashboard</span>
                </div>
              </div>

              {/* Quick Stats */}
              <QuickStats collapsed={false} />

              <SidebarNav
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                collapsed={false}
                onNavigate={() => setSidebarOpen(false)}
                groupsCollapsed={groupsCollapsed}
                toggleGroups={toggleGroups}
              />
              <Separator />
              <div className="p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
                  </span>
                  System Operational
                </div>
              </div>
            </div>
          </TooltipProvider>
        </SheetContent>
      </Sheet>
    )
  }

  // Desktop: always-visible collapsible sidebar
  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'flex h-screen flex-col bg-card/80 backdrop-blur-sm transition-all duration-300 border-r border-border/60',
          sidebarOpen ? 'w-56' : 'w-16'
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-2 px-3 border-b border-border/50">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-md shadow-emerald-600/20">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <AnimatePresence>
            {sidebarOpen && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col overflow-hidden"
              >
                <span className="text-sm font-bold tracking-tight text-foreground">NEXUS OS</span>
                <span className="text-[10px] text-muted-foreground">v3.1 — Intelligence Dashboard</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Quick Stats */}
        <AnimatePresence>
          {sidebarOpen && <QuickStats collapsed={!sidebarOpen} />}
        </AnimatePresence>

        {/* Navigation */}
        <SidebarNav
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          collapsed={!sidebarOpen}
          groupsCollapsed={groupsCollapsed}
          toggleGroups={toggleGroups}
        />

        <Separator />

        {/* Status */}
        <div className="p-3">
          {sidebarOpen ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
              </span>
              System Operational
            </div>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="relative mx-auto flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
                </span>
              </TooltipTrigger>
              <TooltipContent side="right">System Operational</TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* Collapse Toggle */}
        <div className="border-t border-border p-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-full text-muted-foreground hover:text-foreground"
            onClick={toggleSidebar}
          >
            {sidebarOpen ? <ChevronLeft className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  )
}
