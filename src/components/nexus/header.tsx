'use client'

import { useNexusStore } from '@/store/nexus-store'
import { Moon, Sun, Menu, Activity, Settings, Terminal, Download } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { NotificationCenter } from '@/components/nexus/notification-center'
import { SystemLogsPanel } from '@/components/nexus/system-logs'
import { GlobalExportDialog } from '@/components/nexus/global-export-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useEffect, useState, useCallback, useRef } from 'react'
import { toast } from 'sonner'
// useMounted removed — using useState+useEffect for hydration safety

const tabTitles: Record<string, string> = {
  overview: 'System Overview',
  stresslab: 'StressLab Arena',
  gmr: 'GMR Router Panel',
  governor: 'Governor Dashboard',
  vault: 'Vault Browser',
  research: 'Research Pipeline',
  swarm: 'Swarm Monitor',
  tokens: 'Token Budget',
}

interface SystemConfig {
  maxAgents: number
  apiCallsLimit: number
  fileWritesLimit: number
  maxConcurrent: number
  healthCheckInterval: number
  fallbackEnabled: boolean
  autoBlockCrit: boolean
  trustDecayRate: number
  sensitivity: string
}

const defaultConfig: SystemConfig = {
  maxAgents: 5,
  apiCallsLimit: 20,
  fileWritesLimit: 30,
  maxConcurrent: 2,
  healthCheckInterval: 30,
  fallbackEnabled: true,
  autoBlockCrit: true,
  trustDecayRate: 0.02,
  sensitivity: 'med',
}

