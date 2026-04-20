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

const navItems: { id: NexusTab; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" /> },
  { id: 'stresslab', label: 'StressLab', icon: <FlaskConical className="h-4 w-4" />, badge: 'ISC' },
  { id: 'gmr', label: 'GMR Router', icon: <Router className="h-4 w-4" /> },
  { id: 'governor', label: 'Governor', icon: <Shield className="h-4 w-4" /> },
  { id: 'vault', label: 'Vault', icon: <Database className="h-4 w-4" /> },
  { id: 'research', label: 'Research', icon: <BookOpen className="h-4 w-4" />, badge: '20' },
  { id: 'swarm', label: 'Swarm', icon: <Bug className="h-4 w-4" /> },
  { id: 'tokens', label: 'Token Budget', icon: <Coins className="h-4 w-4" /> },
]

export function NexusSidebar() {
  const { activeTab, setActiveTab, sidebarOpen, toggleSidebar } = useNexusStore()

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'flex h-screen flex-col border-r border-border bg-card transition-all duration-300',
          sidebarOpen ? 'w-56' : 'w-16'
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-2 px-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-emerald-600">
            <Zap className="h-4 w-4 text-white" />
          </div>
          {sidebarOpen && (
            <div className="flex flex-col overflow-hidden">
              <span className="text-sm font-bold tracking-tight text-foreground">NEXUS OS</span>
              <span className="text-[10px] text-muted-foreground">v3.0 — Command Center</span>
            </div>
          )}
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = activeTab === item.id
            const button = (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-emerald-600/15 text-emerald-400'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <span className="shrink-0">{item.icon}</span>
                {sidebarOpen && (
                  <>
                    <span className="flex-1 text-left truncate">{item.label}</span>
                    {item.badge && (
                      <Badge variant="secondary" className="h-4 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-400 border-0">
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
                {!sidebarOpen && item.badge && (
                  <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-emerald-500" />
                )}
              </button>
            )

            if (!sidebarOpen) {
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>{button}</TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              )
            }

            return button
          })}
        </nav>

        <Separator />

        {/* Status */}
        <div className="p-3">
          {sidebarOpen ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              System Operational
            </div>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="mx-auto block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
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
            className="h-7 w-full"
            onClick={toggleSidebar}
          >
            {sidebarOpen ? <ChevronLeft className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  )
}
