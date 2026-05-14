'use client'

import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import { useNexusStore, type NexusTab } from '@/store/nexus-store'
import { useTheme } from 'next-themes'
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
  Target,
  LayoutGrid,
  Network,
  Boxes,
  PanelLeftClose,
  Sun,
  Moon,
  Terminal,
  Bell,
  Download,
  RefreshCw,
  Settings,
  Trash2,
  Search,
  Clock,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

// ─── Tab Definitions ──────────────────────────────────────────────────────

interface TabDef {
  id: NexusTab
  label: string
  icon: React.ReactNode
  shortcut: string
  description: string
}

const ALL_TABS: TabDef[] = [
  { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" />, shortcut: '1', description: 'System overview and status' },
  { id: 'architecture', label: 'System Architecture', icon: <Boxes className="h-4 w-4" />, shortcut: '2', description: 'Architecture diagram & data flow' },
  { id: 'stresslab', label: 'StressLab Arena', icon: <FlaskConical className="h-4 w-4" />, shortcut: '3', description: 'Model stress testing & ISC analysis' },
  { id: 'gmr', label: 'GMR Router', icon: <Router className="h-4 w-4" />, shortcut: '4', description: 'Global Model Router panel' },
  { id: 'providers', label: 'Providers', icon: <Server className="h-4 w-4" />, shortcut: '5', description: 'Provider management & health' },
  { id: 'governor', label: 'Governor Dashboard', icon: <Shield className="h-4 w-4" />, shortcut: '6', description: 'Constitutional governance & rules' },
  { id: 'vault', label: 'Vault Browser', icon: <Database className="h-4 w-4" />, shortcut: '7', description: 'Secure data vault & audit log' },
  { id: 'research', label: 'Research Pipeline', icon: <BookOpen className="h-4 w-4" />, shortcut: '8', description: 'Research paper vetting & pipeline' },
  { id: 'aichat', label: 'AI Assistant', icon: <MessageSquare className="h-4 w-4" />, shortcut: '9', description: 'Multi-model AI chat interface' },
  { id: 'swarm', label: 'Swarm Monitor', icon: <Bug className="h-4 w-4" />, shortcut: '10', description: 'Agent swarm monitoring' },
  { id: 'tokens', label: 'Token Budget', icon: <Coins className="h-4 w-4" />, shortcut: '11', description: 'Token usage & budget tracking' },
  { id: 'ratelimit', label: 'Rate Limits', icon: <Gauge className="h-4 w-4" />, shortcut: '12', description: 'Rate limit control center' },
  { id: 'kpi', label: 'KPI Dashboard', icon: <Target className="h-4 w-4" />, shortcut: '13', description: 'Key Performance Indicators' },
  { id: 'dashboards', label: 'Dashboards', icon: <LayoutGrid className="h-4 w-4" />, shortcut: '14', description: 'Custom dashboards & widgets' },
  { id: 'modelrelay', label: 'ModelRelay Gateway', icon: <Network className="h-4 w-4" />, shortcut: '15', description: 'Gateway routing & model registry' },
]

// ─── Quick Actions ────────────────────────────────────────────────────────

interface QuickAction {
  id: string
  label: string
  icon: React.ReactNode
  shortcut?: string
  description: string
  action: () => void
}

// ─── Recent Searches Storage ──────────────────────────────────────────────

const RECENT_KEY = 'nexus-cmd-recent'
const MAX_RECENT = 5

function getRecentSearches(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(RECENT_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function addRecentSearch(term: string) {
  if (!term.trim()) return
  try {
    const recent = getRecentSearches().filter(r => r !== term)
    recent.unshift(term)
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, MAX_RECENT)))
  } catch {}
}

function clearRecentSearches() {
  try {
    localStorage.removeItem(RECENT_KEY)
  } catch {}
}