function SystemConfigDialog({ open, onOpenChange }: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [config, setConfig] = useState<SystemConfig>(defaultConfig)

  const handleSave = useCallback(() => {
    toast.success('System configuration saved', {
      description: 'Changes will take effect on next session cycle.',
    })
    onOpenChange(false)
  }, [onOpenChange])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            System Configuration
          </DialogTitle>
          <DialogDescription>
            Configure NEXUS OS constitution limits, GMR settings, and Governor behavior
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-2">
          {/* Constitution Limits */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Constitution Limits</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium">Max Agents / hr</label>
                <Input
                  type="number"
                  value={config.maxAgents}
                  onChange={(e) => setConfig((c) => ({ ...c, maxAgents: parseInt(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium">API Calls / session</label>
                <Input
                  type="number"
                  value={config.apiCallsLimit}
                  onChange={(e) => setConfig((c) => ({ ...c, apiCallsLimit: parseInt(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium">File Writes / session</label>
                <Input
                  type="number"
                  value={config.fileWritesLimit}
                  onChange={(e) => setConfig((c) => ({ ...c, fileWritesLimit: parseInt(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium">Max Concurrent</label>
                <Input
                  type="number"
                  value={config.maxConcurrent}
                  onChange={(e) => setConfig((c) => ({ ...c, maxConcurrent: parseInt(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* GMR Settings */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">GMR Settings</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium">Health Check Interval (s)</label>
                <Input
                  type="number"
                  value={config.healthCheckInterval}
                  onChange={(e) => setConfig((c) => ({ ...c, healthCheckInterval: parseInt(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>
              <div className="flex items-center gap-2 pt-5">
                <Switch
                  checked={config.fallbackEnabled}
                  onCheckedChange={(checked) => setConfig((c) => ({ ...c, fallbackEnabled: checked }))}
                />
                <span className="text-xs">Pool Fallback</span>
              </div>
            </div>
          </div>

          <Separator />

          {/* Governor Settings */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Governor Settings</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-medium">Auto-Block CRIT Actions</span>
                  <p className="text-[10px] text-muted-foreground">Automatically deny CRITICAL impact actions</p>
                </div>
                <Switch
                  checked={config.autoBlockCrit}
                  onCheckedChange={(checked) => setConfig((c) => ({ ...c, autoBlockCrit: checked }))}
                />
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium">Trust Decay Rate</label>
                  <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400 tabular-nums">{config.trustDecayRate.toFixed(3)}/hr</span>
                </div>
                <Input
                  type="number"
                  step="0.001"
                  min="0"
                  max="0.1"
                  value={config.trustDecayRate}
                  onChange={(e) => setConfig((c) => ({ ...c, trustDecayRate: parseFloat(e.target.value) || 0 }))}
                  className="h-8 text-xs font-mono"
                />
                <p className="text-[10px] text-muted-foreground">Rate at which trust scores decay per hour of inactivity</p>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium">Danger Pattern Sensitivity</label>
                <div className="flex gap-2">
                  {(['low', 'med', 'high'] as const).map((level) => (
                    <button
                      key={level}
                      onClick={() => setConfig((c) => ({ ...c, sensitivity: level }))}
                      className={`flex-1 rounded-md px-3 py-1.5 text-[11px] font-medium transition-all duration-200 ${
                        config.sensitivity === level
                          ? level === 'high'
                            ? 'bg-red-600 text-white shadow-sm shadow-red-600/30'
                            : level === 'med'
                            ? 'bg-yellow-600 text-white shadow-sm shadow-yellow-600/30'
                            : 'bg-emerald-600 text-white shadow-sm shadow-emerald-600/30'
                          : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                      }`}
                    >
                      {level.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setConfig(defaultConfig)
              onOpenChange(false)
            }}
          >
            Reset
          </Button>
          <Button
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={handleSave}
          >
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function NexusHeader() {
  const { activeTab, setSidebarOpen, isExportDialogOpen, setExportDialogOpen } = useNexusStore()
  const { setTheme, theme } = useTheme()
  const [time, setTime] = useState('--:--:--')
  const [configOpen, setConfigOpen] = useState(false)
  const [logsOpen, setLogsOpen] = useState(false)

  // Ctrl+L shortcut for logs
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'l') {
        e.preventDefault()
        setLogsOpen(prev => !prev)
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        e.preventDefault()
        setExportDialogOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [setExportDialogOpen])

  // Clock hydration-safe: useState initial value matches placeholder, useEffect sets real time
  useEffect(() => {
    const update = () =>
      setTime(new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="relative flex h-14 items-center gap-3 border-b border-border/60 bg-card/80 backdrop-blur-sm px-4">
      {/* Gradient bottom border */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-600/30 to-transparent" />

      {/* Mobile menu trigger */}
      <Button variant="ghost" size="icon" className="h-8 w-8 md:hidden" onClick={() => setSidebarOpen(true)}>
        <Menu className="h-4 w-4" />
      </Button>

      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-foreground truncate">{tabTitles[activeTab] || 'NEXUS OS'}</h1>
      </div>

      {/* Token budget indicator */}
      <div className="hidden items-center gap-2 rounded-lg bg-gradient-to-r from-emerald-600/10 to-emerald-600/5 border border-emerald-600/10 px-3 py-1.5 sm:flex">
        <Activity className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
        <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">73,450</span>
        <span className="text-[10px] text-muted-foreground">/ 100,000</span>
      </div>

      {/* Active agents */}
      <Badge variant="outline" className="hidden gap-1.5 sm:flex text-[10px]">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        3 agents
      </Badge>

      {/* Notification center */}
      <NotificationCenter />

      {/* Export Dashboard */}
      <Button
        variant="ghost"
        size="sm"
        className="hidden h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground sm:flex"
        onClick={() => setExportDialogOpen(true)}
        aria-label="Export Dashboard"
      >
        <Download className="h-3.5 w-3.5" />
        <span className="hidden lg:inline">Export</span>
      </Button>

      {/* System Logs */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        onClick={() => setLogsOpen(true)}
        aria-label="System Logs"
      >
        <Terminal className="h-4 w-4" />
      </Button>

      {/* Clock */}
      <span className="hidden font-mono text-xs text-muted-foreground md:block tabular-nums">{time}</span>

      {/* System Config */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        onClick={() => setConfigOpen(true)}
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

      {/* System Config Dialog */}
      <SystemConfigDialog open={configOpen} onOpenChange={setConfigOpen} />

      {/* Global Export Dialog */}
      <GlobalExportDialog open={isExportDialogOpen} onOpenChange={setExportDialogOpen} />

      {/* System Logs Panel */}
      <SystemLogsPanel open={logsOpen} onOpenChange={setLogsOpen} />
    </header>
  )
}
