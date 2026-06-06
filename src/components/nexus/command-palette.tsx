'use client'

import { useEffect, useState, useCallback } from 'react'
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
  Shield,
  Database,
  BookOpen,
  Bug,
  Coins,
  PanelLeftClose,
  Sun,
  Moon,
  Terminal,
  MessageSquare,
  Bell,
  Download,
} from 'lucide-react'

interface CommandItemDef {
  id: string
  label: string
  icon: React.ReactNode
  shortcut?: string
  action: () => void
  group: 'navigation' | 'actions'
}

export function NexusCommandPalette() {
  const [open, setOpen] = useState(false)
  const { setActiveTab, toggleSidebar, toggleChat, toggleNotificationCenter, setExportDialogOpen } = useNexusStore()
  const { setTheme, theme } = useTheme()

  const commands: CommandItemDef[] = [
    { id: 'nav-overview', label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" />, shortcut: '1', action: () => setActiveTab('overview'), group: 'navigation' },
    { id: 'nav-stresslab', label: 'StressLab Arena', icon: <FlaskConical className="h-4 w-4" />, shortcut: '2', action: () => setActiveTab('stresslab'), group: 'navigation' },
    { id: 'nav-gmr', label: 'GMR Router', icon: <Router className="h-4 w-4" />, shortcut: '3', action: () => setActiveTab('gmr'), group: 'navigation' },
    { id: 'nav-governor', label: 'Governor Dashboard', icon: <Shield className="h-4 w-4" />, shortcut: '4', action: () => setActiveTab('governor'), group: 'navigation' },
    { id: 'nav-vault', label: 'Vault Browser', icon: <Database className="h-4 w-4" />, shortcut: '5', action: () => setActiveTab('vault'), group: 'navigation' },
    { id: 'nav-research', label: 'Research Pipeline', icon: <BookOpen className="h-4 w-4" />, shortcut: '6', action: () => setActiveTab('research'), group: 'navigation' },
    { id: 'nav-swarm', label: 'Swarm Monitor', icon: <Bug className="h-4 w-4" />, shortcut: '7', action: () => setActiveTab('swarm'), group: 'navigation' },
    { id: 'nav-tokens', label: 'Token Budget', icon: <Coins className="h-4 w-4" />, shortcut: '8', action: () => setActiveTab('tokens'), group: 'navigation' },
    { id: 'act-sidebar', label: 'Toggle Sidebar', icon: <PanelLeftClose className="h-4 w-4" />, shortcut: '⌘B', action: () => toggleSidebar(), group: 'actions' },
    { id: 'act-theme', label: 'Toggle Theme', icon: theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />, shortcut: '⌘⇧D', action: () => setTheme(theme === 'dark' ? 'light' : 'dark'), group: 'actions' },
    { id: 'act-stresslab', label: 'Run StressLab Test', icon: <FlaskConical className="h-4 w-4 text-orange-600 dark:text-orange-400" />, action: () => setActiveTab('stresslab'), group: 'actions' },
    { id: 'act-trust', label: 'View Trust Scores', icon: <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />, action: () => setActiveTab('governor'), group: 'actions' },
    { id: 'act-budget', label: 'Check Token Budget', icon: <Coins className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />, action: () => setActiveTab('tokens'), group: 'actions' },
    { id: 'act-chat', label: 'Open AI Assistant', icon: <MessageSquare className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />, action: () => toggleChat(), group: 'actions' },
    { id: 'act-logs', label: 'Open System Logs', icon: <Terminal className="h-4 w-4 text-blue-600 dark:text-blue-400" />, shortcut: '⌘L', action: () => { /* Handled by header keyboard listener */ }, group: 'actions' },
    { id: 'act-notifications', label: 'View Notifications', icon: <Bell className="h-4 w-4 text-red-600 dark:text-red-400" />, shortcut: '⌘N', action: () => toggleNotificationCenter(), group: 'actions' },
    { id: 'act-export', label: 'Export Dashboard', icon: <Download className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />, shortcut: '⌘E', action: () => setExportDialogOpen(true), group: 'actions' },
  ]

  const runCommand = useCallback((command: CommandItemDef) => {
    setOpen(false)
    command.action()
  }, [])

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  // Number key shortcuts for tab navigation
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const tabMap: Record<string, NexusTab> = {
        '1': 'overview', '2': 'stresslab', '3': 'gmr', '4': 'governor',
        '5': 'vault', '6': 'research', '7': 'swarm', '8': 'tokens',
      }
      if (tabMap[e.key]) {
        setActiveTab(tabMap[e.key])
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [setActiveTab])

  const navCommands = commands.filter(c => c.group === 'navigation')
  const actionCommands = commands.filter(c => c.group === 'actions')

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="overflow-hidden rounded-xl border border-border/60 bg-card/95 p-0 shadow-2xl backdrop-blur-xl max-w-lg">
        <Command className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-4 [&_[cmdk-input-wrapper]_svg]:w-4 [&_[cmdk-input]]:h-11 [&_[cmdk-item]]:px-3 [&_[cmdk-item]]:py-2.5 [&_[cmdk-item]_svg]:h-4 [&_[cmdk-item]_svg]:w-4">
          <div className="flex items-center border-b border-border/50 px-3">
            <Terminal className="mr-2 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <CommandInput placeholder="Type a command or search..." />
          </div>
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup heading="Navigation">
              {navCommands.map((cmd) => (
                <CommandItem
                  key={cmd.id}
                  onSelect={() => runCommand(cmd)}
                  className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
                >
                  {cmd.icon}
                  <span className="flex-1 text-sm">{cmd.label}</span>
                  {cmd.shortcut && (
                    <span className="text-[10px] text-muted-foreground font-mono bg-accent/50 px-1.5 py-0.5 rounded">
                      {cmd.shortcut}
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Actions">
              {actionCommands.map((cmd) => (
                <CommandItem
                  key={cmd.id}
                  onSelect={() => runCommand(cmd)}
                  className="flex items-center gap-2 rounded-lg cursor-pointer aria-selected:bg-emerald-600/10"
                >
                  {cmd.icon}
                  <span className="flex-1 text-sm">{cmd.label}</span>
                  {cmd.shortcut && (
                    <span className="text-[10px] text-muted-foreground font-mono bg-accent/50 px-1.5 py-0.5 rounded">
                      {cmd.shortcut}
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
          <div className="border-t border-border/50 px-3 py-2 flex items-center justify-between text-[10px] text-muted-foreground">
            <span>↑↓ navigate · ↵ select · esc close</span>
            <span className="font-mono">⌘K</span>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