// ─── Component ────────────────────────────────────────────────────────────

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [searchRefresh, setSearchRefresh] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const {
    setActiveTab,
    toggleSidebar,
    toggleChat,
    toggleNotificationCenter,
    setExportDialogOpen,
    clearChatMessages,
  } = useNexusStore()
  const { setTheme, theme } = useTheme()

  // Recompute recent searches each time the dialog opens or searchRefresh changes
  const recentSearches = useMemo(() => (open ? getRecentSearches() : []), [open, searchRefresh])

  const handleTabSelect = useCallback((tab: NexusTab, searchValue?: string) => {
    if (searchValue) addRecentSearch(searchValue)
    setOpen(false)
    setActiveTab(tab)
  }, [setActiveTab])

  const handleAction = useCallback((action: () => void, searchValue?: string) => {
    if (searchValue) addRecentSearch(searchValue)
    setOpen(false)
    action()
  }, [])

  const quickActions: QuickAction[] = [
    {
      id: 'act-theme',
      label: 'Toggle Theme',
      icon: theme === 'dark' ? <Sun className="h-4 w-4 text-amber-500" /> : <Moon className="h-4 w-4 text-violet-500" />,
      shortcut: '⌘⇧D',
      description: `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`,
      action: () => setTheme(theme === 'dark' ? 'light' : 'dark'),
    },
    {
      id: 'act-refresh',
      label: 'Refresh All Data',
      icon: <RefreshCw className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
      shortcut: '⌘⇧R',
      description: 'Refresh all dashboard data',
      action: () => { window.dispatchEvent(new CustomEvent('nexus:refresh-all')) },
    },
    {
      id: 'act-settings',
      label: 'Open Settings',
      icon: <Settings className="h-4 w-4 text-muted-foreground" />,
      shortcut: '⌘,',
      description: 'Open system settings panel',
      action: () => { window.dispatchEvent(new CustomEvent('nexus:open-settings')) },
    },
    {
      id: 'act-clear-chat',
      label: 'Clear Chat History',
      icon: <Trash2 className="h-4 w-4 text-red-500" />,
      description: 'Clear all AI assistant messages',
      action: () => clearChatMessages(),
    },
    {
      id: 'act-export',
      label: 'Export Data',
      icon: <Download className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
      shortcut: '⌘E',
      description: 'Export dashboard data',
      action: () => setExportDialogOpen(true),
    },
  ]

  // Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  // Number key shortcuts for tab navigation (1-9, shift+1-6 for 10-15)
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) return
      if (target.closest('input, textarea, select, [contenteditable]')) return
      if (target.closest('[role="dialog"]')) return
      if (target.closest('[cmdk-input]')) return

      const num = parseInt(e.key)
      if (isNaN(num)) return

      let tabIndex: number
      if (e.shiftKey) {
        // Shift+1 = tab 10, Shift+2 = tab 11, etc.
        tabIndex = 9 + num
      } else {
        tabIndex = num - 1
      }

      if (tabIndex >= 0 && tabIndex < ALL_TABS.length) {
        e.preventDefault()
        setActiveTab(ALL_TABS[tabIndex].id)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [setActiveTab])

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="overflow-hidden rounded-xl border border-border/60 bg-card/95 p-0 shadow-2xl backdrop-blur-xl max-w-lg">
        <Command className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-4 [&_[cmdk-input-wrapper]_svg]:w-4 [&_[cmdk-input]]:h-11 [&_[cmdk-item]]:px-3 [&_[cmdk-item]]:py-2.5 [&_[cmdk-item]_svg]:h-4 [&_[cmdk-item]_svg]:w-4">
          <div className="flex items-center border-b border-border/50 px-3">
            <Sparkles className="mr-2 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <CommandInput placeholder="Type a command or search tabs..." ref={inputRef} />
            <kbd className="ml-2 pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground shrink-0">
              esc
            </kbd>
          </div>
          <CommandList className="max-h-[420px]">
            <CommandEmpty>
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <Search className="h-8 w-8 text-muted-foreground/30 mb-2" />
                <p className="text-sm text-muted-foreground">No results found</p>
                <p className="text-xs text-muted-foreground/60 mt-1">Try a different search term</p>
              </div>
            </CommandEmpty>

            {/* Recent Searches */}
            {recentSearches.length > 0 && (
              <CommandGroup heading="Recent">
                {recentSearches.map((term) => (
                  <CommandItem
                    key={`recent-${term}`}
                    onSelect={() => {
                      const match = ALL_TABS.find(t =>
                        t.label.toLowerCase().includes(term.toLowerCase()) ||
                        t.description.toLowerCase().includes(term.toLowerCase())
                      )
                      if (match) {
                        handleTabSelect(match.id, term)
                      } else {
                        addRecentSearch(term)
                        setOpen(false)
                      }
                    }}
                    className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
                  >
                    <Clock className="h-3.5 w-3.5 text-muted-foreground/50" />
                    <span className="flex-1 text-sm text-muted-foreground">{term}</span>
                    <ArrowRight className="h-3 w-3 text-muted-foreground/30" />
                  </CommandItem>
                ))}
                <CommandItem
                  onSelect={() => { clearRecentSearches(); setSearchRefresh(n => n + 1) }}
                  className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10 text-xs text-muted-foreground"
                >
                  <Trash2 className="h-3 w-3" />
                  <span>Clear recent searches</span>
                </CommandItem>
              </CommandGroup>
            )}

            <CommandGroup heading="Navigate to Tab">
              {ALL_TABS.map((tab) => (
                <CommandItem
                  key={tab.id}
                  value={`navigate-${tab.label}`}
                  onSelect={() => handleTabSelect(tab.id, tab.label)}
                  className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10 group"
                >
                  <span className="shrink-0 text-emerald-600 dark:text-emerald-400 group-aria-selected:text-emerald-500">{tab.icon}</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm">{tab.label}</span>
                    <span className="block text-[10px] text-muted-foreground/60 truncate">{tab.description}</span>
                  </div>
                  <kbd className="pointer-events-none inline-flex h-5 select-none items-center rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground shrink-0">
                    {tab.shortcut}
                  </kbd>
                </CommandItem>
              ))}
            </CommandGroup>

            <CommandSeparator />

            <CommandGroup heading="Quick Actions">
              {quickActions.map((action) => (
                <CommandItem
                  key={action.id}
                  value={`action-${action.label}`}
                  onSelect={() => handleAction(action.action, action.label)}
                  className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
                >
                  {action.icon}
                  <div className="flex-1 min-w-0">
                    <span className="text-sm">{action.label}</span>
                    <span className="block text-[10px] text-muted-foreground/60">{action.description}</span>
                  </div>
                  {action.shortcut && (
                    <kbd className="pointer-events-none inline-flex h-5 select-none items-center rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground shrink-0">
                      {action.shortcut}
                    </kbd>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>

            <CommandSeparator />

            {/* Additional commands */}
            <CommandGroup heading="Controls">
              <CommandItem
                value="control-sidebar"
                onSelect={() => handleAction(toggleSidebar)}
                className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
              >
                <PanelLeftClose className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm">Toggle Sidebar</span>
                  <span className="block text-[10px] text-muted-foreground/60">Show or hide the navigation sidebar</span>
                </div>
                <kbd className="pointer-events-none inline-flex h-5 select-none items-center rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground shrink-0">⌘B</kbd>
              </CommandItem>
              <CommandItem
                value="control-chat"
                onSelect={() => handleAction(toggleChat)}
                className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
              >
                <MessageSquare className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm">Open AI Assistant</span>
                  <span className="block text-[10px] text-muted-foreground/60">Toggle the floating chat assistant</span>
                </div>
              </CommandItem>
              <CommandItem
                value="control-notifications"
                onSelect={() => handleAction(toggleNotificationCenter)}
                className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
              >
                <Bell className="h-4 w-4 text-red-500" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm">View Notifications</span>
                  <span className="block text-[10px] text-muted-foreground/60">Open notification center</span>
                </div>
                <kbd className="pointer-events-none inline-flex h-5 select-none items-center rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground shrink-0">⌘N</kbd>
              </CommandItem>
              <CommandItem
                value="control-terminal"
                onSelect={() => handleAction(() => setActiveTab('aichat'))}
                className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
              >
                <Terminal className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm">Open AI Terminal</span>
                  <span className="block text-[10px] text-muted-foreground/60">Navigate to AI chat tab</span>
                </div>
              </CommandItem>
            </CommandGroup>
          </CommandList>

          {/* Footer */}
          <div className="border-t border-border/50 px-3 py-2 flex items-center justify-between text-[10px] text-muted-foreground">
            <div className="flex items-center gap-3">
              <span>↑↓ navigate</span>
              <span>↵ select</span>
              <span>esc close</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Badge variant="outline" className="h-4 px-1 text-[8px] border-emerald-600/30 text-emerald-600 dark:text-emerald-400">
                {ALL_TABS.length} tabs
              </Badge>
              <kbd className="font-mono bg-muted/50 px-1 py-0.5 rounded">⌘K</kbd>
            </div>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  )
}

// Keep backward-compatible alias
export { CommandPalette as NexusCommandPalette }
