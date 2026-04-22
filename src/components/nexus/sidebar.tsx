'use client'

import { useNexusStore, type NexusTab } from '@/store/nexus-store'
import {
  LayoutDashboard,
  FlaskConical,
  Router,
  Shield,
  Database,
  BookOpen,
  Bug,
  Coins,
  Gauge,
  ChevronLeft,
  ChevronRight,
  Zap,
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

const navItems: { id: NexusTab; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" /> },
  { id: 'stresslab', label: 'StressLab', icon: <FlaskConical className="h-4 w-4" />, badge: 'ISC' },
  { id: 'gmr', label: 'GMR Router', icon: <Router className="h-4 w-4" /> },
  { id: 'governor', label: 'Governor', icon: <Shield className="h-4 w-4" /> },
  { id: 'vault', label: 'Vault', icon: <Database className="h-4 w-4" /> },
  { id: 'research', label: 'Research', icon: <BookOpen className="h-4 w-4" />, badge: '20' },
  { id: 'swarm', label: 'Swarm', icon: <Bug className="h-4 w-4" /> },
  { id: 'tokens', label: 'Token Budget', icon: <Coins className="h-4 w-4" /> },
  { id: 'ratelimit', label: 'Rate Limits', icon: <Gauge className="h-4 w-4" /> },
]

function SidebarNav({ activeTab, setActiveTab, collapsed, onNavigate }: { activeTab: NexusTab; setActiveTab: (t: NexusTab) => void; collapsed: boolean; onNavigate?: () => void }) {
  return (
    <nav className="flex-1 space-y-0.5 p-2 overflow-y-auto custom-scrollbar">
      {navItems.map((item, index) => {
        const isActive = activeTab === item.id
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
                    : 'text-muted-foreground hover:bg-accent/70 hover:text-accent-foreground'
                )}
              >
                {/* Active left border indicator */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
                )}
                <span className={cn('shrink-0 transition-transform duration-200', isActive && 'scale-110')}>{item.icon}</span>
                {!collapsed && (
                  <>
                    <span className="flex-1 text-left truncate">{item.label}</span>
                    <span className="text-[10px] text-muted-foreground/40 tabular-nums">{index + 1}</span>
                    {item.badge && (
                      <Badge variant="secondary" className="h-4 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
              </button>
            </TooltipTrigger>
            {collapsed && <TooltipContent side="right" className="text-xs flex items-center gap-2">{item.label} <kbd className="text-[9px] bg-muted px-1 rounded">{index + 1}</kbd></TooltipContent>}
          </Tooltip>
        )
      })}
    </nav>
  )
}

export function NexusSidebar() {
  const { activeTab, setActiveTab, sidebarOpen, toggleSidebar, setSidebarOpen } = useNexusStore()
  const isMobile = !useMediaQuery('(min-width: 768px)')

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
                  <span className="text-[10px] text-muted-foreground">v3.0 — Command Center</span>
                </div>
              </div>
              <SidebarNav
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                collapsed={false}
                onNavigate={() => setSidebarOpen(false)}
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
          {sidebarOpen && (
            <div className="flex flex-col overflow-hidden">
              <span className="text-sm font-bold tracking-tight text-foreground">NEXUS OS</span>
              <span className="text-[10px] text-muted-foreground">v3.0 — Command Center</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <SidebarNav activeTab={activeTab} setActiveTab={setActiveTab} collapsed={!sidebarOpen} />

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
